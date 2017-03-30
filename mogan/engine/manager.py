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

import functools
import sys

from oslo_log import log
import oslo_messaging as messaging
from oslo_service import periodic_task
from oslo_utils import excutils
from oslo_utils import timeutils

from mogan.common import exception
from mogan.common import flow_utils
from mogan.common.i18n import _
from mogan.common import states
from mogan.common import utils
from mogan.conf import CONF
from mogan.engine import base_manager
from mogan.engine.flows import create_instance
from mogan.notifications import base as notifications
from mogan import objects
from mogan.objects import fields
from mogan.objects import quota

LOG = log.getLogger(__name__)


@utils.expects_func_args('instance')
def wrap_instance_fault(function):
    """Wraps a method to catch exceptions related to instances.

    This decorator wraps a method to catch any exceptions having to do with
    an instance that may get thrown. It then logs an instance fault in the db.
    """

    @functools.wraps(function)
    def decorated_function(self, context, *args, **kwargs):
        try:
            return function(self, context, *args, **kwargs)
        except exception.InstanceNotFound:
            raise
        except Exception as e:
            kwargs.update(dict(zip(function.__code__.co_varnames[2:], args)))

            with excutils.save_and_reraise_exception():
                utils.add_instance_fault_from_exc(context,
                                                  kwargs['instance'],
                                                  e, sys.exc_info())

    return decorated_function


class EngineManager(base_manager.BaseEngineManager):
    """Mogan Engine manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, *args, **kwargs):
        super(EngineManager, self).__init__(*args, **kwargs)
        self.quota = quota.Quota()
        self.quota.register_resource(objects.quota.InstanceResource())

    def _get_compute_port(self, context, port_uuid):
        """Gets compute port by the uuid."""
        try:
            return objects.ComputePort.get(context, port_uuid)
        except exception.NotFound:
            LOG.warning("No compute port record for %(port)s",
                        {'port': port_uuid})

    def _get_compute_node(self, context, node_uuid):
        """Gets compute node by the uuid."""
        try:
            return objects.ComputeNode.get(context, node_uuid)
        except exception.NotFound:
            LOG.warning("No compute node record for %(node)s",
                        {'node': node_uuid})

    def _init_compute_port(self, context, port):
        """Initialize the compute port if it does not already exist.

        :param context: security context
        :param port: initial values
        """

        # now try to get the compute port record from the
        # database. If we get one we use resources to initialize
        cp = self._get_compute_port(context, port['port_uuid'])
        if cp:
            cp.update_from_driver(port)
            cp.save()
            return

        # there was no compute port in the database so we need to create
        # a new compute port. This needs to be initialized with node values.
        cp = objects.ComputePort(context)
        cp.update_from_driver(port)
        cp.create()

    def _init_compute_node(self, context, node):
        """Initialize the compute node if it does not already exist.

        :param context: security context
        :param node: initial values
        """

        # now try to get the compute node record from the
        # database. If we get one we use resources to initialize
        cn = self._get_compute_node(context, node['node_uuid'])
        if cn:
            cn.update_from_driver(node)
            cn.save()
        else:
            # there was no compute node in the database so we need to
            # create a new compute node. This needs to be initialized
            # with node values.
            cn = objects.ComputeNode(context)
            cn.update_from_driver(node)
            cn.create()

        # Record compute ports to db
        for port in node['ports']:
            # initialize the compute port object, creating it
            # if it does not already exist.
            self._init_compute_port(context, port)

    @periodic_task.periodic_task(
        spacing=CONF.engine.update_resources_interval,
        run_immediately=True)
    def _update_available_resources(self, context):
        """See driver.get_available_resource()

        Periodic process that keeps that the engine's understanding of
        resource availability in sync with the underlying hypervisor.

        :param context: security context
        """
        nodes = self.driver.get_available_resources()
        compute_nodes_in_db = objects.ComputeNodeList.get_all(context)

        # Record compute nodes to db
        for uuid, node in nodes.items():
            # initialize the compute node object, creating it
            # if it does not already exist.
            self._init_compute_node(context, node)

        # Delete orphan compute node not reported by driver but still in db
        for cn in compute_nodes_in_db:
            if cn.node_uuid not in nodes:
                LOG.info("Deleting orphan compute node %(id)s)",
                         {'id': cn.node_uuid})
                cn.destroy()

    @periodic_task.periodic_task(spacing=CONF.engine.sync_power_state_interval,
                                 run_immediately=True)
    def _sync_power_states(self, context):
        """Align power states between the database and the hypervisor."""

        # Only fetching the necessary fields, will skip synchronizing if
        # target_power_state is not None.

        try:
            nodes = self.driver.get_nodes_power_state()
        except Exception as e:
            LOG.warning(
                ("Failed to retrieve node list when synchronizing power "
                 "states: %(msg)s") % {"msg": e})
            # Just retrun if we fail to get nodes real power state.
            return

        node_dict = {node.instance_uuid: node for node in nodes
                     if node.target_power_state is None}

        if not node_dict:
            LOG.warning("While synchronizing instance power states, "
                        "found none instance with stable power state "
                        "on the hypervisor.")
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
                LOG.exception("Periodic sync_power_state task had an "
                              "error while processing an instance.",
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
                    LOG.info("During sync_power_state the instance has a "
                             "pending task (%(task)s). Skip.",
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
            LOG.info("During sync_power_state the instance has a "
                     "pending task (%(task)s). Skip.",
                     {'task': db_instance.task_state},
                     instance=db_instance)
            return

        if node_power_state != db_power_state:
            LOG.info('During _sync_instance_power_state the DB '
                     'power_state (%(db_power_state)s) does not match '
                     'the node_power_state from the hypervisor '
                     '(%(node_power_state)s). Updating power_state in the '
                     'DB to match the hypervisor.',
                     {'db_power_state': db_power_state,
                      'node_power_state': node_power_state},
                     instance=db_instance)
            # power_state is always updated from hypervisor to db
            db_instance.power_state = node_power_state
            db_instance.save()

    @periodic_task.periodic_task(spacing=CONF.engine.sync_maintenance_interval,
                                 run_immediately=True)
    def _sync_maintenance_states(self, context):
        """Align maintenance states between the database and the hypervisor."""

        try:
            nodes = self.driver.get_maintenance_node_list()
        except Exception as e:
            LOG.warning(
                "Failed to retrieve node list when synchronizing "
                "maintenance states: %(msg)s" % {"msg": e})
            # Just retrun if we fail to get nodes maintenance state.
            return

        node_dict = {node.instance_uuid: node for node in nodes}

        if not node_dict:
            LOG.warning("While synchronizing instance maintenance states, "
                        "found none node with instance associated on the "
                        "hypervisor.")
            return

        db_instances = objects.Instance.list(context)
        for instance in db_instances:
            uuid = instance.uuid

            # If instance in unstable states and the node goes to maintenance,
            # just skip the syncing process as the pending task should be goes
            # to error state instead.
            if instance.status in states.UNSTABLE_STATES:
                LOG.info("During sync_maintenance_state the instance "
                         "has a pending task (%(task)s). Skip.",
                         {'task': instance.status},
                         instance=instance)
                continue

            if uuid not in node_dict:
                continue

            node_maintenance = node_dict[uuid].maintenance

            if instance.status == states.MAINTENANCE and not node_maintenance:
                # TODO(zhenguo): need to check whether we need states machine
                # transition here, and currently we just move to ACTIVE state
                # regardless of it's real power state which may need sync power
                # state periodic task to correct it.
                instance.status = states.ACTIVE
                instance.save()
            elif node_maintenance and instance.status != states.MAINTENANCE:
                instance.status = states.MAINTENANCE
                instance.save()

    def destroy_networks(self, context, instance):
        ports = instance.nics.get_port_ids()
        for port in ports:
            self.network_api.delete_port(context, port, instance.uuid)

    def _rollback_instances_quota(self, context, number):
        reserve_opts = {'instances': number}
        reservations = self.quota.reserve(context, **reserve_opts)
        if reservations:
            self.quota.commit(context, reservations)

    @wrap_instance_fault
    def create_instance(self, context, instance, requested_networks,
                        request_spec=None, filter_properties=None):
        """Perform a deployment."""
        LOG.debug("Starting instance...", instance=instance)
        notifications.notify_about_instance_action(
            context, instance, self.host,
            action=fields.NotificationAction.CREATE,
            phase=fields.NotificationPhase.START)

        fsm = utils.get_state_machine(start_state=instance.status,
                                      target_state=states.ACTIVE)

        if filter_properties is None:
            filter_properties = {}

        retry = filter_properties.pop('retry', {})

        # update attempt count:
        if retry:
            retry['num_attempts'] += 1
        else:
            retry = {
                'num_attempts': 1,
                'nodes': []  # list of tried nodes
            }
        filter_properties['retry'] = retry

        try:
            node = self.scheduler_rpcapi.select_destinations(
                context, request_spec, filter_properties)
            instance.node_uuid = node['node_uuid']
            instance.save()
            # Add a retry entry for the selected node
            nodes = retry['nodes']
            nodes.append(node['node_uuid'])
        except Exception as e:
            utils.process_event(fsm, instance, event='error')
            LOG.error("Created instance %(uuid)s failed. "
                      "Exception: %(exception)s",
                      {"uuid": instance.uuid,
                       "exception": e})
            return

        try:
            flow_engine = create_instance.get_flow(
                context,
                self,
                instance,
                requested_networks,
                node['ports'],
                request_spec,
                filter_properties,
            )
        except Exception:
            utils.process_event(fsm, instance, event='error')
            self._rollback_instances_quota(context, -1)
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
            instance.power_state = states.NOSTATE
            utils.process_event(fsm, instance, event='error')
            self._rollback_instances_quota(context, -1)
            LOG.error("Created instance %(uuid)s failed."
                      "Exception: %(exception)s",
                      {"uuid": instance.uuid,
                       "exception": e})
        else:
            # Advance the state model for the given event. Note that this
            # doesn't alter the instance in any way. This may raise
            # InvalidState, if this event is not allowed in the current state.
            instance.power_state = self.driver.get_power_state(context,
                                                               instance.uuid)
            instance.launched_at = timeutils.utcnow()
            utils.process_event(fsm, instance, event='done')
            LOG.info("Created instance %s successfully.", instance.uuid)
        finally:
            return instance

    def _delete_instance(self, context, instance):
        """Delete an instance

        :param context: mogan request context
        :param instance: instance object
        """
        # TODO(zhenguo): Add delete notification

        try:
            self.destroy_networks(context, instance)
        except Exception as e:
            LOG.error("Destroy networks for instance %(uuid)s failed. "
                      "Exception: %(exception)s",
                      {"uuid": instance.uuid, "exception": e})

        self.driver.unplug_vifs(context, instance)
        self.driver.destroy(context, instance)

    @wrap_instance_fault
    def delete_instance(self, context, instance):
        """Delete an instance."""
        LOG.debug("Deleting instance...")

        fsm = utils.get_state_machine(start_state=instance.status,
                                      target_state=states.DELETED)

        @utils.synchronized(instance.uuid)
        def do_delete_instance(instance):
            try:
                self._delete_instance(context, instance)
            except exception.InstanceNotFound:
                LOG.info("Instance disappeared during terminate",
                         instance=instance)
            except Exception:
                # As we're trying to delete always go to Error if something
                # goes wrong that _delete_instance can't handle.
                with excutils.save_and_reraise_exception():
                    LOG.exception('Setting instance status to ERROR',
                                  instance=instance)
                    instance.power_state = states.NOSTATE
                    utils.process_event(fsm, instance, event='error')
                    self._rollback_instances_quota(context, 1)

        # Issue delete request to driver only if instance is associated with
        # a underlying node.
        if instance.node_uuid:
            do_delete_instance(instance)

        instance.power_state = states.NOSTATE
        utils.process_event(fsm, instance, event='done')
        instance.destroy()

    def set_power_state(self, context, instance, state):
        """Set power state for the specified instance."""

        fsm = utils.get_state_machine(start_state=instance.status)

        @utils.synchronized(instance.uuid)
        def do_set_power_state():
            LOG.debug('Power %(state)s called for instance %(instance)s',
                      {'state': state,
                       'instance': instance})
            self.driver.set_power_state(context, instance, state)

        do_set_power_state()
        instance.power_state = self.driver.get_power_state(context,
                                                           instance.uuid)
        utils.process_event(fsm, instance, event='done')
        LOG.info('Successfully set node power state: %s',
                 state, instance=instance)

    def _rebuild_instance(self, context, instance):
        """Perform rebuild action on the specified instance."""

        # TODO(zhenguo): Add delete notification

        self.driver.rebuild(context, instance)

    @wrap_instance_fault
    def rebuild_instance(self, context, instance):
        """Destroy and re-make this instance.

        :param context: mogan request context
        :param instance: instance object
        """

        LOG.debug('Rebuilding instance', instance=instance)

        fsm = utils.get_state_machine(start_state=instance.status)

        try:
            self._rebuild_instance(context, instance)
        except Exception as e:
            utils.process_event(fsm, instance, event='error')
            LOG.error("Rebuild instance %(uuid)s failed."
                      "Exception: %(exception)s",
                      {"uuid": instance.uuid,
                       "exception": e})
            return

        utils.process_event(fsm, instance, event='done')
        LOG.info('Instance was successfully rebuilt', instance=instance)

    def list_availability_zones(self, context):
        """Get availability zone list."""
        compute_nodes = objects.ComputeNodeList.get_all_available(context)

        azs = set()
        for node in compute_nodes:
            az = node.availability_zone \
                or CONF.engine.default_availability_zone
            if az is not None:
                azs.add(az)

        return {'availability_zones': list(azs)}
