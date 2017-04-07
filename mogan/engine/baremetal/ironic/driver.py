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
from oslo_utils import excutils
import six

from mogan.common import exception
from mogan.common.i18n import _
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


def map_power_state(state):
    try:
        return _POWER_STATE_MAP[state]
    except KeyError:
        LOG.warning("Power state %s not found.", state)
        return states.NOSTATE


def _log_ironic_polling(what, node, instance):
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
              instance=instance)


class IronicDriver(base_driver.BaseEngineDriver):

    def __init__(self):
        super(IronicDriver, self).__init__()
        self.ironicclient = ironic.IronicClientWrapper()

    def _get_node(self, node_uuid):
        """Get a node by its UUID."""
        return self.ironicclient.call('node.get', node_uuid,
                                      fields=_NODE_FIELDS)

    def _validate_instance_and_node(self, instance):
        """Get the node associated with the instance.

        Check with the Ironic service that this instance is associated with a
        node, and return the node.
        """
        try:
            return self.ironicclient.call('node.get_by_instance_uuid',
                                          instance.uuid, fields=_NODE_FIELDS)
        except ironic_exc.NotFound:
            raise exception.InstanceNotFound(instance_id=instance.uuid)

    def _parse_node_properties(self, node):
        """Helper method to parse the node's properties."""
        properties = {}

        for prop in ('cpus', 'memory_mb', 'local_gb'):
            try:
                properties[prop] = int(node.properties.get(prop, 0))
            except (TypeError, ValueError):
                LOG.warning('Node %(uuid)s has a malformed "%(prop)s". '
                            'It should be an integer.',
                            {'uuid': node.uuid, 'prop': prop})
                properties[prop] = 0

        properties['capabilities'] = node.properties.get('capabilities')
        properties['availability_zone'] = \
            node.properties.get('availability_zone')
        properties['node_type'] = node.properties.get('node_type')
        return properties

    def _node_resource(self, node):
        """Helper method to create resource dict from node stats."""
        properties = self._parse_node_properties(node)

        cpus = properties['cpus']
        memory_mb = properties['memory_mb']
        availability_zone = properties['availability_zone']
        node_type = properties['node_type']

        nodes_extra_specs = {}

        # NOTE(gilliard): To assist with more precise scheduling, if the
        # node.properties contains a key 'capabilities', we expect the value
        # to be of the form "k1:v1,k2:v2,etc.." which we add directly as
        # key/value pairs into the node_extra_specs to be used by the
        # ComputeCapabilitiesFilter
        capabilities = properties['capabilities']
        if capabilities:
            for capability in str(capabilities).split(','):
                parts = capability.split(':')
                if len(parts) == 2 and parts[0] and parts[1]:
                    nodes_extra_specs[parts[0].strip()] = parts[1]
                else:
                    LOG.warning("Ignoring malformed capability '%s'. "
                                "Format should be 'key:val'.", capability)

        dic = {
            'cpus': cpus,
            'memory_mb': memory_mb,
            'hypervisor_type': self._get_hypervisor_type(),
            'availability_zone': str(availability_zone),
            'node_type': str(node_type),
            'extra_specs': nodes_extra_specs,
            'node_uuid': str(node.uuid),
            'ports': node.ports,
        }
        return dic

    def _port_resource(self, port):
        """Helper method to create resource dict from port stats."""
        port_type = port.extra.get('port_type')

        dic = {
            'address': str(port.address),
            'port_type': str(port_type),
            'node_uuid': str(port.node_uuid),
            'port_uuid': str(port.uuid),
        }
        return dic

    def _add_instance_info_to_node(self, node, instance):

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

        try:
            # FIXME(lucasagomes): The "retry_on_conflict" parameter was added
            # to basically causes the deployment to fail faster in case the
            # node picked by the scheduler is already associated with another
            # instance due bug #1341420.
            self.ironicclient.call('node.update', node.uuid, patch,
                                   retry_on_conflict=False)
        except ironic_exc.BadRequest:
            msg = (_("Failed to add deploy parameters on node %(node)s "
                     "when provisioning the instance %(instance)s")
                   % {'node': node.uuid, 'instance': instance.uuid})
            LOG.error(msg)
            raise exception.InstanceDeployFailure(msg)

    def _remove_instance_info_from_node(self, node, instance):
        patch = [{'path': '/instance_info', 'op': 'remove'},
                 {'path': '/instance_uuid', 'op': 'remove'}]
        try:
            self.ironicclient.call('node.update', node.uuid, patch)
        except ironic_exc.BadRequest as e:
            LOG.warning("Failed to remove deploy parameters from node "
                        "%(node)s when unprovisioning the instance "
                        "%(instance)s: %(reason)s",
                        {'node': node.uuid, 'instance': instance.uuid,
                         'reason': six.text_type(e)})

    def _wait_for_active(self, instance):
        """Wait for the node to be marked as ACTIVE in Ironic."""
        instance.refresh()
        if instance.status in (states.DELETING, states.ERROR, states.DELETED):
            raise exception.InstanceDeployAborted(
                _("Instance %s provisioning was aborted") % instance.uuid)

        node = self._validate_instance_and_node(instance)
        if node.provision_state == ironic_states.ACTIVE:
            # job is done
            LOG.debug("Ironic node %(node)s is now ACTIVE",
                      dict(node=node.uuid), instance=instance)
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

        _log_ironic_polling('become ACTIVE', node, instance)

    def _wait_for_power_state(self, instance, message):
        """Wait for the node to complete a power state change."""
        node = self._validate_instance_and_node(instance)

        if node.target_power_state == ironic_states.NOSTATE:
            raise loopingcall.LoopingCallDone()

        _log_ironic_polling(message, node, instance)

    def _get_hypervisor_type(self):
        """Get hypervisor type."""
        return 'ironic'

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

    def unplug_vifs(self, context, instance):
        LOG.debug("unplug: instance_uuid=%(uuid)s vif=%(instance_nics)s",
                  {'uuid': instance.uuid,
                   'instance_nics': str(instance.nics)})
        patch = [{'op': 'remove',
                  'path': '/extra/vif_port_id'}]

        ports = self.get_ports_from_node(instance.node_uuid)

        for port in ports:
            try:
                if 'vif_port_id' in port.extra:
                    self.ironicclient.call("port.update",
                                           port.uuid, patch)
            except client_e.BadRequest:
                pass

    def spawn(self, context, instance):
        """Deploy an instance.

        :param context: The security context.
        :param instance: The instance object.
        """
        LOG.debug('Spawn called for instance', instance=instance)

        # The engine manager is meant to know the node uuid, so missing uuid
        # is a significant issue. It may mean we've been passed the wrong data.
        node_uuid = instance.node_uuid
        if not node_uuid:
            raise ironic_exc.BadRequest(
                _("Ironic node uuid not supplied to "
                  "driver for instance %s.") % instance.uuid)

        # add instance info to node
        node = self._get_node(node_uuid)
        self._add_instance_info_to_node(node, instance)

        # validate we are ready to do the deploy
        validate_chk = self.ironicclient.call("node.validate", node_uuid)
        if (not validate_chk.deploy.get('result')
                or not validate_chk.power.get('result')):
            # something is wrong. undo what we have done
            self._cleanup_deploy(node, instance)
            raise exception.ValidationError(_(
                "Ironic node: %(id)s failed to validate."
                " (deploy: %(deploy)s, power: %(power)s)")
                % {'id': instance.node_uuid,
                   'deploy': validate_chk.deploy,
                   'power': validate_chk.power})

        # trigger the node deploy
        try:
            self.ironicclient.call("node.set_provision_state", node_uuid,
                                   ironic_states.ACTIVE)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                msg = ("Failed to request Ironic to provision instance "
                       "%(inst)s: %(reason)s",
                       {'inst': instance.uuid,
                        'reason': six.text_type(e)})
                LOG.error(msg)

        timer = loopingcall.FixedIntervalLoopingCall(self._wait_for_active,
                                                     instance)
        try:
            timer.start(interval=CONF.ironic.api_retry_interval).wait()
            LOG.info('Successfully provisioned Ironic node %s',
                     node.uuid, instance=instance)
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.error("Error deploying instance %(instance)s on "
                          "baremetal node %(node)s.",
                          {'instance': instance.uuid,
                           'node': node_uuid})

    def _unprovision(self, instance, node):
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
            if getattr(e, '__name__', None) != 'InstanceDeployFailure':
                raise

        # using a dict because this is modified in the local method
        data = {'tries': 0}

        def _wait_for_provision_state():
            try:
                node = self._validate_instance_and_node(instance)
            except exception.InstanceNotFound:
                LOG.debug("Instance already removed from Ironic",
                          instance=instance)
                raise loopingcall.LoopingCallDone()
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

            _log_ironic_polling('unprovision', node, instance)

        # wait for the state transition to finish
        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_provision_state)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()

    def destroy(self, context, instance):
        """Destroy the specified instance, if it can be found.

        :param context: The security context.
        :param instance: The instance object.
        """
        LOG.debug('Destroy called for instance', instance=instance)
        try:
            node = self._validate_instance_and_node(instance)
        except exception.InstanceNotFound:
            LOG.warning("Destroy called on non-existing instance %s.",
                        instance.uuid)
            return

        if node.provision_state in _UNPROVISION_STATES:
            self._unprovision(instance, node)
        else:
            # NOTE(hshiina): if spawn() fails before ironic starts
            #                provisioning, instance information should be
            #                removed from ironic node.
            self._remove_instance_info_from_node(node, instance)

        LOG.info('Successfully unprovisioned Ironic node %s',
                 node.uuid, instance=instance)

    def get_available_resources(self):
        """Helper function to return the list of resources.

        If unable to connect ironic server, an empty list is returned.

        :returns: a list of raw node from ironic

        """

        # Retrieve nodes
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
            LOG.exception("Could not get nodes from ironic. Reason: "
                          "%(detail)s", {'detail': e.message})
            node_list = []

        # Retrive ports
        params = {
            'limit': 0,
            'fields': ('uuid', 'node_uuid', 'extra', 'address')
        }

        try:
            port_list = self.ironicclient.call("port.list", **params)
        except client_e.ClientException as e:
            LOG.exception("Could not get ports from ironic. Reason: "
                          "%(detail)s", {'detail': e.message})
            port_list = []

        # TODO(zhenguo): Add portgroups resources
        node_resources = {}
        for node in node_list:
            # Add ports to the associated node
            node.ports = [self._port_resource(port) for port in port_list
                          if node.uuid == port.node_uuid]
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
                          "%(detail)s", {'detail': e.message})
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
            LOG.exception("Could not get nodes from ironic. Reason: "
                          "%(detail)s", {'detail': e.message})
            node_list = []
        return node_list

    def get_power_state(self, context, instance_uuid):
        try:
            node = self.ironicclient.call('node.get_by_instance_uuid',
                                          instance_uuid,
                                          fields=('power_state',))
            return map_power_state(node.power_state)
        except client_e.NotFound:
            return map_power_state(ironic_states.NOSTATE)

    def set_power_state(self, context, instance, state):
        """Set power state on the specified instance.

        :param context: The security context.
        :param instance: The instance object.
        """
        node = self._validate_instance_and_node(instance)
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
            self._wait_for_power_state, instance, state)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()

    def rebuild(self, context, instance):
        """Rebuild/redeploy an instance.

        :param context: The security context.
        :param instance: The instance object.
        """
        LOG.debug('Rebuild called for instance', instance=instance)

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
        LOG.info('Instance was successfully rebuilt', instance=instance)

    def get_serial_console_by_instance(self, context, instance):
        node = self._validate_instance_and_node(instance)
        node_uuid = node.uuid

        def _get_console():
            """Request ironicclient to acquire node console."""
            try:
                return self.ironicclient.call('node.get_console', node_uuid)
            except (ironic_exc.InternalServerError,
                    ironic_exc.BadRequest) as e:
                LOG.error('Failed to acquire console information for '
                          'node %(inst)s: %(reason)s',
                          {'inst': node_uuid,
                           'reason': e})
                raise exception.ConsoleNotAvailable()

        def _wait_state(state):
            """Wait for the expected console mode to be set on node."""
            console = _get_console()
            if console['console_enabled'] == state:
                raise loopingcall.LoopingCallDone(retvalue=console)

            _log_ironic_polling('set console mode', node, instance)

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
            if console['console_info']['type'] != 'shellinabox':
                raise exception.ConsoleTypeUnavailable(
                    console_type=console['console_info']['type'])

            return {'node': node,
                    'console_info': console['console_info']}
        else:
            LOG.debug('Console is disabled for node %s', node_uuid)
            raise exception.ConsoleNotAvailable()
