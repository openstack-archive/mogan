# Copyright 2016 Huawei Technologies Co.,LTD.
# Copyright 2014 Red Hat, Inc.
# Copyright 2013 Hewlett-Packard Development Company, L.P.
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

'''
Leverages nova/virt/ironic/driver.py
'''

import collections

from ironicclient import exc as ironic_exc
from ironicclient import exceptions as client_e
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import excutils
import six
import six.moves.urllib.parse as urlparse

from mogan.baremetal import driver as base_driver
from mogan.baremetal.ironic import ironic_states
from mogan.common import exception
from mogan.common.i18n import _
from mogan.common import ironic
from mogan.common import states
from mogan.conf import CONF


LOG = logging.getLogger(__name__)

_POWER_STATE_MAP = {
    ironic_states.POWER_ON: states.POWER_ON,
    ironic_states.NOSTATE: states.NOSTATE,
    ironic_states.POWER_OFF: states.POWER_OFF,
}

_UNPROVISION_STATES = (ironic_states.ACTIVE, ironic_states.DEPLOYFAIL,
                       ironic_states.ERROR, ironic_states.DEPLOYWAIT,
                       ironic_states.DEPLOYING)

_NODE_FIELDS = ('uuid', 'power_state', 'target_power_state', 'provision_state',
                'target_provision_state', 'last_error', 'maintenance',
                'properties', 'instance_uuid')

TENANT_VIF_KEY = 'tenant_vif_port_id'

VIF_KEY = 'vif_port_id'


def map_power_state(state):
    try:
        return _POWER_STATE_MAP[state]
    except KeyError:
        LOG.warning("Power state %s not found.", state)
        return states.NOSTATE


def _log_ironic_polling(what, node, server):
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
                   tgt_prov_state=tgt_prov_state),
              server=server)


class IronicDriver(base_driver.BaseEngineDriver):

    def __init__(self):
        super(IronicDriver, self).__init__()
        self.ironicclient = ironic.IronicClientWrapper()

    def _get_node(self, node_uuid):
        """Get a node by its UUID."""
        return self.ironicclient.call('node.get', node_uuid,
                                      fields=_NODE_FIELDS)

    def _validate_server_and_node(self, server):
        """Get the node associated with the server.

        Check with the Ironic service that this server is associated with a
        node, and return the node.
        """
        try:
            return self.ironicclient.call('node.get_by_instance_uuid',
                                          server.uuid, fields=_NODE_FIELDS)
        except ironic_exc.NotFound:
            raise exception.ServerNotFound(server=server.uuid)

    def _node_resource(self, node):
        """Helper method to create resource dict from node stats."""

        dic = {
            'resource_class': str(node.resource_class),
            'ports': node.ports,
            'portgroups': node.portgroups,
            'name': node.name,
            'power_state': node.power_state,
            'provision_state': node.provision_state,
            'image_source': node.instance_info.get('image_source'),
        }

        return dic

    def _port_resource(self, port):
        """Helper method to create resource dict from port stats."""

        neutron_port_id = (port.internal_info.get(TENANT_VIF_KEY) or
                           port.extra.get(VIF_KEY))
        dic = {
            'address': port.address,
            'uuid': port.uuid,
            'neutron_port_id': neutron_port_id,
        }
        return dic

    def _portgroup_resource(self, portgroup):
        """Helper method to create resource dict from portgroup stats. """

        neutron_port_id = (portgroup.internal_info.get(TENANT_VIF_KEY) or
                           portgroup.extra.get(VIF_KEY))
        dic = {
            'address': portgroup.address,
            'uuid': portgroup.uuid,
            'mode': portgroup.mode,
            'neutron_port_id': neutron_port_id,
        }
        return dic

    def _add_server_info_to_node(self, node, server, preserve_ephemeral=None,
                                 partitions=None):
        patch = list()
        # Associate the node with a server
        patch.append({'path': '/instance_uuid', 'op': 'add',
                      'value': server.uuid})
        # Add the required fields to deploy a node.
        patch.append({'path': '/instance_info/image_source', 'op': 'add',
                      'value': server.image_uuid})

        root_gb = node.properties.get('local_gb', 0)

        if preserve_ephemeral is not None:
            patch.append({'path': '/instance_info/preserve_ephemeral',
                          'op': 'add', 'value': str(preserve_ephemeral)})
        if partitions:
            patch.append({'path': '/instance_info/ephemeral_gb', 'op': 'add',
                          'value': str(partitions.get('ephemeral_gb', 0))})
            patch.append({'path': '/instance_info/swap_mb', 'op': 'add',
                          'value': str(partitions.get('swap_mb', 0))})
            # Local boot support with partition images, **must** contain
            # ``grub2`` installed within it
            patch.append({'path': '/instance_info/capabilities',
                          'op': 'add', 'value': '{"boot_option": "local"}'})

            # If partitions is not None, use the root_gb in partitions instead
            root_gb = partitions.get('root_gb', root_gb)

        # root_gb is required not optional
        patch.append({'path': '/instance_info/root_gb', 'op': 'add',
                      'value': str(root_gb)})

        try:
            # FIXME(lucasagomes): The "retry_on_conflict" parameter was added
            # to basically causes the deployment to fail faster in case the
            # node picked by the scheduler is already associated with another
            # server due bug #1341420.
            self.ironicclient.call('node.update', node.uuid, patch,
                                   retry_on_conflict=False)
        except ironic_exc.BadRequest:
            msg = (_("Failed to add deploy parameters on node %(node)s "
                     "when provisioning the server %(server)s")
                   % {'node': node.uuid, 'server': server.uuid})
            LOG.error(msg)
            raise exception.ServerDeployFailure(msg)

    def _remove_server_info_from_node(self, node, server):
        patch = [{'path': '/instance_info', 'op': 'remove'},
                 {'path': '/instance_uuid', 'op': 'remove'}]
        try:
            self.ironicclient.call('node.update', node.uuid, patch)
        except ironic_exc.BadRequest as e:
            LOG.warning("Failed to remove deploy parameters from node "
                        "%(node)s when unprovisioning the server "
                        "%(server)s: %(reason)s",
                        {'node': node.uuid, 'server': server.uuid,
                         'reason': six.text_type(e)})

    def _wait_for_active(self, server):
        """Wait for the node to be marked as ACTIVE in Ironic."""
        server.refresh()
        if server.status in (states.DELETING, states.ERROR, states.DELETED):
            raise exception.ServerDeployAborted(
                _("Server %s provisioning was aborted") % server.uuid)

        node = self._validate_server_and_node(server)
        if node.provision_state == ironic_states.ACTIVE:
            # job is done
            LOG.debug("Ironic node %(node)s is now ACTIVE",
                      dict(node=node.uuid), server=server)
            raise loopingcall.LoopingCallDone()

        if node.target_provision_state in (ironic_states.DELETED,
                                           ironic_states.AVAILABLE):
            # ironic is trying to delete it now
            raise exception.ServerNotFound(server=server.uuid)

        if node.provision_state in (ironic_states.NOSTATE,
                                    ironic_states.AVAILABLE):
            # ironic already deleted it
            raise exception.ServerNotFound(server=server.uuid)

        if node.provision_state == ironic_states.DEPLOYFAIL:
            # ironic failed to deploy
            msg = (_("Failed to provision server %(server)s: %(reason)s")
                   % {'server': server.uuid, 'reason': node.last_error})
            raise exception.ServerDeployFailure(msg)

        _log_ironic_polling('become ACTIVE', node, server)

    def _wait_for_power_state(self, server, message):
        """Wait for the node to complete a power state change."""
        node = self._validate_server_and_node(server)

        if node.target_power_state == ironic_states.NOSTATE:
            raise loopingcall.LoopingCallDone()

        _log_ironic_polling(message, node, server)

    def get_portgroups_and_ports(self, node_uuid):
        """List ports and portgroups of a node."""
        free_ports = []
        ports_by_portgroup = collections.defaultdict(list)
        ports = self.ironicclient.call("node.list_ports", node_uuid,
                                       detail=True)
        for p in ports:
            if p.portgroup_uuid is None:
                free_ports.append(p)
            else:
                ports_by_portgroup[p.portgroup_uuid].append(p)

        portgroups = self.ironicclient.call("portgroup.list", node=node_uuid)
        for pg in portgroups:
            if ports_by_portgroup[pg.uuid]:
                free_ports.append(pg)

        return free_ports

    def plug_vif(self, node_uuid, port_id):
        self.ironicclient.call("node.vif_attach", node_uuid, port_id)

    def unplug_vif(self, context, server, port_id):
        LOG.debug("unplug: server_uuid=%(uuid)s vif=%(server_nics)s "
                  "port=%(port_id)s",
                  {'uuid': server.uuid,
                   'server_nics': str(server.nics),
                   'port_id': port_id})
        node = self._get_node(server.node_uuid)
        self._unplug_vif(node, port_id)

    def _unplug_vif(self, node, port_id):
        try:
            self.ironicclient.call("node.vif_detach", node.uuid,
                                   port_id)
        except ironic_exc.BadRequest:
            LOG.debug(
                "VIF %(vif)s isn't attached to Ironic node %(node)s",
                {'vif': port_id, 'node': node.uuid})

    def spawn(self, context, server, configdrive_value, partitions):
        """Deploy a server.

        :param context: The security context.
        :param server: The server object.
        :param configdrive_value: configdrive value to be injected.
        :param partitions: root disk partitions.
        """
        LOG.debug('Spawn called for server', server=server)

        # The engine manager is meant to know the node uuid, so missing uuid
        # is a significant issue. It may mean we've been passed the wrong data.
        node_uuid = server.node_uuid
        if not node_uuid:
            raise ironic_exc.BadRequest(
                _("Ironic node uuid not supplied to "
                  "driver for server %s.") % server.uuid)

        # add server info to node
        node = self._get_node(node_uuid)
        self._add_server_info_to_node(node, server, None, partitions)
        # validate we are ready to do the deploy
        validate_chk = self.ironicclient.call("node.validate", node_uuid)
        if (not validate_chk.deploy.get('result')
                or not validate_chk.power.get('result')):
            raise exception.ValidationError(_(
                "Ironic node: %(id)s failed to validate."
                " (deploy: %(deploy)s, power: %(power)s)")
                % {'id': server.node_uuid,
                   'deploy': validate_chk.deploy,
                   'power': validate_chk.power})

        # trigger the node deploy
        try:
            self.ironicclient.call("node.set_provision_state", node_uuid,
                                   ironic_states.ACTIVE,
                                   configdrive=configdrive_value)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                msg = ("Failed to request Ironic to provision server "
                       "%(server)s: %(reason)s",
                       {'server': server.uuid,
                        'reason': six.text_type(e)})
                LOG.error(msg)

        timer = loopingcall.FixedIntervalLoopingCall(self._wait_for_active,
                                                     server)
        try:
            timer.start(interval=CONF.ironic.api_retry_interval).wait()
            LOG.info('Successfully provisioned Ironic node %s',
                     node.uuid, server=server)
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.error("Error deploying server %(server)s on "
                          "baremetal node %(node)s.",
                          {'server': server.uuid,
                           'node': node_uuid})

    def _unprovision(self, server, node):
        """This method is called from destroy() to unprovision
        already provisioned node after required checks.
        """
        try:
            self.ironicclient.call("node.set_provision_state", node.uuid,
                                   "deleted")
        except Exception as e:
            # if the node is already in a deprovisioned state, continue
            # This should be fixed in Ironic.
            # TODO(deva): This exception should be added to
            #             python-ironicclient and matched directly,
            #             rather than via __name__.
            if getattr(e, '__name__', None) != 'ServerDeployFailure':
                raise

        # using a dict because this is modified in the local method
        data = {'tries': 0}

        def _wait_for_provision_state():
            try:
                node = self._validate_server_and_node(server)
            except exception.ServerNotFound:
                LOG.debug("Server already removed from Ironic",
                          server=server)
                raise loopingcall.LoopingCallDone()
            if node.provision_state in (ironic_states.NOSTATE,
                                        ironic_states.CLEANING,
                                        ironic_states.CLEANWAIT,
                                        ironic_states.CLEANFAIL,
                                        ironic_states.AVAILABLE):
                # From a user standpoint, the node is unprovisioned. If a node
                # gets into CLEANFAIL state, it must be fixed in Ironic, but we
                # can consider the server unprovisioned.
                LOG.debug("Ironic node %(node)s is in state %(state)s, "
                          "server is now unprovisioned.",
                          dict(node=node.uuid, state=node.provision_state),
                          server=server)
                raise loopingcall.LoopingCallDone()

            if data['tries'] >= CONF.ironic.api_max_retries + 1:
                msg = (_("Error destroying the server on node %(node)s. "
                         "Provision state still '%(state)s'.")
                       % {'state': node.provision_state,
                          'node': node.uuid})
                LOG.error(msg)
                raise exception.MoganException(msg)
            else:
                data['tries'] += 1

            _log_ironic_polling('unprovision', node, server)

        # wait for the state transition to finish
        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_provision_state)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()

    def destroy(self, context, server):
        """Destroy the specified server, if it can be found.

        :param context: The security context.
        :param server: The server object.
        """
        LOG.debug('Destroy called for server', server=server)
        try:
            node = self._validate_server_and_node(server)
        except exception.ServerNotFound:
            LOG.warning("Destroy called on non-existing server %s.",
                        server.uuid)
            return

        if node.provision_state in _UNPROVISION_STATES:
            self._unprovision(server, node)
        else:
            # NOTE(hshiina): if spawn() fails before ironic starts
            #                provisioning, server information should be
            #                removed from ironic node.
            self._remove_server_info_from_node(node, server)

        LOG.info('Successfully unprovisioned Ironic node %s',
                 node.uuid, server=server)

    def _get_manageable_nodes(self):
        """Helper function to return the list of manageable nodes.

        If unable to connect ironic server, an empty list is returned.

        :returns: a list of raw node from ironic

        """

        # Retrieve nodes
        params = {
            'maintenance': False,
            'detail': True,
            'provision_state': ironic_states.ACTIVE,
            'associated': False,
            'limit': 0
        }
        try:
            node_list = self.ironicclient.call("node.list", **params)
        except client_e.ClientException as e:
            LOG.exception("Could not get nodes from ironic. Reason: "
                          "%(detail)s", {'detail': six.text_type(e)})
            raise e

        # Retrive ports
        params = {
            'limit': 0,
            'fields': ('uuid', 'node_uuid', 'extra', 'address',
                       'internal_info')
        }

        try:
            port_list = self.ironicclient.call("port.list", **params)
        except client_e.ClientException as e:
            LOG.exception("Could not get ports from ironic. Reason: "
                          "%(detail)s", {'detail': six.text_type(e)})
            port_list = []

        # Retrive portgroups
        try:
            portgroup_list = self.ironicclient.call("portgroup.list", **params)
        except client_e.ClientException as e:
            LOG.exception("Could not get portgroups from ironic. Reason: "
                          "%(detail)s", {'detail': six.text_type(e)})
            portgroup_list = []

        node_resources = {}
        for node in node_list:
            if node.resource_class is None:
                continue
            # Add ports to the associated node
            node.ports = [self._port_resource(port)
                          for port in port_list
                          if node.uuid == port.node_uuid]
            # Add portgroups to the associated node
            node.portgroups = [self._portgroup_resource(portgroup)
                               for portgroup in portgroup_list
                               if node.uuid == portgroup.node_uuid]
            node_resources[node.uuid] = self._node_resource(node)
        return node_resources

    def get_maintenance_node_list(self):
        """Helper function to return the list of maintenance nodes.

        If unable to connect ironic server, an empty list is returned.

        :returns: a list of maintenance node from ironic

        """
        params = {
            'associated': True,
            'fields': ('instance_uuid', 'maintenance'),
            'limit': 0
        }
        try:
            node_list = self.ironicclient.call("node.list", **params)
        except client_e.ClientException as e:
            LOG.exception("Could not get nodes from ironic. Reason: "
                          "%(detail)s", {'detail': six.text_type(e)})
            node_list = []
        return node_list

    def get_nodes_power_state(self):
        """Helper function to return the node power states.

        If unable to connect ironic server, an empty list is returned.

        :returns: a list of node power states from ironic

        """
        params = {
            'maintenance': False,
            'associated': True,
            'fields': ('instance_uuid', 'power_state', 'target_power_state'),
            'limit': 0
        }
        try:
            node_list = self.ironicclient.call("node.list", **params)
        except client_e.ClientException as e:
            LOG.exception("Could not get nodes from ironic. Reason: "
                          "%(detail)s", {'detail': six.text_type(e)})
            node_list = []
        return node_list

    def get_power_state(self, context, server_uuid):
        try:
            node = self.ironicclient.call('node.get_by_instance_uuid',
                                          server_uuid,
                                          fields=('power_state',))
            return map_power_state(node.power_state)
        except client_e.NotFound:
            return map_power_state(ironic_states.NOSTATE)

    def set_power_state(self, context, server, state):
        """Set power state on the specified server.

        :param context: The security context.
        :param server: The server object.
        """
        node = self._validate_server_and_node(server)
        if state == "soft_off":
            self.ironicclient.call("node.set_power_state",
                                   node.uuid, "off", soft=True)
        elif state == "soft_reboot":
            self.ironicclient.call("node.set_power_state",
                                   node.uuid, "reboot", soft=True)
        else:
            self.ironicclient.call("node.set_power_state",
                                   node.uuid, state)
        timer = loopingcall.FixedIntervalLoopingCall(
            self._wait_for_power_state, server, state)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()

    def rebuild(self, context, server, preserve_ephemeral):
        """Rebuild/redeploy a server.

        :param context: The security context.
        :param server: The server object.
        :param preserve_ephemeral: whether preserve ephemeral partition
        """
        LOG.debug('Rebuild called for server', server=server)

        node_uuid = server.node_uuid
        node = self._get_node(node_uuid)
        self._add_server_info_to_node(node, server, preserve_ephemeral)
        # trigger the node rebuild
        try:
            self.ironicclient.call("node.set_provision_state",
                                   node_uuid,
                                   ironic_states.REBUILD)
        except (ironic_exc.InternalServerError,
                ironic_exc.BadRequest) as e:
            msg = (_("Failed to request Ironic to rebuild server "
                     "%(server)s: %(reason)s") % {'server': server.uuid,
                                                  'reason': six.text_type(e)})
            raise exception.ServerDeployFailure(msg)

        # Although the target provision state is REBUILD, it will actually go
        # to ACTIVE once the redeploy is finished.
        timer = loopingcall.FixedIntervalLoopingCall(self._wait_for_active,
                                                     server)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()
        LOG.info('Server was successfully rebuilt', server=server)

    def _get_node_console_with_reset(self, server):
        """Acquire console information for a server.

        If the console is enabled, the console will be re-enabled
        before returning.

        :param server: mogan server object
        :return: a dictionary with below values
            { 'node': ironic node
              'console_info': node console info }
        :raise ConsoleNotAvailable: if console is unavailable
            for the server
        """
        node = self._validate_server_and_node(server)
        node_uuid = node.uuid

        def _get_console():
            """Request ironicclient to acquire node console."""
            try:
                return self.ironicclient.call('node.get_console', node_uuid)
            except (ironic_exc.InternalServerError,
                    ironic_exc.BadRequest) as e:
                LOG.error('Failed to acquire console information for '
                          'node %(server)s: %(reason)s',
                          {'server': node_uuid,
                           'reason': e})
                raise exception.ConsoleNotAvailable()

        def _wait_state(state):
            """Wait for the expected console mode to be set on node."""
            console = _get_console()
            if console['console_enabled'] == state:
                raise loopingcall.LoopingCallDone(retvalue=console)

            _log_ironic_polling('set console mode', node, server)

            # Return False to start backing off
            return False

        def _enable_console(mode):
            """Request ironicclient to enable/disable node console."""
            try:
                self.ironicclient.call(
                    'node.set_console_mode', node_uuid, mode)
            except (ironic_exc.InternalServerError,  # Validations
                    ironic_exc.BadRequest) as e:  # Maintenance
                LOG.error('Failed to set console mode to "%(mode)s" '
                          'for node %(node)s: %(reason)s',
                          {'mode': mode,
                           'node': node_uuid,
                           'reason': e})
                raise exception.ConsoleNotAvailable()

            # Waiting for the console state to change (disabled/enabled)
            try:
                timer = loopingcall.BackOffLoopingCall(_wait_state, state=mode)
                return timer.start(
                    starting_interval=1, timeout=10, jitter=0.5).wait()
            except loopingcall.LoopingCallTimeOut:
                LOG.error('Timeout while waiting for console mode to be '
                          'set to "%(mode)s" on node %(node)s',
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
            return {'node': node,
                    'console_info': console['console_info']}
        else:
            LOG.debug('Console is disabled for node %s', node_uuid)
            raise exception.ConsoleNotAvailable()

    def get_serial_console(self, context, server, console_type):
        """Acquire serial console information.

        :param context: request context
        :param server: mogan server object
        :return: console url
        :raise ConsoleTypeUnavailable: if serial console is unavailable
            for the server
        """
        LOG.debug('Getting serial console for server %s', server.uuid)
        try:
            result = self._get_node_console_with_reset(server)
        except exception.ConsoleNotAvailable:
            raise exception.ConsoleTypeUnavailable(console_type=console_type)

        node = result['node']
        console_info = result['console_info']

        if console_info["type"] != console_type:
            LOG.warning('Console type "%(type)s" (of ironic node '
                        '%(node)s) does not match with the given type',
                        {'type': console_info["type"],
                         'node': node.uuid},
                        server=server)
            raise exception.ConsoleTypeUnavailable(console_type=console_type)

        # Parse and check the console url
        return urlparse.urlparse(console_info["url"])

    def get_available_nodes(self):
        """Helper function to return the list of all nodes.

        If unable to connect ironic server, an empty list is returned.

        :returns: a list of normal nodes from ironic

        """
        normal_nodes = []
        params = {
            'detail': True,
            'limit': 0,
            'maintenance': False
        }
        try:
            node_list = self.ironicclient.call("node.list", **params)
        except client_e.ClientException as e:
            LOG.exception("Could not get nodes from ironic. Reason: "
                          "%(detail)s", {'detail': e.message})
            return []

        bad_power_states = [ironic_states.ERROR, ironic_states.NOSTATE]
        bad_provision_states = [ironic_states.ENROLL]
        # keep NOSTATE around for compatibility
        good_provision_states = [
            ironic_states.AVAILABLE, ironic_states.NOSTATE]
        for node_obj in node_list:
            if ((node_obj.resource_class is None) or
                node_obj.power_state in bad_power_states or
                node_obj.provision_state in bad_provision_states or
                (node_obj.provision_state in good_provision_states and
                    node_obj.instance_uuid is not None)):
                continue
            normal_nodes.append(node_obj)
        return normal_nodes

    @staticmethod
    def get_node_inventory(node):
        """Get the inventory of a node.

        :param node: server to get its inventory data.
        """
        return {'total': 1,
                'reserved': 0,
                'min_unit': 1,
                'max_unit': 1,
                'step_size': 1,
                'allocation_ratio': 1.0,
                }

    @staticmethod
    def is_node_consumable(node):
        """Check if a node is consumable

        :param node: node to check if it is consumable.
        """
        return (not node.instance_uuid and node.provision_state ==
                ironic_states.AVAILABLE)

    def get_node_name(self, node):
        """Get the name of a node.

        :param node: the uuid of the node.
        """
        try:
            node = self.ironicclient.call(
                'node.get', node, fields=('name',))
        except Exception:
            return None

        return node.name

    def get_manageable_nodes(self):
        nodes = self._get_manageable_nodes()
        manageable_nodes = []
        for node_uuid, node in nodes.items():
            manageable_nodes.append(
                {'uuid': node_uuid,
                 'name': node.get('name'),
                 'resource_class': node.get('resource_class'),
                 'power_state': node.get('power_state'),
                 'provision_state': node.get('provision_state'),
                 'ports': node.get('ports'),
                 'portgroups': node.get('portgroups'),
                 'image_source': node.get('image_source')})
        return manageable_nodes

    def get_manageable_node(self, node_uuid):
        try:
            node = self.ironicclient.call('node.get', node_uuid)
        except ironic_exc.NotFound:
            raise exception.NodeNotFound(node=node_uuid)

        if (node.instance_uuid is not None or
            node.provision_state != ironic_states.ACTIVE or
                node.resource_class is None):
                LOG.error("The node's instance uuid is %(instance_uuid)s, "
                          "node's provision state is %(provision_state)s, "
                          "node's resource class is %(resource_class)s",
                          {"instance_uuid": node.instance_uuid,
                           "provision_state": node.provision_state,
                           "resource_class": node.resource_class})
                raise exception.NodeNotAllowedManaged(node_uuid=node_uuid)

        # Retrieves ports
        params = {
            'limit': 0,
            'fields': ('uuid', 'node_uuid', 'extra', 'address',
                       'internal_info')
        }

        port_list = self.ironicclient.call("port.list", **params)
        portgroup_list = self.ironicclient.call("portgroup.list", **params)

        # Add ports to the associated node
        node.ports = [self._port_resource(port)
                      for port in port_list
                      if node.uuid == port.node_uuid]
        # Add portgroups to the associated node
        node.portgroups = [self._portgroup_resource(portgroup)
                           for portgroup in portgroup_list
                           if node.uuid == portgroup.node_uuid]
        node.power_state = map_power_state(node.power_state)
        manageable_node = self._node_resource(node)
        manageable_node['uuid'] = node_uuid

        return manageable_node

    def manage(self, server, node_uuid):
        """Manage an existing bare metal node.

        :param server: The bare metal server object.
        :param node_uuid: The manageable bare metal node uuid.
        """
        # Associate the node with a server
        patch = [{'path': '/instance_uuid', 'op': 'add', 'value': server.uuid}]

        try:
            self.ironicclient.call('node.update', node_uuid, patch,
                                   retry_on_conflict=False)
        except ironic_exc.BadRequest:
            msg = (_("Failed to update parameters on node %(node)s "
                     "when provisioning the server %(server)s")
                   % {'node': node_uuid, 'server': server.uuid})
            LOG.error(msg)
            raise exception.ServerDeployFailure(msg)

    def unmanage(self, server, node_uuid):
        """unmanage a bare metal node.

         :param server: The bare metal server object.
         :param node_uuid: The manageable bare metal node uuid.
         """
        patch = [{'path': '/instance_uuid', 'op': 'remove'}]

        try:
            self.ironicclient.call('node.update', node_uuid, patch)
        except ironic_exc.BadRequest as e:
            LOG.warning("Failed to remove deploy parameters from node "
                        "%(node)s when unprovisioning the server "
                        "%(server)s: %(reason)s",
                        {'node': node_uuid, 'server': server.uuid,
                         'reason': six.text_type(e)})
