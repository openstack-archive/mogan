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
from oslo_service import loopingcall
from oslo_service import periodic_task
from oslo_utils import timeutils
from oslo_utils import uuidutils
import six
import six.moves.urllib.parse as urlparse

from mogan.common import exception
from mogan.common import flow_utils
from mogan.common.i18n import _
from mogan.common.i18n import _LE
from mogan.common.i18n import _LI
from mogan.common.i18n import _LW
from mogan.common import states
from mogan.common import utils
from mogan.conf import CONF
from mogan.engine.baremetal import ironic
from mogan.engine.baremetal import ironic_states
from mogan.engine import base_manager
from mogan.engine.flows import create_instance
from mogan.notifications import base as notifications
from mogan import objects
from mogan.objects import fields

LOG = log.getLogger(__name__)

_UNPROVISION_STATES = (ironic_states.ACTIVE, ironic_states.DEPLOYFAIL,
                       ironic_states.ERROR, ironic_states.DEPLOYWAIT,
                       ironic_states.DEPLOYING)


class EngineManager(base_manager.BaseEngineManager):
    """Mogan Engine manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)
    _lock = threading.Lock()

    def _refresh_cache(self):
        node_cache = {}
        nodes = ironic.get_node_list(self.ironicclient, detail=True,
                                     maintenance=False,
                                     provision_state=ironic_states.AVAILABLE,
                                     associated=False, limit=0)
        ports = ironic.get_port_list(self.ironicclient, limit=0,
                                     fields=('uuid', 'node_uuid', 'extra',
                                             'address'))
        portgroups = ironic.get_portgroup_list(self.ironicclient, limit=0,
                                               fields=('uuid', 'node_uuid',
                                                       'extra', 'address'))
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
        node_fields = ('instance_uuid', 'power_state', 'target_power_state')

        try:
            nodes = ironic.get_node_list(self.ironicclient,
                                         maintenance=False,
                                         associated=True,
                                         fields=node_fields,
                                         limit=0)
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

    def destroy_networks(self, context, instance):
        LOG.debug("unplug: instance_uuid=%(uuid)s vif=%(instance_nics)s",
                  {'uuid': instance.uuid,
                   'instance_nics': str(instance.nics)})

        ports = instance.nics.get_port_ids()
        for port in ports:
            self.network_api.delete_port(context, port, instance.uuid)

        ironic_ports = ironic.get_ports_from_node(self.ironicclient,
                                                  instance.node_uuid,
                                                  detail=True)
        for pif in ironic_ports:
            if 'vif_port_id' in pif.extra:
                ironic.unplug_vif(self.ironicclient, pif.uuid)

    def _destroy_instance(self, context, instance):
        try:
            ironic.destroy_node(self.ironicclient, instance.node_uuid)
        except Exception as e:
            # if the node is already in a deprovisioned state, continue
            # This should be fixed in Ironic.
            # TODO(deva): This exception should be added to
            #             python-ironicclient and matched directly,
            #             rather than via __name__.
            if getattr(e, '__name__', None) != 'InstanceDeployFailure':
                raise

        # using a dict because this is modified in the local method
        data = {'tries': 0}

        def _wait_for_provision_state():

            try:
                node = ironic.get_node_by_instance(self.ironicclient,
                                                   instance.uuid)
            except ironic_exc.NotFound:
                LOG.debug("Instance already removed from Ironic",
                          instance=instance)
                raise loopingcall.LoopingCallDone()
            LOG.debug('Current ironic node state is %s', node.provision_state)
            if node.provision_state in (ironic_states.NOSTATE,
                                        ironic_states.CLEANING,
                                        ironic_states.CLEANWAIT,
                                        ironic_states.CLEANFAIL,
                                        ironic_states.AVAILABLE):
                # From a user standpoint, the node is unprovisioned. If a node
                # gets into CLEANFAIL state, it must be fixed in Ironic, but we
                # can consider the instance unprovisioned.
                LOG.debug("Ironic node %(node)s is in state %(state)s, "
                          "instance is now unprovisioned.",
                          dict(node=node.uuid, state=node.provision_state),
                          instance=instance)
                raise loopingcall.LoopingCallDone()

            if data['tries'] >= CONF.ironic.api_max_retries + 1:
                msg = (_("Error destroying the instance on node %(node)s. "
                         "Provision state still '%(state)s'.")
                       % {'state': node.provision_state,
                          'node': node.uuid})
                LOG.error(msg)
                raise exception.MoganException(msg)
            else:
                data['tries'] += 1

        # wait for the state transition to finish
        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_provision_state)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()

        LOG.info(_LI('Successfully destroyed Ironic node %s'),
                 instance.node_uuid)

    def _remove_instance_info_from_node(self, instance):
        try:
            ironic.unset_instance_info(self.ironicclient, instance)
        except ironic_exc.BadRequest as e:
            LOG.warning(_LW("Failed to remove deploy parameters from node "
                            "%(node)s when unprovisioning the instance "
                            "%(instance)s: %(reason)s"),
                        {'node': instance.node_uuid, 'instance': instance.uuid,
                         'reason': six.text_type(e)})

    def wait_for_active(self, instance):
        """Wait for the node to be marked as ACTIVE in Ironic."""
        instance.refresh()
        if instance.status in (states.DELETING, states.ERROR, states.DELETED):
            raise exception.InstanceDeployFailure(
                _("Instance %s provisioning was aborted") % instance.uuid)

        node = ironic.get_node_by_instance(self.ironicclient,
                                           instance.uuid)
        LOG.debug('Current ironic node state is %s', node.provision_state)
        if node.provision_state == ironic_states.ACTIVE:
            # job is done
            LOG.debug("Ironic node %(node)s is now ACTIVE",
                      dict(node=node.uuid))
            raise loopingcall.LoopingCallDone()

        if node.target_provision_state in (ironic_states.DELETED,
                                           ironic_states.AVAILABLE):
            # ironic is trying to delete it now
            raise exception.InstanceNotFound(instance_id=instance.uuid)

        if node.provision_state in (ironic_states.NOSTATE,
                                    ironic_states.AVAILABLE):
            # ironic already deleted it
            raise exception.InstanceNotFound(instance_id=instance.uuid)

        if node.provision_state == ironic_states.DEPLOYFAIL:
            # ironic failed to deploy
            msg = (_("Failed to provision instance %(inst)s: %(reason)s")
                   % {'inst': instance.uuid, 'reason': node.last_error})
            raise exception.InstanceDeployFailure(msg)

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
            instance.power_state = ironic.get_power_state(self.ironicclient,
                                                          instance.uuid)
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
            node = ironic.get_node_by_instance(self.ironicclient,
                                               instance.uuid)
        except ironic_exc.NotFound:
            node = None

        if node:
            try:
                if node.provision_state in _UNPROVISION_STATES:
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

    def _wait_for_power_state(self, instance):
        """Wait for the node to complete a power state change."""
        try:
            node = ironic.get_node_by_instance(self.ironicclient,
                                               instance.uuid)
        except ironic_exc.NotFound:
            LOG.debug("While waiting for node to complete a power state "
                      "change, it dissociate with the instance.",
                      instance=instance)
            raise exception.NodeNotFound()

        if node.target_power_state == ironic_states.NOSTATE:
            raise loopingcall.LoopingCallDone()

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
            ironic.set_power_state(self.ironicclient,
                                   instance.node_uuid,
                                   state)

            timer = loopingcall.FixedIntervalLoopingCall(
                self._wait_for_power_state, instance)
            timer.start(interval=CONF.ironic.api_retry_interval).wait()

            fsm.process_event('done')
            instance.power_state = ironic.get_power_state(self.ironicclient,
                                                          instance.uuid)
            instance.status = fsm.current_state
            instance.save()

        do_set_power_state()
        LOG.info(_LI('Successfully set node power state: %s'),
                 state, instance=instance)

    def _rebuild(self, context, instance):
        """Perform rebuild action on the specified instance."""

        try:
            ironic.do_node_rebuild(self.ironicclient, instance.node_uuid)
        except (ironic_exc.InternalServerError,
                ironic_exc.BadRequest) as e:
            msg = (_("Failed to request Ironic to rebuild instance "
                     "%(inst)s: %(reason)s") % {'inst': instance.uuid,
                                                'reason': six.text_type(e)})
            raise exception.InstanceDeployFailure(msg)

        # Although the target provision state is REBUILD, it will actually go
        # to ACTIVE once the redeploy is finished.
        timer = loopingcall.FixedIntervalLoopingCall(self.wait_for_active,
                                                     instance)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()

    def rebuild(self, context, instance):
        """Perform rebuild action on the specified instance."""

        LOG.debug('Rebuild called for instance', instance=instance)
        # Initialize state machine
        fsm = states.machine.copy()
        fsm.initialize(start_state=instance.status)

        try:
            self._rebuild(context, instance)
        except Exception as e:
            fsm.process_event('error')
            instance.status = fsm.current_state
            instance.save()
            LOG.error(_LE("Rebuild instance %(uuid)s failed."
                          "Exception: %(exception)s"),
                      {"uuid": instance.uuid,
                       "exception": e})
            return

        fsm.process_event('done')
        instance.status = fsm.current_state
        instance.save()
        LOG.info(_LI('Instance was successfully rebuilt'), instance=instance)

    @messaging.expected_exceptions(exception.NodeNotFound)
    def get_ironic_node(self, context, instance_uuid, fields):
        """Get a ironic node."""
        try:
            node = ironic.get_node_by_instance(self.ironicclient,
                                               instance_uuid, fields)
        except ironic_exc.NotFound:
            msg = (_("Error retrieving the node by instance %(instance)s.")
                   % {'instance': instance_uuid})
            LOG.debug(msg)
            raise exception.NodeNotFound(msg)

        return node.to_dict()

    def get_ironic_node_list(self, context, fields):
        """Get an ironic node list."""
        nodes = ironic.get_node_list(self.ironicclient, associated=True,
                                     limit=0, fields=fields)
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

    @staticmethod
    def _log_ironic_polling(what, node):
        power_state = (None if node.power_state is None else
                       '"%s"' % node.power_state)
        tgt_power_state = (None if node.target_power_state is None else
                           '"%s"' % node.target_power_state)
        prov_state = (None if node.provision_state is None else
                      '"%s"' % node.provision_state)
        tgt_prov_state = (None if node.target_provision_state is None else
                          '"%s"' % node.target_provision_state)
        LOG.debug('Still waiting for ironic node %(node)s to %(what)s: '
                  'power_state=%(power_state)s, '
                  'target_power_state=%(tgt_power_state)s, '
                  'provision_state=%(prov_state)s, '
                  'target_provision_state=%(tgt_prov_state)s',
                  dict(what=what,
                       node=node.uuid,
                       power_state=power_state,
                       tgt_power_state=tgt_power_state,
                       prov_state=prov_state,
                       tgt_prov_state=tgt_prov_state))

    def get_console(self, context, instance_uuid=None, console_type=None):
        node = ironic.get_node_by_instance(self.ironicclient,
                                           instance_uuid)
        node_uuid = node.uuid

        def _get_console():
            """Request ironicclient to acquire node console."""
            try:
                return ironic.get_console(self.ironicclient, node_uuid)
            except (ironic_exc.InternalServerError,
                    ironic_exc.BadRequest) as e:
                LOG.error(_LE('Failed to acquire console information for '
                              'instance %(inst)s: %(reason)s'),
                          {'inst': instance_uuid,
                           'reason': e})
                raise exception.ConsoleNotAvailable()

        def _wait_state(state):
            """Wait for the expected console mode to be set on node."""
            console = _get_console()
            if console['console_enabled'] == state:
                raise loopingcall.LoopingCallDone(retvalue=console)

            self._log_ironic_polling('set console mode', node)

            # Return False to start backing off
            return False

        def _enable_console(mode):
            """Request ironicclient to enable/disable node console."""
            try:
                ironic.set_console_mode(self.ironicclient, node_uuid, mode)
            except (ironic_exc.InternalServerError,  # Validations
                    ironic_exc.BadRequest) as e:  # Maintenance
                LOG.error(_LE('Failed to set console mode to "%(mode)s" '
                              'for instance %(inst)s: %(reason)s'),
                          {'mode': mode,
                           'inst': instance_uuid,
                           'reason': e})
                raise exception.ConsoleNotAvailable()

            # Waiting for the console state to change (disabled/enabled)
            try:
                timer = loopingcall.BackOffLoopingCall(_wait_state, state=mode)
                return timer.start(
                    starting_interval=1, timeout=10, jitter=0.5).wait()
            except loopingcall.LoopingCallTimeOut:
                LOG.error(_LE('Timeout while waiting for console mode to be '
                              'set to "%(mode)s" on node %(node)s'),
                          {'mode': mode,
                           'node': node_uuid})
                raise exception.ConsoleNotAvailable()

        # Acquire the console
        console = _get_console()

        # NOTE: Resetting console is a workaround to force acquiring
        # console when it has already been acquired by another user/operator.
        # IPMI serial console does not support multi session, so
        # resetting console will deactivate any active one without
        # warning the operator.
        if console['console_enabled']:
            try:
                # Disable console
                _enable_console(False)
                # Then re-enable it
                console = _enable_console(True)
            except exception.ConsoleNotAvailable:
                # NOTE: We try to do recover on failure.
                # But if recover fails, the console may remain in
                # "disabled" state and cause any new connection
                # will be refused.
                console = _enable_console(True)

        if console['console_enabled']:
            token = uuidutils.generate_uuid()
            access_url = '%s?token=%s' % (
                CONF.shellinabox_console.shellinabox_base_url, token)
            console_url = console['console_info']['url']
            parsed_url = urlparse.urlparse(console_url)
            return {'access_url': access_url,
                    'token': token,
                    'host': parsed_url.hostname,
                    'port': parsed_url.port,
                    'internal_access_path': None}
        else:
            LOG.debug('Console is disabled for instance %s',
                      instance_uuid)
            raise exception.ConsoleNotAvailable()
