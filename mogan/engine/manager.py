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
import six.moves.urllib.parse as urlparse

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

LOG = log.getLogger(__name__)


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
            # Just retrun if we fail to get nodes maintenance state.
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
        ports = server.nics.get_port_ids()
        for port in ports:
            self.network_api.delete_port(context, port, server.uuid)

    def _rollback_servers_quota(self, context, number):
        reserve_opts = {'servers': number}
        reservations = self.quota.reserve(context, **reserve_opts)
        if reservations:
            self.quota.commit(context, reservations)

    @wrap_server_fault
    def create_server(self, context, server, requested_networks,
                      user_data, injected_files, key_pair, request_spec=None,
                      filter_properties=None):
        """Perform a deployment."""
        LOG.debug("Starting server...", server=server)
        notifications.notify_about_server_action(
            context, server, self.host,
            action=fields.NotificationAction.CREATE,
            phase=fields.NotificationPhase.START)

        fsm = utils.get_state_machine(start_state=server.status,
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
            server.node_uuid = node['node_uuid']
            server.save()
            # Add a retry entry for the selected node
            nodes = retry['nodes']
            nodes.append(node['node_uuid'])
        except Exception as e:
            with excutils.save_and_reraise_exception():
                utils.process_event(fsm, server, event='error')
                LOG.error("Created server %(uuid)s failed. "
                          "Exception: %(exception)s",
                          {"uuid": server.uuid,
                           "exception": e})

        try:
            flow_engine = create_server.get_flow(
                context,
                self,
                server,
                requested_networks,
                user_data,
                injected_files,
                key_pair,
                node['ports'],
                request_spec,
                filter_properties,
            )
        except Exception:
            with excutils.save_and_reraise_exception():
                utils.process_event(fsm, server, event='error')
                self._rollback_servers_quota(context, -1)
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
                LOG.error("Created server %(uuid)s failed."
                          "Exception: %(exception)s",
                          {"uuid": server.uuid,
                           "exception": e})
        else:
            # Advance the state model for the given event. Note that this
            # doesn't alter the server in any way. This may raise
            # InvalidState, if this event is not allowed in the current state.
            server.power_state = self.driver.get_power_state(context,
                                                             server.uuid)
            server.launched_at = timeutils.utcnow()
            utils.process_event(fsm, server, event='done')
            LOG.info("Created server %s successfully.", server.uuid)

    def _delete_server(self, context, server):
        """Delete a server

        :param context: mogan request context
        :param server: server object
        """
        # TODO(zhenguo): Add delete notification

        try:
            self.destroy_networks(context, server)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error("Destroy networks for server %(uuid)s failed. "
                          "Exception: %(exception)s",
                          {"uuid": server.uuid, "exception": e})

        self.driver.unplug_vifs(context, server)
        self.driver.destroy(context, server)

    @wrap_server_fault
    def delete_server(self, context, server):
        """Delete a server."""
        LOG.debug("Deleting server...")

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

    def set_power_state(self, context, server, state):
        """Set power state for the specified server."""

        fsm = utils.get_state_machine(start_state=server.status)

        @utils.synchronized(server.uuid)
        def do_set_power_state():
            LOG.debug('Power %(state)s called for server %(server)s',
                      {'state': state,
                       'server': server})
            self.driver.set_power_state(context, server, state)

        do_set_power_state()
        server.power_state = self.driver.get_power_state(context,
                                                         server.uuid)
        utils.process_event(fsm, server, event='done')
        LOG.info('Successfully set node power state: %s',
                 state, server=server)

    def _rebuild_server(self, context, server):
        """Perform rebuild action on the specified server."""

        # TODO(zhenguo): Add delete notification

        self.driver.rebuild(context, server)

    @wrap_server_fault
    def rebuild_server(self, context, server):
        """Destroy and re-make this server.

        :param context: mogan request context
        :param server: server object
        """

        LOG.debug('Rebuilding server', server=server)

        fsm = utils.get_state_machine(start_state=server.status)

        try:
            self._rebuild_server(context, server)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                utils.process_event(fsm, server, event='error')
                LOG.error("Rebuild server %(uuid)s failed."
                          "Exception: %(exception)s",
                          {"uuid": server.uuid,
                           "exception": e})

        utils.process_event(fsm, server, event='done')
        LOG.info('Server was successfully rebuilt', server=server)

    def get_serial_console(self, context, server):
        node_console_info = self.driver.get_serial_console_by_server(
            context, server)
        token = uuidutils.generate_uuid()
        access_url = '%s?token=%s' % (
            CONF.shellinabox_console.shellinabox_base_url, token)
        console_url = node_console_info['console_info']['url']
        parsed_url = urlparse.urlparse(console_url)
        return {'access_url': access_url,
                'token': token,
                'host': parsed_url.hostname,
                'port': parsed_url.port,
                'internal_access_path': None}

    def detach_interface(self, context, server, port_id):
        LOG.debug('Detaching interface', server=server)
        try:
            self.network_api.detach_neutron_port(context, server, port_id)
        except Exception:
            msg = _('Detach neutron port %(port_id) failed'
                    ) % ({'port_id': port_id})
            LOG.exception(msg)
        try:
            self.driver.unplug_vifs(context, server)
        except Exception:
            LOG.exception('Detach ironic port failed')

        LOG.info('Interface was successfully detached', server=server)


