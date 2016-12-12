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

from oslo_log import log
import oslo_messaging as messaging
from oslo_service import loopingcall
from oslo_service import periodic_task
from oslo_utils import timeutils

from nimble.common import exception
from nimble.common.i18n import _LE
from nimble.common.i18n import _LI
from nimble.common import neutron
from nimble.conf import CONF
from nimble.engine.baremetal import ironic
from nimble.engine.baremetal import ironic_states
from nimble.engine import base_manager
from nimble.engine import status

MANAGER_TOPIC = 'nimble.engine_manager'

LOG = log.getLogger(__name__)


class EngineManager(base_manager.BaseEngineManager):
    """Nimble Engine manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def _refresh_cache(self):
        node_cache = {}
        nodes = ironic.get_node_list(self.ironicclient, detail=True,
                                     maintenance=False,
                                     provision_state=ironic_states.AVAILABLE,
                                     associated=False, limit=0)
        for node in nodes:
            node_cache[node.uuid] = node

        self.node_cache = node_cache

    @periodic_task.periodic_task(
        spacing=CONF.engine.sync_node_resource_interval)
    def _sync_node_resources(self, context):
        self._refresh_cache()

    def _set_instance_obj_error_state(self, context, instance):
        try:
            instance.status = status.ERROR
            instance.save()
        except exception.InstanceNotFound:
            LOG.debug('Instance has been destroyed from under us while '
                      'trying to set it to ERROR', instance=instance)

    def _build_networks(self, context, instance, requested_networks):
        node_uuid = instance.node_uuid
        ironic_ports = ironic.get_ports_from_node(self.ironicclient,
                                                  node_uuid,
                                                  detail=True)
        LOG.debug(_('Find ports %(ports)s for node %(node)s') %
                  {'ports': ironic_ports, 'node': node_uuid})
        if len(requested_networks) > len(ironic_ports):
            raise exception.InterfacePlugException(_(
                "Ironic node: %(id)s virtual to physical interface count"
                "  mismatch"
                " (Vif count: %(vif_count)d, Pif count: %(pif_count)d)")
                % {'id': instance.node_uuid,
                   'vif_count': len(requested_networks),
                   'pif_count': len(ironic_ports)})

        network_info = {}
        for vif in requested_networks:
            for pif in ironic_ports:
                # Match the specified port type with physical interface type
                if vif.get('port_type') == pif.extra.get('port_type'):
                    port = neutron.create_port(context, vif['uuid'],
                                               pif.address, instance.uuid)
                    port_dict = port['port']
                    network_info[port_dict['id']] = {
                        'network': port_dict['network_id'],
                        'mac_address': port_dict['mac_address'],
                        'fixed_ips': port_dict['fixed_ips']}
                    ironic.plug_vif(self.ironicclient, pif.uuid,
                                    port_dict['id'])

        return network_info

    def _destroy_networks(self, context, instance):
        LOG.debug("unplug: instance_uuid=%(uuid)s vif=%(network_info)s",
                  {'uuid': instance.uuid,
                   'network_info': str(instance.network_info)})

        ports = instance.network_info.keys()
        for port in ports:
            neutron.delete_port(context, port, instance.uuid)

        ironic_ports = ironic.get_ports_from_node(self.ironicclient,
                                                  instance.node_uuid,
                                                  detail=True)
        for pif in ironic_ports:
            if 'vif_port_id' in pif.extra:
                ironic.unplug_vif(self.ironicclient, pif.uuid)

    def _wait_for_active(self, instance):
        """Wait for the node to be marked as ACTIVE in Ironic."""

        node = ironic.get_node_by_instance(self.ironicclient,
                                           instance.uuid)
        LOG.debug('Current ironic node state is %s', node.provision_state)
        if node.provision_state == ironic_states.ACTIVE:
            # job is done
            LOG.debug("Ironic node %(node)s is now ACTIVE",
                      dict(node=node.uuid))
            instance.status = status.ACTIVE
            instance.launched_at = timeutils.utcnow()
            instance.save()
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

    def _build_instance(self, context, instance):
        ironic.do_node_deploy(self.ironicclient, instance.node_uuid)

        timer = loopingcall.FixedIntervalLoopingCall(self._wait_for_active,
                                                     instance)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()
        LOG.info(_LI('Successfully provisioned Ironic node %s'),
                 instance.node_uuid)

    def _destroy_instance(self, context, instance):
        ironic.destroy_node(self.ironicclient, instance.node_uuid)
        LOG.info(_LI('Successfully destroyed Ironic node %s'),
                 instance.node_uuid)

    def create_instance(self, context, instance,
                        requested_networks, instance_type):
        """Perform a deployment."""
        LOG.debug("Starting instance...")

        # Populate request spec
        instance_type_uuid = instance.instance_type_uuid
        request_spec = {
            'instance_id': instance.uuid,
            'instance_properties': {
                'availability_zone': instance.availability_zone,
                'instance_type_uuid': instance_type_uuid,
            },
            'instance_type': dict(instance_type),
        }
        LOG.debug("Scheduling with request_spec: %s", request_spec)

        # TODO(zhenguo): Add retry
        filter_properties = {}
        try:
            top_node = self.scheduler.schedule(context,
                                               request_spec,
                                               self.node_cache,
                                               filter_properties)
        except exception.NoValidNode:
            self._set_instance_obj_error_state(context, instance)
            raise exception.NoValidNode(
                _('No valid node is found with request spec %s') %
                request_spec)
        instance.node_uuid = top_node.to_dict()['node']
        del self.node_cache[top_node.to_dict()['node']]

        ironic.set_instance_info(self.ironicclient, instance)
        # validate we are ready to do the deploy
        validate_chk = ironic.validate_node(self.ironicclient,
                                            instance.node_uuid)
        if (not validate_chk.deploy.get('result')
                or not validate_chk.power.get('result')):
            self._set_instance_obj_error_state(context, instance)
            raise exception.ValidationError(_(
                "Ironic node: %(id)s failed to validate."
                " (deploy: %(deploy)s, power: %(power)s)")
                % {'id': instance.node_uuid,
                   'deploy': validate_chk.deploy,
                   'power': validate_chk.power})

        try:
            network_info = self._build_networks(context, instance,
                                                requested_networks)
        except Exception:
            self._set_instance_obj_error_state(context, instance)
            return

        instance.network_info = network_info

        try:
            self._build_instance(context, instance)
        except Exception:
            self._set_instance_obj_error_state(context, instance)

    def delete_instance(self, context, instance):
        """Delete an instance."""
        LOG.debug("Deleting instance...")

        try:
            self._destroy_networks(context, instance)
            self._destroy_instance(context, instance)
        except Exception:
            LOG.exception(_LE("Error while trying to clean up "
                              "instance resources."),
                          instance=instance)

        instance.destroy()

    def _instance_states(self, context, instance):
        states = ironic.get_node_states(self.ironicclient,
                                        instance.node_uuid)
        LOG.info(_LI('Successfully get ironic node states: %s'),
                 states)
        return states.to_dict()

    def instance_states(self, context, instance):
        """Get an instance states."""
        LOG.debug("get instance states")

        return self._instance_states(context, instance)

    def _set_power_state(self, context, instance, state):
        ironic.set_power_state(self.ironicclient, instance.node_uuid, state)
        LOG.info(_LI('Successfully set ironic node power state: %s'),
                 state)

    def set_power_state(self, context, instance, state):
        """Get an instance states."""
        LOG.debug("set power state...")

        return self._set_power_state(context, instance, state)

    def get_ironic_node(self, context, instance_uuid, fields):
        """Get a ironic node."""
        node = ironic.get_node_by_instance(self.ironicclient,
                                           instance_uuid, fields)
        return node.to_dict()

    def get_ironic_node_list(self, context, fields):
        """Get a ironic node list."""
        nodes = ironic.get_node_list(self.ironicclient, associated=True,
                                     limit=0, fields=fields)
        return {'nodes': [node.to_dict() for node in nodes]}

    def list_availability_zones(self, context):
        """Get availability zone list."""
        azs = set()
        for node in self.node_cache:
            az = node.properties.get('availability_zone')
            if az is not None:
                azs.add(az)

        return {'availability_zones': list(azs)}
