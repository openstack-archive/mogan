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

import time

from oslo_log import log
import oslo_messaging as messaging
from oslo_service import periodic_task

from nimble.common.i18n import _LI
from nimble.common import neutron
from nimble.conf import CONF
from nimble.engine.baremetal import ironic
from nimble.engine.baremetal import ironic_states
from nimble.engine import base_manager
from nimble.engine.flows import create_instance as create_instance_flow

MANAGER_TOPIC = 'nimble.engine_manager'

LOG = log.getLogger(__name__)


class EngineManager(base_manager.BaseEngineManager):
    """Nimble Engine manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def _refresh_cache(self):
        node_cache = []
        nodes = ironic.get_node_list(self.ironicclient, detail=True,
                                     maintenance=False,
                                     provision_state=ironic_states.AVAILABLE,
                                     associated=False, limit=0)
        for node in nodes:
            node_cache.append(node)

        self.node_cache = node_cache
        self.node_cache_time = time.time()

    @periodic_task.periodic_task(
        spacing=CONF.engine.sync_node_resource_interval)
    def _sync_node_resources(self, context):
        self._refresh_cache()

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
        instance = create_instance_flow.get_created_instance(
            context,
            instance,
            requested_networks,
            request_spec)

        return instance

    def delete_instance(self, context, instance):
        """Delete an instance."""
        LOG.debug("Deleting instance...")

        self._destroy_networks(context, instance)
        self._destroy_instance(context, instance)

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
