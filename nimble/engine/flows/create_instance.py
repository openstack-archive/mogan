# Copyright 2016 Intel
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from nimble.common import exception
from nimble.common.i18n import _LI
from nimble.common import neutron
from nimble.conf import CONF
from nimble.engine.baremetal import ironic
from nimble.engine.baremetal import ironic_states
from nimble.engine import status

from oslo_log import log
from oslo_service import loopingcall
from oslo_utils import importutils
from oslo_utils import timeutils

from taskflow import engines as taskflow_engines
from taskflow.patterns import graph_flow as gf
from taskflow import task

LOG = log.getLogger(__name__)


class ScheduleNodeTask(task.Task):
    def __init__(self):
        schedule_driver = CONF.schedule.schedule_driver
        self.schedule = importutils.import_object(schedule_driver)

    def execute(self, context, instance, request_spec):
        filter_properties = {}
        try:
            top_node = self.engine_manager.scheduler.schedule(
                context,
                request_spec,
                self.engine_manager.node_cache,
                filter_properties)
        except exception.NoValidNode:
            instance.status = status.ERROR
            instance.save()
            raise exception.NoValidNode(
                _('No valid node is found with request spec %s') %
                request_spec)
        instance.node_uuid = top_node.to_dict()['node']
        return instance

    def revert(self):
        pass


class SetInstanceInfoInIronicTask(task.Task):
    def __init__(self):
        self.ironicclient = ironic.IronicClientWrapper()

    def execute(self, context, instance):
        ironic.set_instance_info(self.ironicclient, instance)
        # validate we are ready to do the deploy
        validate_chk = ironic.validate_node(self.ironicclient,
                                            instance.node_uuid)
        if (not validate_chk.deploy.get('result')
                or not validate_chk.power.get('result')):
            instance.status = status.ERROR
            instance.save()
            raise exception.ValidationError(_(
                "Ironic node: %(id)s failed to validate."
                " (deploy: %(deploy)s, power: %(power)s)")
                % {'id': instance.node_uuid,
                   'deploy': validate_chk.deploy,
                   'power': validate_chk.power})
        return instance

    def revert(self):
        pass


class BuildNetworkTask(task.Task):
    def __init__(self):
        self.ironicclient = ironic.IronicClientWrapper()

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

    def execute(self, context, instance, requested_networks):
        try:
            network_info = self._build_networks(
                context,
                instance,
                requested_networks)
        except exception.InterfacePlugException:
            raise exception.NetworkError(_(
                "Build network for instance failed."))

        instance.network_info = network_info
        return instance

    def revert(self):
        pass


class BuildInstanceTask(task.Task):
    def __init__(self):
        self.ironicclient = ironic.IronicClientWrapper()

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

    def execute(self, context, instance):
        instance.status = status.BUILDING
        instance.save()
        self._build_instance(context, instance)
        return instance

    def revert(self):
        pass


def create_instance_flow(context, instance, requested_networks, request_spec):
    create_what = {
        'context': context,
        'instance': instance,
        'requested_networks': requested_networks,
        'request_spec': request_spec
    }
    flow = gf.Flow('create_instance')
    flow.add(ScheduleNodeTask('ScheduleNode',
                              provides='instance1',
                              rebind=['context',
                                      'instance',
                                      'request_spec']))
    flow.add(SetInstanceInfoInIronicTask('SetInstanceInfo',
                                         provides=[],
                                         rebind=[]))
    flow.add(BuildNetworkTask('BuildNetwork',
                              provides='instance2',
                              rebind=['context',
                                      'instance1',
                                      'requested_networks']))
    flow.add(BuildInstanceTask('BuildInstance',
                               provides='created_instance',
                               rebind=['context',
                                       'instance2']))
    result = taskflow_engines.run(flow,
                                  engine_conf={'engine': 'serial'},
                                  store=create_what)
    return result['created_instance']
