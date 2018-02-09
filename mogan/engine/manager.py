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
from oslo_utils import uuidutils
import six

from mogan.common import exception
from mogan.common import flow_utils
from mogan.common.i18n import _
from mogan.common import states
from mogan.common import utils
from mogan.conf import CONF
from mogan.engine import base_manager
from mogan.engine.flows import create_server
from mogan.notifications import base as notifications
from mogan import objects
from mogan.objects import fields
from mogan.objects import quota
from mogan.scheduler import client
from mogan.scheduler import utils as sched_utils

LOG = log.getLogger(__name__)

POWER_NOTIFICATION_MAP = {
    'on': fields.NotificationAction.POWER_ON,
    'off': fields.NotificationAction.POWER_OFF,
    'reboot': fields.NotificationAction.REBOOT,
    'soft_off': fields.NotificationAction.SOFT_POWER_OFF,
    'soft_reboot': fields.NotificationAction.SOFT_REBOOT
}


@utils.expects_func_args('server')
def wrap_server_fault(function):
    """Wraps a method to catch exceptions related to servers.

    This decorator wraps a method to catch any exceptions having to do with
    a server that may get thrown. It then logs a server fault in the db.
    """

    @functools.wraps(function)
    def decorated_function(self, context, *args, **kwargs):
        try:
            return function(self, context, *args, **kwargs)
        except exception.ServerNotFound:
            raise
        except Exception as e:
            kwargs.update(dict(zip(function.__code__.co_varnames[2:], args)))

            with excutils.save_and_reraise_exception():
                utils.add_server_fault_from_exc(context,
                                                kwargs['server'],
                                                e, sys.exc_info())

    return decorated_function


class EngineManager(base_manager.BaseEngineManager):
    """Mogan Engine manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, *args, **kwargs):
        super(EngineManager, self).__init__(*args, **kwargs)
        self.quota = quota.Quota()
        self.quota.register_resource(objects.quota.ServerResource())
        self.scheduler_client = client.SchedulerClient()

    @periodic_task.periodic_task(
        spacing=CONF.engine.update_resources_interval,
        run_immediately=True)
    def _update_available_resources(self, context):
        """See driver.get_available_resource()

        Periodic process that keeps that the engine's understanding of
        resource availability in sync with the underlying hypervisor.

        :param context: security context
        """

        all_nodes = self.driver.get_available_nodes()
        all_rps = self.scheduler_client.reportclient\
            .get_filtered_resource_providers({})
        node_uuids = [node.uuid for node in all_nodes]

        # Clean orphan resource providers in placement
        for rp in all_rps:
            if rp['uuid'] not in node_uuids:
                server_by_node = objects.Server.list(
                    context, filters={'node_uuid': rp['uuid']})
                if server_by_node:
                    continue
                self.scheduler_client.reportclient.delete_resource_provider(
                    rp['uuid'])

        for node in all_nodes:
            if self.driver.is_node_consumable(node):
                self.scheduler_client.reportclient \
                    .delete_allocations_for_resource_provider(node.uuid)
            resource_class = sched_utils.ensure_resource_class_name(
                node.resource_class)
            inventory = self.driver.get_node_inventory(node)
            inventory_data = {resource_class: inventory}
            self.scheduler_client.set_inventory_for_provider(
                node.uuid, node.name or node.uuid, inventory_data,
                resource_class)

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
            # Just return if we fail to get nodes real power state.
            return

        node_dict = {node.instance_uuid: node for node in nodes
                     if node.target_power_state is None}

        if not node_dict:
            LOG.warning("While synchronizing server power states, "
                        "found none server with stable power state "
                        "on the hypervisor.")
            return

        def _sync(db_server, node_power_state):
            # This must be synchronized as we query state from two separate
            # sources, the driver (ironic) and the database. They are set
            # (in stop_server) and read, in sync.
            @utils.synchronized(db_server.uuid)
            def sync_server_power_state():
                self._sync_server_power_state(context, db_server,
                                              node_power_state)

            try:
                sync_server_power_state()
            except Exception:
                LOG.exception("Periodic sync_power_state task had an "
                              "error while processing a server.",
                              server=db_server)

            self._syncs_in_progress.pop(db_server.uuid)

        db_servers = objects.Server.list(context)
        for db_server in db_servers:
            # process syncs asynchronously - don't want server locking to
            # block entire periodic task thread
            uuid = db_server.uuid
            if uuid in self._syncs_in_progress:
                LOG.debug('Sync power state already in progress for %s', uuid)
                continue

            if db_server.status not in (states.ACTIVE, states.STOPPED):
                if db_server.status in states.UNSTABLE_STATES:
                    LOG.info("During sync_power_state the server has a "
                             "pending task (%(task)s). Skip.",
                             {'task': db_server.status},
                             server=db_server)
                continue

            if uuid not in node_dict:
                continue

            node_power_state = node_dict[uuid].power_state
            if db_server.power_state != node_power_state:
                LOG.debug('Triggering sync for uuid %s', uuid)
                self._syncs_in_progress[uuid] = True
                self._sync_power_pool.spawn_n(_sync, db_server,
                                              node_power_state)

    def _sync_server_power_state(self, context, db_server,
                                 node_power_state):
        """Align server power state between the database and hypervisor.

        If the server is not found on the hypervisor, but is in the database,
        then a stop() API will be called on the server.
        """

        # We re-query the DB to get the latest server info to minimize
        # (not eliminate) race condition.
        db_server.refresh()
        db_power_state = db_server.power_state

        if db_server.status not in (states.ACTIVE, states.STOPPED):
            # on the receiving end of mogan-engine, it could happen
            # that the DB server already report the new resident
            # but the actual BM has not showed up on the hypervisor
            # yet. In this case, let's allow the loop to continue
            # and run the state sync in a later round
            LOG.info("During sync_power_state the server has a "
                     "pending task (%(task)s). Skip.",
                     {'task': db_server.task_state},
                     server=db_server)
            return

        if node_power_state != db_power_state:
            LOG.info('During _sync_server_power_state the DB '
                     'power_state (%(db_power_state)s) does not match '
                     'the node_power_state from the hypervisor '
                     '(%(node_power_state)s). Updating power_state in the '
                     'DB to match the hypervisor.',
                     {'db_power_state': db_power_state,
                      'node_power_state': node_power_state},
                     server=db_server)
            # power_state is always updated from hypervisor to db
            db_server.power_state = node_power_state
            db_server.save()

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
            # Just return if we fail to get nodes maintenance state.
            return

        node_dict = {node.instance_uuid: node for node in nodes}

        if not node_dict:
            LOG.warning("While synchronizing server maintenance states, "
                        "found none node with server associated on the "
                        "hypervisor.")
            return

        db_servers = objects.Server.list(context)
        for server in db_servers:
            uuid = server.uuid

            # If server in unstable states and the node goes to maintenance,
            # just skip the syncing process as the pending task should be goes
            # to error state instead.
            if server.status in states.UNSTABLE_STATES:
                LOG.info("During sync_maintenance_state the server "
                         "has a pending task (%(task)s). Skip.",
                         {'task': server.status},
                         server=server)
                continue

            if uuid not in node_dict:
                continue

            node_maintenance = node_dict[uuid].maintenance

            if server.status == states.MAINTENANCE and not node_maintenance:
                # TODO(zhenguo): need to check whether we need states machine
                # transition here, and currently we just move to ACTIVE state
                # regardless of it's real power state which may need sync power
                # state periodic task to correct it.
                server.status = states.ACTIVE
                server.save()
            elif node_maintenance and server.status != states.MAINTENANCE:
                server.status = states.MAINTENANCE
                server.save()

    def destroy_networks(self, context, server):
        for nic in server.nics:
            self._detach_interface(context, server, nic.port_id,
                                   nic.preserve_on_delete)

    def _rollback_servers_quota(self, context, number):
        reserve_opts = {'servers': number}
        reservations = self.quota.reserve(context, **reserve_opts)
        if reservations:
            self.quota.commit(context, reservations)

    def schedule_and_create_servers(self, context, servers,
                                    requested_networks,
                                    user_data,
                                    injected_files,
                                    admin_password,
                                    key_pair,
                                    partitions,
                                    request_spec=None,
                                    filter_properties=None):

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
        request_spec['num_servers'] = len(servers)
        request_spec['server_ids'] = [s.uuid for s in servers]
        try:
            nodes = self.scheduler_client.select_destinations(
                context, request_spec, filter_properties)
        except exception.NoValidNode as e:
            # Here should reset the state of building servers to Error
            # state. And rollback the quotas.
            # TODO(litao) rollback the quotas
            with excutils.save_and_reraise_exception():
                for server in servers:
                    fsm = utils.get_state_machine(
                        start_state=server.status,
                        target_state=states.ACTIVE)
                    utils.process_event(fsm, server, event='error')
                    utils.add_server_fault_from_exc(
                        context, server, e, sys.exc_info())

        LOG.info("The selected nodes %(nodes)s for servers",
                 {"nodes": nodes})

        for (server, node) in six.moves.zip(servers, nodes):
            server.node_uuid = node
            server.node = self.driver.get_node_name(node)
            server.save()
            # Add a retry entry for the selected node
            retry_nodes = retry['nodes']
            retry_nodes.append(node)

        for server in servers:
            utils.spawn_n(self._create_server,
                          context, server,
                          requested_networks,
                          user_data,
                          injected_files,
                          admin_password,
                          key_pair,
                          partitions,
                          request_spec,
                          filter_properties)

    @wrap_server_fault
    def _create_server(self, context, server, requested_networks,
                       user_data, injected_files, admin_password, key_pair,
                       partitions, request_spec=None, filter_properties=None):
        """Perform a deployment."""
        LOG.debug("Creating server: %s", server)
        notifications.notify_about_server_action(
            context, server, self.host,
            action=fields.NotificationAction.CREATE,
            phase=fields.NotificationPhase.START)

        fsm = utils.get_state_machine(start_state=server.status,
                                      target_state=states.ACTIVE)

        try:
            flow_engine = create_server.get_flow(
                context,
                self,
                server,
                requested_networks,
                user_data,
                injected_files,
                admin_password,
                key_pair,
                partitions,
                request_spec,
                filter_properties,
            )
        except Exception as e:
            with excutils.save_and_reraise_exception():
                utils.process_event(fsm, server, event='error')
                self._rollback_servers_quota(context, -1)
                notifications.notify_about_server_action(
                    context, server, self.host,
                    action=fields.NotificationAction.CREATE,
                    phase=fields.NotificationPhase.ERROR, exception=e)
                msg = _("Create manager server flow failed.")
                LOG.exception(msg)

        def _run_flow():
            # This code executes create server flow. If something goes wrong,
            # flow reverts all job that was done and reraises an exception.
            # Otherwise, all data that was generated by flow becomes available
            # in flow engine's storage.
            with flow_utils.DynamicLogListener(flow_engine, logger=LOG):
                flow_engine.run()

        try:
            _run_flow()
        except Exception as e:
            with excutils.save_and_reraise_exception():
                server.power_state = states.NOSTATE
                utils.process_event(fsm, server, event='error')
                self._rollback_servers_quota(context, -1)
                notifications.notify_about_server_action(
                    context, server, self.host,
                    action=fields.NotificationAction.CREATE,
                    phase=fields.NotificationPhase.ERROR, exception=e)
                LOG.error("Created server %(uuid)s failed."
                          "Exception: %(exception)s",
                          {"uuid": server.uuid,
                           "exception": e})
        # Advance the state model for the given event. Note that this
        # doesn't alter the server in any way. This may raise
        # InvalidState, if this event is not allowed in the current state.
        server.power_state = self.driver.get_power_state(context,
                                                         server.uuid)
        server.launched_at = timeutils.utcnow()
        utils.process_event(fsm, server, event='done')
        notifications.notify_about_server_action(
            context, server, self.host,
            action=fields.NotificationAction.CREATE,
            phase=fields.NotificationPhase.END)
        LOG.info("Created server %s successfully.", server.uuid)

    def _delete_server(self, context, server):
        """Delete a server

        :param context: mogan request context
        :param server: server object
        """
        try:
            self.destroy_networks(context, server)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error("Destroy networks for server %(uuid)s failed. "
                          "Exception: %(exception)s",
                          {"uuid": server.uuid, "exception": e})
        self.driver.destroy(context, server)

    @wrap_server_fault
    def delete_server(self, context, server):
        """Delete a server."""
        LOG.debug("Deleting server: %s.", server.uuid)
        notifications.notify_about_server_action(
            context, server, self.host,
            action=fields.NotificationAction.DELETE,
            phase=fields.NotificationPhase.START)
        fsm = utils.get_state_machine(start_state=server.status,
                                      target_state=states.DELETED)

        @utils.synchronized(server.uuid)
        def do_delete_server(server):
            try:
                self._delete_server(context, server)
            except exception.ServerNotFound:
                LOG.info("Server disappeared during terminate",
                         server=server)
            except Exception:
                # As we're trying to delete always go to Error if something
                # goes wrong that _delete_server can't handle.
                with excutils.save_and_reraise_exception():
                    LOG.exception('Setting server status to ERROR',
                                  server=server)
                    server.power_state = states.NOSTATE
                    utils.process_event(fsm, server, event='error')
                    self._rollback_servers_quota(context, 1)

        # Issue delete request to driver only if server is associated with
        # a underlying node.
        if server.node_uuid:
            do_delete_server(server)

        server.power_state = states.NOSTATE
        utils.process_event(fsm, server, event='done')
        server.destroy()
        notifications.notify_about_server_action(
            context, server, self.host,
            action=fields.NotificationAction.DELETE,
            phase=fields.NotificationPhase.END)
        LOG.info("Deleted server successfully.")

    @wrap_server_fault
    def set_power_state(self, context, server, state):
        """Set power state for the specified server."""

        fsm = utils.get_state_machine(start_state=server.status)

        @utils.synchronized(server.uuid)
        def do_set_power_state():
            LOG.debug('Power %(state)s called for server %(server)s',
                      {'state': state,
                       'server': server})
            self.driver.set_power_state(context, server, state)

        try:
            do_set_power_state()
            server.power_state = self.driver.get_power_state(context,
                                                             server.uuid)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.exception("Set server power state to %(state)s failed, "
                              "the reason: %(reason)s",
                              {"state": state, "reason": six.text_type(e)})
                server.power_state = self.driver.get_power_state(context,
                                                                 server.uuid)
                if state in ['reboot', 'soft_reboot'] \
                        and server.power_state != states.POWER_ON:
                    utils.process_event(fsm, server, event='error')
                else:
                    utils.process_event(fsm, server, event='fail')

                action = POWER_NOTIFICATION_MAP[state]
                notifications.notify_about_server_action(
                    context, server, self.host,
                    action=action,
                    phase=fields.NotificationPhase.ERROR,
                    exception=e)

        utils.process_event(fsm, server, event='done')
        LOG.info('Successfully set node power state: %s',
                 state, server=server)

    def _rebuild_server(self, context, server, preserve_ephemeral):
        """Perform rebuild action on the specified server."""

        self.driver.rebuild(context, server, preserve_ephemeral)

    @wrap_server_fault
    def rebuild_server(self, context, server, preserve_ephemeral):
        """Destroy and re-make this server.

        :param context: mogan request context
        :param server: server object
        :param preserve_ephemeral: whether preserve ephemeral partition
        """
        LOG.debug('Rebuilding server: %s', server)

        notifications.notify_about_server_action(
            context, server, self.host,
            action=fields.NotificationAction.REBUILD,
            phase=fields.NotificationPhase.START)

        fsm = utils.get_state_machine(start_state=server.status)

        try:
            self._rebuild_server(context, server, preserve_ephemeral)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                utils.process_event(fsm, server, event='error')
                LOG.error("Rebuild server %(uuid)s failed."
                          "Exception: %(exception)s",
                          {"uuid": server.uuid,
                           "exception": e})
                notifications.notify_about_server_action(
                    context, server, self.host,
                    action=fields.NotificationAction.REBUILD,
                    phase=fields.NotificationPhase.ERROR, exception=e)
        utils.process_event(fsm, server, event='done')
        notifications.notify_about_server_action(
            context, server, self.host,
            action=fields.NotificationAction.REBUILD,
            phase=fields.NotificationPhase.END)
        LOG.info('Server was successfully rebuilt')

    def get_serial_console(self, context, server, console_type):
        """Returns connection information for a serial console."""

        LOG.debug("Getting serial console for server %s", server.uuid)

        token = uuidutils.generate_uuid()
        if console_type == 'shellinabox':
            access_url = '%s?token=%s' % (
                CONF.serial_console.shellinabox_base_url, token)
        elif console_type == 'socat':
            access_url = '%s?token=%s' % (
                CONF.serial_console.socat_base_url, token)
        else:
            raise exception.ConsoleTypeInvalid(console_type=console_type)

        console_url = self.driver.get_serial_console(
            context, server, console_type)
        return {'access_url': access_url,
                'token': token,
                'host': console_url.hostname,
                'port': console_url.port,
                'internal_access_path': None}

    @wrap_server_fault
    def attach_interface(self, context, server, net_id, port_id):
        # prepare port to be attached
        if port_id:
            LOG.debug("Attaching port %(port_id)s to server %(server)s",
                      {'port_id': port_id, 'server': server})
            try:
                vif_port = self.network_api.show_port(context, port_id)
            except Exception:
                raise exception.PortNotFound(port_id=port_id)
            try:
                self.network_api.check_port_availability(vif_port)
                self.network_api.bind_port(context, port_id, server)
            except Exception as e:
                raise exception.InterfaceAttachFailed(message=six.text_type(e))
            preserve_on_delete = True

        else:
            LOG.debug("Attaching network interface %(net_id)s to server "
                      "%(server)s", {'net_id': net_id, 'server': server})
            vif_port = self.network_api.create_port(context, net_id,
                                                    server.uuid)
            preserve_on_delete = False

        try:
            self.driver.plug_vif(server.node_uuid, vif_port['id'])
            nics_obj = objects.ServerNics(context)
            nic_dict = {'port_id': vif_port['id'],
                        'network_id': vif_port['network_id'],
                        'mac_address': vif_port['mac_address'],
                        'fixed_ips': vif_port['fixed_ips'],
                        'preserve_on_delete': preserve_on_delete,
                        'server_uuid': server.uuid}
            nics_obj.objects.append(objects.ServerNic(
                context, **nic_dict))
            server.nics = nics_obj
            server.save()
        except Exception as e:
            if port_id:
                self.network_api.unbind_port(context, vif_port)
            else:
                self.network_api.delete_port(context, vif_port['id'],
                                             server.uuid)
            raise exception.InterfaceAttachFailed(message=six.text_type(e))
        LOG.info('Attaching interface successfully')

    def _detach_interface(self, context, server, port_id, preserve=False):
        try:
            self.driver.unplug_vif(context, server, port_id)
        except exception.MoganException as e:
            LOG.warning("Detach interface failed, port_id=%(port_id)s,"
                        " reason: %(msg)s",
                        {'port_id': port_id, 'msg': six.text_type(e)})
            raise exception.InterfaceDetachFailed(server_uuid=server.uuid)
        else:
            try:
                if preserve:
                    vif_port = self.network_api.show_port(context, port_id)
                    self.network_api.unbind_port(context, vif_port)
                else:
                    self.network_api.delete_port(context, port_id, server.uuid)
            except Exception as e:
                raise exception.InterfaceDetachFailed(server_uuid=server.uuid)

        try:
            objects.ServerNic.delete_by_port_id(context, port_id)
        except exception.PortNotFound:
            pass

    @wrap_server_fault
    def detach_interface(self, context, server, port_id):
        LOG.debug("Detaching interface %(port_id)s from server %(server)s",
                  {'port_id': port_id, 'server': server.uuid})
        try:
            db_nic = objects.ServerNic.get_by_port_id(context, port_id)
            preserve = db_nic['preserve_on_delete']
        except exception.PortNotFound:
            preserve = False
        self._detach_interface(context, server, port_id, preserve)

        LOG.info('Interface was successfully detached')

    def list_compute_nodes(self, context):
        nodes = self.scheduler_client.reportclient \
            .get_nodes_from_resource_providers()
        return nodes

    def list_aggregate_nodes(self, context, aggregate_uuid):
        nodes = self.scheduler_client.reportclient \
            .get_nodes_from_aggregate(aggregate_uuid)
        return nodes

    def add_aggregate_node(self, context, aggregate_uuid, node):
        LOG.info('Adding node to aggregate: %s', aggregate_uuid)
        self.scheduler_client.reportclient \
            .update_aggregate_node(aggregate_uuid, node, 'add')

    def remove_aggregate_node(self, context, aggregate_uuid, node):
        LOG.info('Removing node from aggregate: %s', aggregate_uuid)
        self.scheduler_client.reportclient \
            .update_aggregate_node(aggregate_uuid, node, 'remove')

    def remove_aggregate(self, context, aggregate_uuid):
        LOG.info('Removing aggregate: %s', aggregate_uuid)
        self.scheduler_client.reportclient \
            .remove_aggregate(aggregate_uuid)

    def list_node_aggregates(self, context, node):
        aggregates = self.scheduler_client.reportclient \
            .get_aggregates_from_node(node)
        return aggregates

    def get_manageable_servers(self, context):
        return self.driver.get_manageable_nodes()

    def _manage_server(self, context, server, node):
        # Create the rp
        resource_class = sched_utils.ensure_resource_class_name(
            node['resource_class'])
        inventory = self.driver.get_node_inventory(node)
        inventory_data = {resource_class: inventory}
        # TODO(liusheng) need to ensure the inventory being rollback if
        # putting allocations failed.
        self.scheduler_client.set_inventory_for_provider(
            node['uuid'], node['name'] or node['uuid'], inventory_data,
            resource_class)
        # Allocate the resource
        self.scheduler_client.reportclient.put_allocations(
            node['uuid'], server.uuid, {resource_class: 1},
            server.project_id, server.user_id)

        LOG.info("Starting to manage bare metal node %(node_uuid)s for "
                 "server %(uuid)s",
                 {"node_uuid": node['uuid'], "uuid": server.uuid})

        nics_obj = objects.ServerNics(context)
        # Check networks
        all_ports = node['ports'] + node['portgroups']
        for vif in all_ports:
            neutron_port_id = vif['neutron_port_id']
            if neutron_port_id is not None:
                port_dict = self.network_api.show_port(
                    context, neutron_port_id)

                nic_dict = {'port_id': port_dict['id'],
                            'network_id': port_dict['network_id'],
                            'mac_address': port_dict['mac_address'],
                            'fixed_ips': port_dict['fixed_ips'],
                            'preserve_on_delete': False,
                            'server_uuid': server.uuid}

                # Check if the neutron port's mac address matches the port
                # address of bare metal nics.
                if nic_dict['mac_address'] != vif['address']:
                    msg = (
                        _("The address of neutron port %(port_id)s is "
                          "%(address)s, but the nic address of bare metal "
                          "node %(node_uuid)s is %(nic_address)s.") %
                        {"port_id": nic_dict['port_id'],
                         "address": nic_dict['mac_address'],
                         "node_uuid": node['uuid'],
                         "nic_address": vif['address']})
                    raise exception.NetworkError(msg)

                self.network_api.bind_port(context, neutron_port_id, server)
                server_nic = objects.ServerNic(context, **nic_dict)
                nics_obj.objects.append(server_nic)

        # Manage the bare metal node
        self.driver.manage(server, node['uuid'])

        image_uuid = node.get('image_source')
        if not uuidutils.is_uuid_like(image_uuid):
            image_uuid = None

        # Set the server information
        server.image_uuid = image_uuid
        server.node_uuid = node['uuid']
        server.node = node['name']
        server.nics = nics_obj
        server.power_state = node['power_state']
        server.launched_at = timeutils.utcnow()
        server.status = states.ACTIVE
        server.system_metadata = {"managed_server": "True"}
        if server.power_state == states.POWER_OFF:
            server.status = states.STOPPED

    def manage_server(self, context, server, node_uuid):
        try:
            node = self.driver.get_manageable_node(node_uuid)
            self._manage_server(context, server, node)
        except Exception:
            with excutils.save_and_reraise_exception():
                self._rollback_servers_quota(context, -1)
        # Save the server information
        try:
            server.create()
        except Exception:
            with excutils.save_and_reraise_exception():
                self._rollback_servers_quota(context, -1)
                self.driver.unmanage(server, node['uuid'])

        LOG.info("Manage server %s successfully.", server.uuid)
        return server
