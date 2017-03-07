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

from ironicclient import exc as ironic_exc
from ironicclient import exceptions as client_e
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import uuidutils
import six
import six.moves.urllib.parse as urlparse

from mogan.common import exception
from mogan.common.i18n import _
from mogan.common.i18n import _LE
from mogan.common.i18n import _LI
from mogan.common.i18n import _LW
from mogan.common import ironic
from mogan.common import states
from mogan.conf import CONF
from mogan.engine.baremetal import driver as base_driver
from mogan.engine.baremetal.ironic import ironic_states

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


class IronicDriver(base_driver.BaseEngineDriver):

    def __init__(self):
        super(IronicDriver, self).__init__()
        self.ironicclient = ironic.IronicClientWrapper()

    def map_power_state(self, state):
        try:
            return _POWER_STATE_MAP[state]
        except KeyError:
            LOG.warning(_LW("Power state %s not found."), state)
            return states.NOSTATE

    def get_power_state(self, instance_uuid):
        try:
            node = self.ironicclient.call('node.get_by_instance_uuid',
                                          instance_uuid,
                                          fields=('power_state',))
            return self.map_power_state(node.power_state)
        except client_e.NotFound:
            return self.map_power_state(ironic_states.NOSTATE)

    def get_ports_from_node(self, node_uuid, detail=True):
        """List the MAC addresses and the port types from a node."""
        ports = self.ironicclient.call("node.list_ports",
                                       node_uuid, detail=detail)
        portgroups = self.ironicclient.call("portgroup.list", node=node_uuid,
                                            detail=detail)
        return ports + portgroups

    def plug_vif(self, ironic_port_id, port_id):
        patch = [{'op': 'add',
                  'path': '/extra/vif_port_id',
                  'value': port_id}]
        self.ironicclient.call("port.update", ironic_port_id, patch)

    def unplug_vif(self, node_interface):
        patch = [{'op': 'remove',
                  'path': '/extra/vif_port_id'}]
        try:
            if 'vif_port_id' in node_interface.extra:
                self.ironicclient.call("port.update",
                                       node_interface.uuid, patch)
        except client_e.BadRequest:
            pass

    def set_instance_info(self, instance, node):

        patch = list()
        # Associate the node with an instance
        patch.append({'path': '/instance_uuid', 'op': 'add',
                      'value': instance.uuid})
        # Add the required fields to deploy a node.
        patch.append({'path': '/instance_info/image_source', 'op': 'add',
                      'value': instance.image_uuid})
        # TODO(zhenguo) Add partition support
        patch.append({'path': '/instance_info/root_gb', 'op': 'add',
                      'value': str(node.properties.get('local_gb', 0))})

        self.ironicclient.call("node.update", instance.node_uuid, patch)

    def unset_instance_info(self, instance):

        patch = [{'path': '/instance_info', 'op': 'remove'},
                 {'path': '/instance_uuid', 'op': 'remove'}]
        try:
            self.ironicclient.call("node.update", instance.node_uuid, patch)
        except ironic_exc.BadRequest as e:
            raise exception.Invalid(msg=six.text_type(e))

    def do_node_deploy(self, instance):
        # trigger the node deploy
        self.ironicclient.call("node.set_provision_state", instance.node_uuid,
                               ironic_states.ACTIVE)
        timer = loopingcall.FixedIntervalLoopingCall(self._wait_for_active,
                                                     instance)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()

    def _wait_for_active(self, instance):
        """Wait for the node to be marked as ACTIVE in Ironic."""
        instance.refresh()
        if instance.status in (states.DELETING, states.ERROR, states.DELETED):
            raise exception.InstanceDeployFailure(
                _("Instance %s provisioning was aborted") % instance.uuid)

        node = self.get_node_by_instance(instance.uuid)
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

    def get_node_by_instance(self, instance_uuid):
        fields = _NODE_FIELDS
        try:
            return self.ironicclient.call('node.get_by_instance_uuid',
                                          instance_uuid, fields=fields)
        except ironic_exc.NotFound:
            raise exception.NotFound

    def get_node(self, node_uuid, fields=None):
        if fields is None:
            fields = _NODE_FIELDS
        """Get a node by its UUID."""
        return self.ironicclient.call('node.get', node_uuid, fields=fields)

    def destroy(self, instance):
        node_uuid = instance.node_uuid
        # trigger the node destroy
        try:
            self.ironicclient.call("node.set_provision_state", node_uuid,
                                   ironic_states.DELETED)
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
                node = self.get_node_by_instance(instance.uuid)
            except exception.NotFound:
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

        LOG.info(_LI('Successfully destroyed Ironic node %s'), node_uuid)

    def validate_node(self, node_uuid):
        return self.ironicclient.call("node.validate", node_uuid)

    def get_available_node_list(self):
        """Helper function to return the list of nodes.

        If unable to connect ironic server, an empty list is returned.

        :returns: a list of raw node from ironic

        """
        params = {
            'maintenance': False,
            'detail': True,
            'provision_state': ironic_states.AVAILABLE,
            'associated': False,
            'limit': 0
        }
        try:
            node_list = self.ironicclient.call("node.list", **params)
        except client_e.ClientException as e:
            LOG.exception(_LE("Could not get nodes from ironic. Reason: "
                              "%(detail)s"), {'detail': e.message})
            node_list = []
        return node_list

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
            LOG.exception(_LE("Could not get nodes from ironic. Reason: "
                              "%(detail)s"), {'detail': e.message})
            node_list = []
        return node_list

    def get_node_power_states(self):
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
            LOG.exception(_LE("Could not get nodes from ironic. Reason: "
                              "%(detail)s"), {'detail': e.message})
            node_list = []
        return node_list

    def get_port_list(self):
        """Helper function to return the list of ports.

        If unable to connect ironic server, an empty list is returned.

        :returns: a list of raw port from ironic

        """
        params = {
            'limit': 0,
            'fields': ('uuid', 'node_uuid', 'extra', 'address')
        }

        try:
            port_list = self.ironicclient.call("port.list", **params)
        except client_e.ClientException as e:
            LOG.exception(_LE("Could not get ports from ironic. Reason: "
                              "%(detail)s"), {'detail': e.message})
            port_list = []
        return port_list

    def get_portgroup_list(self, **kwargs):
        """Helper function to return the list of portgroups.

        If unable to connect ironic server, an empty list is returned.

        :returns: a list of raw port from ironic

        """
        params = {
            'limit': 0,
            'fields': ('uuid', 'node_uuid', 'extra', 'address')
        }

        try:
            portgroup_list = self.ironicclient.call("portgroup.list", **params)
        except client_e.ClientException as e:
            LOG.exception(_LE("Could not get portgroups from ironic. Reason: "
                              "%(detail)s"), {'detail': e.message})
            portgroup_list = []
        return portgroup_list

    def set_power_state(self, instance, state):
        if state == "soft_off":
            self.ironicclient.call("node.set_power_state",
                                   instance.node_uuid, "off", soft=True)
        elif state == "soft_reboot":
            self.ironicclient.call("node.set_power_state",
                                   instance.node_uuid, "reboot", soft=True)
        else:
            self.ironicclient.call("node.set_power_state",
                                   instance.node_uuid, state)
        timer = loopingcall.FixedIntervalLoopingCall(
            self._wait_for_power_state, instance)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()

    def is_node_unprovision(self, node):
        return node.provision_state in _UNPROVISION_STATES

    def _wait_for_power_state(self, instance):
        """Wait for the node to complete a power state change."""
        try:
            node = self.get_node_by_instance(self.ironicclient,
                                             instance.uuid)
        except exception.NotFound:
            LOG.debug("While waiting for node to complete a power state "
                      "change, it dissociate with the instance.",
                      instance=instance)
            raise exception.NodeNotFound()

        if node.target_power_state == ironic_states.NOSTATE:
            raise loopingcall.LoopingCallDone()

    def do_node_rebuild(self, instance):
        # trigger the node rebuild
        try:
            self.ironicclient.call("node.set_provision_state",
                                   instance.node_uuid,
                                   ironic_states.REBUILD)
        except (ironic_exc.InternalServerError,
                ironic_exc.BadRequest) as e:
            msg = (_("Failed to request Ironic to rebuild instance "
                     "%(inst)s: %(reason)s") % {'inst': instance.uuid,
                                                'reason': six.text_type(e)})
            raise exception.InstanceDeployFailure(msg)

        # Although the target provision state is REBUILD, it will actually go
        # to ACTIVE once the redeploy is finished.
        timer = loopingcall.FixedIntervalLoopingCall(self._wait_for_active,
                                                     instance)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()

    def get_console_by_node(self, node_uuid):
        def _get_console():
            """Request ironicclient to acquire node console."""
            try:
                return self.ironicclient.call('node.get_console', node_uuid)
            except (ironic_exc.InternalServerError,
                    ironic_exc.BadRequest) as e:
                LOG.error(_LE('Failed to acquire console information for '
                              'noce %(inst)s: %(reason)s'),
                          {'inst': node_uuid,
                           'reason': e})
                raise exception.ConsoleNotAvailable()

        def _wait_state(state):
            """Wait for the expected console mode to be set on node."""
            console = _get_console()
            if console['console_enabled'] == state:
                raise loopingcall.LoopingCallDone(retvalue=console)

            LOG.debug('Still waiting for ironic node %(node)s to set console '
                      'to be: %(state)s',
                      {'node': node_uuid, 'state': state})
            # Return False to start backing off
            return False

        def _enable_console(mode):
            """Request ironicclient to enable/disable node console."""
            try:
                self.ironicclient.call(
                    'node.set_console_mode', node_uuid, mode)
            except (ironic_exc.InternalServerError,  # Validations
                    ironic_exc.BadRequest) as e:  # Maintenance
                LOG.error(_LE('Failed to set console mode to "%(mode)s" '
                              'for node %(node)s: %(reason)s'),
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
            LOG.debug('Console is disabled for node %s', node_uuid)
            raise exception.ConsoleNotAvailable()
