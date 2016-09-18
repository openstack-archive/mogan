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
from oslo_service import loopingcall
from oslo_service import periodic_task

from nimble.common import exception
from nimble.common.i18n import _LI
from nimble.common import neutron
from nimble.conf import CONF
from nimble.engine.baremetal import ironic
from nimble.engine.baremetal import ironic_states
from nimble.engine import base_manager

MANAGER_TOPIC = 'nimble.engine_manager'

LOG = log.getLogger(__name__)


class EngineManager(base_manager.BaseEngineManager):
    """Nimble Engine manager main class."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def _refresh_cache(self):
        node_cache = {}
        nodes = ironic.get_node_list(detail=True, maintenance=False,
                                     provision_state=ironic_states.AVAILABLE,
                                     associated=False, limit=0)
        for node in nodes:
            node_cache[node.uuid] = node

        self.node_cache = node_cache
        self.node_cache_time = time.time()

    @periodic_task.periodic_task(
        spacing=CONF.engine.sync_node_resource_interval)
    def _sync_node_resources(self, context):
        self._refresh_cache()

    def _build_networks(self, context, instance):
        macs = ironic.get_macs_from_node(instance.node_uuid)
        port = neutron.create_ports(context, instance.network_uuid, macs[0])
        ironic.plug_vifs(instance.node_uuid, port['port']['id'])

    def _wait_for_active(self, instance):
        """Wait for the node to be marked as ACTIVE in Ironic."""

        node = ironic.get_node_by_instance(instance.uuid)
        LOG.debug('Current ironic node state is %s', node.provision_state)
        if node.provision_state == ironic_states.ACTIVE:
            # job is done
            LOG.debug("Ironic node %(node)s is now ACTIVE",
                      dict(node=node.uuid))
            instance.status = ironic_states.ACTIVE
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
        ironic.set_instance_info(instance)
        ironic.do_node_deploy(instance.node_uuid)

        timer = loopingcall.FixedIntervalLoopingCall(self._wait_for_active,
                                                     instance)
        timer.start(interval=CONF.ironic.api_retry_interval).wait()
        LOG.info(_LI('Successfully provisioned Ironic node %s'),
                 instance.node_uuid)

    def _destroy_instance(self, context, instance):
        ironic.destroy_node(instance.node_uuid)
        LOG.info(_LI('Successfully destroyed Ironic node %s'),
                 instance.node_uuid)

    def create_instance(self, context, instance):
        """Signal to engine service to perform a deployment."""
        LOG.debug("Strating instance...")
        instance.status = 'building'

        # Populate request spec
        instance_type_id = instance.instance_type_id
        instance_type = instance.instance_type
        request_spec = {
            'instance_id': instance.id,
            'instance_properties': {
                'availability_zone': instance.availability_zone,
                'instance_type_id': instance_type_id,
            },
            'instance_type': dict(instance_type),
        }

        # TODO(zhenguo): Add retry
        top_node = self.scheduler.schedule(context,
                                           request_spec,
                                           self.node_cache)
        instance_node_uuid = top_node.to_dict()['node']

        instance.save()

        self._build_networks(context, instance)

        self._build_instance(context, instance)

        return instance

    def delete_instance(self, context, instance):
        """Signal to engine service to delete an instance."""
        LOG.debug("Deleting instance...")

        self._destroy_instance(context, instance)

        instance.destroy()
