# Copyright 2016 Huawei Technologies Co.,LTD.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import threading

from ironicclient import exc as ironic_exc
from oslo_log import log
import oslo_messaging as messaging
from oslo_service import periodic_task
from oslo_utils import timeutils
import six

from mogan.common import exception
from mogan.common import flow_utils
from mogan.common.i18n import _
from mogan.common.i18n import _LE
from mogan.common.i18n import _LI
from mogan.common.i18n import _LW
from mogan.common import states
from mogan.common import utils
from mogan.conf import CONF
from mogan.engine import base_manager
from mogan.engine.flows import create_instance
from mogan.notifications import base as notifications
from mogan import objects
from mogan.objects import fields

LOG = log.getLogger(__name__)


class EngineManager(base_manager.BaseEngineManager):
    """Mogan Engine manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)
    _lock = threading.Lock()

    def _refresh_cache(self):
        node_cache = {}
        nodes = self.driver.get_available_node_list()
        ports = self.driver.get_port_list()
        portgroups = self.driver.get_portgroup_list()
        ports += portgroups
        for node in nodes:
            # Add ports to the associated node
            node.ports = [port for port in ports
                          if node.uuid == port.node_uuid]
            node_cache[node.uuid] = node

        with self._lock:
            self.node_cache = node_cache

    @periodic_task.periodic_task(
        spacing=CONF.engine.sync_node_resource_interval,
        run_immediately=True)
    def _sync_node_resources(self, context):
        self._refresh_cache()

    @periodic_task.periodic_task(spacing=CONF.engine.sync_power_state_interval,
                                 run_immediately=True)
    def _sync_power_states(self, context):
        """Align power states between the database and the hypervisor."""

        # Only fetching the necessary fields, will skip synchronizing if
        # target_power_state is not None.

        try:
            nodes = self.driver.get_node_list(maintenance=False,
                                              associated=True)
        except Exception as e:
            LOG.warning(
                _LW("Failed to retrieve node list when synchronizing power "
                    "states: %(msg)s") % {"msg": e})
            # Just retrun if we fail to get nodes real power state.
            return

        node_dict = {node.instance_uuid: node for node in nodes
                     if node.target_power_state is None}

        if not node_dict:
            LOG.warning(_LW("While synchronizing instance power states, "
                            "found none instance with stable power state "
                            "on the hypervisor."))
            return

        def _sync(db_instance, node_power_state):
            # This must be synchronized as we query state from two separate
            # sources, the driver (ironic) and the database. They are set
            # (in stop_instance) and read, in sync.
            @utils.synchronized(db_instance.uuid)
            def sync_instance_power_state():
                self._sync_instance_power_state(context, db_instance,
                                                node_power_state)

            try:
                sync_instance_power_state()
            except Exception:
                LOG.exception(_LE("Periodic sync_power_state task had an "
                                  "error while processing an instance."),
                              instance=db_instance)

            self._syncs_in_progress.pop(db_instance.uuid)

        db_instances = objects.Instance.list(context)
        for db_instance in db_instances:
            # process syncs asynchronously - don't want instance locking to
            # block entire periodic task thread
            uuid = db_instance.uuid
            if uuid in self._syncs_in_progress:
                LOG.debug('Sync power state already in progress for %s', uuid)
                continue

            if db_instance.status not in (states.ACTIVE, states.STOPPED):
                if db_instance.status in states.UNSTABLE_STATES:
                    LOG.info(_LI("During sync_power_state the instance has a "
                                 "pending task (%(task)s). Skip."),
                             {'task': db_instance.status},
                             instance=db_instance)
                continue

            if uuid not in node_dict:
                continue

            node_power_state = node_dict[uuid].power_state
            if db_instance.power_state != node_power_state:
                LOG.debug('Triggering sync for uuid %s', uuid)
                self._syncs_in_progress[uuid] = True
                self._sync_power_pool.spawn_n(_sync, db_instance,
                                              node_power_state)

    def _sync_instance_power_state(self, context, db_instance,
                                   node_power_state):
        """Align instance power state between the database and hypervisor.

        If the instance is not found on the hypervisor, but is in the database,
        then a stop() API will be called on the instance.
        """

        # We re-query the DB to get the latest instance info to minimize
        # (not eliminate) race condition.
        db_instance.refresh()
        db_power_state = db_instance.power_state

        if db_instance.status not in (states.ACTIVE, states.STOPPED):
            # on the receiving end of mogan-engine, it could happen
            # that the DB instance already report the new resident
            # but the actual BM has not showed up on the hypervisor
            # yet. In this case, let's allow the loop to continue
            # and run the state sync in a later round
            LOG.info(_LI("During sync_power_state the instance has a "
                         "pending task (%(task)s). Skip."),
                     {'task': db_instance.task_state},
                     instance=db_instance)
            return

        if node_power_state != db_power_state:
            LOG.info(_LI('During _sync_instance_power_state the DB '
                         'power_state (%(db_power_state)s) does not match '
                         'the node_power_state from the hypervisor '
                         '(%(node_power_state)s). Updating power_state in the '
                         'DB to match the hypervisor.'),
                     {'db_power_state': db_power_state,
                      'node_power_state': node_power_state},
                     instance=db_instance)
            # power_state is always updated from hypervisor to db
            db_instance.power_state = node_power_state
            db_instance.save()

    def _set_instance_obj_error_state(self, context, instance):
        try:
            instance.status = states.ERROR
            instance.save()
        except exception.InstanceNotFound:
            LOG.debug('Instance has been destroyed from under us while '
                      'trying to set it to ERROR', instance=instance)

    def destroy_networks(self, context, instance):
        LOG.debug("unplug: instance_uuid=%(uuid)s vif=%(network_info)s",
                  {'uuid': instance.uuid,
                   'network_info': str(instance.network_info)})

        ports = instance.network_info.keys()
        for port in ports:
            self.network_api.delete_port(context, port, instance.uuid)

        bm_interface = self.driver.get_ports_from_node(instance.node_uuid)

        for pif in bm_interface:
            self.driver.unplug_vif(pif)

    def _destroy_instance(self, context, instance):
        try:
            self.driver.destroy(instance)
        except exception.MoganException as e:
            raise exception.MoganException(e.message)
        except Exception as e:
            # if the node is already in a deprovisioned state, continue
            # This should be fixed in Ironic.
            # TODO(deva): This exception should be added to
            #             python-ironicclient and matched directly,
            #             rather than via __name__.
            if getattr(e, '__name__', None) != 'InstanceDeployFailure':
                raise

        LOG.info(_LI('Successfully destroyed Ironic node %s'),
                 instance.node_uuid)

    def _remove_instance_info_from_node(self, instance):
        try:
            self.driver.unset_instance_info(instance)
        except exception.Invalid as e:
            LOG.warning(_LW("Failed to remove deploy parameters from node "
                            "%(node)s when unprovisioning the instance "
                            "%(instance)s: %(reason)s"),
                        {'node': instance.node_uuid, 'instance': instance.uuid,
                         'reason': six.text_type(e)})

    def create_instance(self, context, instance, requested_networks,
                        request_spec=None, filter_properties=None):
        """Perform a deployment."""
        LOG.debug("Starting instance...", instance=instance)
        notifications.notify_about_instance_action(
            context, instance, self.host,
            action=fields.NotificationAction.CREATE,
            phase=fields.NotificationPhase.START)

        # Initialize state machine
        fsm = states.machine.copy()
        fsm.initialize(start_state=instance.status, target_state=states.ACTIVE)

        if filter_properties is None:
            filter_properties = {}

        try:
            flow_engine = create_instance.get_flow(
                context,
                self,
                instance,
                requested_networks,
                request_spec,
                filter_properties,
            )
        except Exception:
            msg = _("Create manager instance flow failed.")
            LOG.exception(msg)
            raise exception.MoganException(msg)

        def _run_flow():
            # This code executes create instance flow. If something goes wrong,
            # flow reverts all job that was done and reraises an exception.
            # Otherwise, all data that was generated by flow becomes available
            # in flow engine's storage.
            with flow_utils.DynamicLogListener(flow_engine, logger=LOG):
                flow_engine.run()

        try:
            _run_flow()
        except Exception as e:
            fsm.process_event('error')
            instance.power_state = states.NOSTATE
            instance.status = fsm.current_state
            instance.save()
            LOG.error(_LE("Created instance %(uuid)s failed."
                          "Exception: %(exception)s"),
                      {"uuid": instance.uuid,
                       "exception": e})
        else:
            # Advance the state model for the given event. Note that this
            # doesn't alter the instance in any way. This may raise
            # InvalidState, if this event is not allowed in the current state.
            fsm.process_event('done')
            instance.power_state = self.driver.get_power_state(instance.uuid)
            instance.status = fsm.current_state
            instance.launched_at = timeutils.utcnow()
            instance.save()
            LOG.info(_LI("Created instance %s successfully."), instance.uuid)
        finally:
            return instance

    def delete_instance(self, context, instance):
        """Delete an instance."""
        LOG.debug("Deleting instance...")

        # Initialize state machine
        fsm = states.machine.copy()
        fsm.initialize(start_state=instance.status,
                       target_state=states.DELETED)

        try:
            node = self.driver.get_node_by_instance(instance.uuid)
        except exception.NotFound:
            node = None

        if node:
            try:
                if self.driver.is_node_unprovision(node):
                    self.destroy_networks(context, instance)
                    self._destroy_instance(context, instance)
                else:
                    self._remove_instance_info_from_node(instance)
            except Exception:
                LOG.exception(_LE("Error while trying to clean up "
                                  "instance resources."),
                              instance=instance)
                fsm.process_event('error')
                instance.power_state = states.NOSTATE
                instance.status = fsm.current_state
                instance.save()
                return

        fsm.process_event('done')
        instance.power_state = states.NOSTATE
        instance.status = fsm.current_state
        instance.deleted_at = timeutils.utcnow()
        instance.save()
        instance.destroy()

    def set_power_state(self, context, instance, state):
        """Set power state for the specified instance."""

        # Initialize state machine
        fsm = states.machine.copy()
        fsm.initialize(start_state=instance.status)

        @utils.synchronized(instance.uuid)
        def do_set_power_state():
            LOG.debug('Power %(state)s called for instance %(instance)s',
                      {'state': state,
                       'instance': instance})
            self.driver.set_power_state(instance, state)

        do_set_power_state()
        fsm.process_event('done')
        instance.power_state = self.driver.get_power_state(instance.uuid)
        instance.status = fsm.current_state
        instance.save()
        LOG.info(_LI('Successfully set node power state: %s'),
                 state, instance=instance)

    # These two functions used only in ut, maybe can be removed later.
    @messaging.expected_exceptions(exception.NodeNotFound)
    def get_ironic_node(self, context, instance_uuid, fields):
        """Get a ironic node."""
        try:
            node = self.driver.get_node_by_instance(instance_uuid, fields)
        except ironic_exc.NotFound:
            msg = (_("Error retrieving the node by instance %(instance)s.")
                   % {'instance': instance_uuid})
            LOG.debug(msg)
            raise exception.NodeNotFound(msg)

        return node.to_dict()

    def get_ironic_node_list(self, context, fields):
        """Get an ironic node list."""
        nodes = self.driver.get_node_list(associated=True)
        return {'nodes': [node.to_dict() for node in nodes]}

    def list_availability_zones(self, context):
        """Get availability zone list."""
        with self._lock:
            node_cache = self.node_cache.values()

        azs = set()
        for node in node_cache:
            az = node.properties.get('availability_zone') \
                or CONF.engine.default_availability_zone
            if az is not None:
                azs.add(az)

        return {'availability_zones': list(azs)}
