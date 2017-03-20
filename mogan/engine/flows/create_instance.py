# Copyright 2016 Huawei Technologies Co.,LTD.
# All Rights Reserved.

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

import traceback

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
import taskflow.engines
from taskflow.patterns import linear_flow

from mogan.common import exception
from mogan.common import flow_utils
from mogan.common.i18n import _
from mogan.common.i18n import _LE
from mogan.common.i18n import _LI
from mogan.common import utils
from mogan import objects


LOG = logging.getLogger(__name__)

ACTION = 'instance:create'
CONF = cfg.CONF


class ScheduleCreateInstanceTask(flow_utils.MoganTask):
    """Activates a scheduler driver and handles any subsequent failure."""

    def __init__(self, manager):
        requires = ['filter_properties', 'request_spec', 'instance',
                    'context']
        super(ScheduleCreateInstanceTask, self).__init__(addons=[ACTION],
                                                         requires=requires)
        self.manager = manager

    def execute(self, context, instance, request_spec, filter_properties):
        top_node = self.manager.scheduler_rpcapi.select_destinations(
            context,
            request_spec,
            filter_properties)
        instance.node_uuid = top_node
        instance.save()


class OnFailureRescheduleTask(flow_utils.MoganTask):
    """Triggers a rescheduling request to be sent when reverting occurs.

    If rescheduling doesn't occur this task errors out the instance.
    """

    def __init__(self, engine_rpcapi):
        requires = ['filter_properties', 'request_spec', 'instance',
                    'requested_networks', 'context']
        super(OnFailureRescheduleTask, self).__init__(addons=[ACTION],
                                                      requires=requires)
        self.engine_rpcapi = engine_rpcapi
        # These exception types will trigger the instance to be set into error
        # status rather than being rescheduled.
        self.no_reschedule_exc_types = [
            # The instance has been removed from the database, that can not
            # be fixed by rescheduling.
            exception.InstanceNotFound,
            exception.NetworkError,
        ]

    def execute(self, **kwargs):
        pass

    def _reschedule(self, context, cause, request_spec, filter_properties,
                    instance, requested_networks):
        """Actions that happen during the rescheduling attempt occur here."""

        create_instance = self.engine_rpcapi.create_instance
        if not filter_properties:
            filter_properties = {}
        if 'retry' not in filter_properties:
            filter_properties['retry'] = {}

        retry_info = filter_properties['retry']
        num_attempts = retry_info.get('num_attempts', 0)

        LOG.debug("Instance %(instance_id)s: re-scheduling %(method)s "
                  "attempt %(num)d due to %(reason)s",
                  {'instance_id': instance.uuid,
                   'method': utils.make_pretty_name(create_instance),
                   'num': num_attempts,
                   'reason': cause.exception_str})

        if all(cause.exc_info):
            # Stringify to avoid circular ref problem in json serialization
            retry_info['exc'] = traceback.format_exception(*cause.exc_info)

        return create_instance(context, instance, requested_networks,
                               request_spec=request_spec,
                               filter_properties=filter_properties)

    def revert(self, context, result, flow_failures, instance, **kwargs):
        # Check if we have a cause which can tell us not to reschedule and
        # set the instance's status to error.
        for failure in flow_failures.values():
            if failure.check(*self.no_reschedule_exc_types):
                LOG.error(_LE("Instance %s: create failed and no reschedule."),
                          instance.uuid)
                return False

        cause = list(flow_failures.values())[0]
        try:
            self._reschedule(context, cause, instance=instance, **kwargs)
            return True
        except exception.MoganException:
            LOG.exception(_LE("Instance %s: rescheduling failed"),
                          instance.uuid)

        return False


class BuildNetworkTask(flow_utils.MoganTask):
    """Build network for the instance."""

    def __init__(self, manager):
        requires = ['instance', 'requested_networks', 'context']
        super(BuildNetworkTask, self).__init__(addons=[ACTION],
                                               requires=requires)
        self.manager = manager
        # These exception types will trigger the network to be cleaned.
        self.network_cleaned_exc_types = [
            exception.NetworkError,
            # include instance create task failure here
            exception.InstanceDeployFailure,
            exception.ValidationError,
            exception.InstanceNotFound,
            loopingcall.LoopingCallTimeOut,
        ]

    def _build_networks(self, context, instance, requested_networks):
        node_uuid = instance.node_uuid
        bm_ports = self.manager.driver.get_ports_from_node(node_uuid,
                                                           detail=True)

        LOG.debug(_('Find ports %(ports)s for node %(node)s') %
                  {'ports': bm_ports, 'node': node_uuid})
        if len(requested_networks) > len(bm_ports):
            raise exception.InterfacePlugException(_(
                "Ironic node: %(id)s virtual to physical interface count"
                "  mismatch"
                " (Vif count: %(vif_count)d, Pif count: %(pif_count)d)")
                % {'id': instance.node_uuid,
                   'vif_count': len(requested_networks),
                   'pif_count': len(bm_ports)})

        nics_obj = objects.InstanceNics(context)
        for vif in requested_networks:
            for pif in bm_ports:
                # Match the specified port type with physical interface type
                if vif.get('port_type') == pif.extra.get('port_type'):
                    try:
                        port = self.manager.network_api.create_port(
                            context, vif['net_id'], pif.address, instance.uuid)
                        port_dict = port['port']

                        self.manager.driver.plug_vif(pif.uuid, port_dict['id'])
                        nic_dict = {'port_id': port_dict['id'],
                                    'network_id': port_dict['network_id'],
                                    'mac_address': port_dict['mac_address'],
                                    'fixed_ips': port_dict['fixed_ips'],
                                    'port_type': vif.get('port_type'),
                                    'instance_uuid': instance.uuid}
                        nics_obj.objects.append(objects.InstanceNic(
                            context, **nic_dict))

                    except Exception:
                        # Set nics here, so we can clean up the
                        # created networks during reverting.
                        instance.nics = nics_obj
                        LOG.error(_LE("Instance %s: create network failed"),
                                  instance.uuid)
                        raise exception.NetworkError(_(
                            "Build network for instance failed."))
        return nics_obj

    def execute(self, context, instance, requested_networks):
        isntance_nics = self._build_networks(
            context,
            instance,
            requested_networks)

        instance.nics = isntance_nics
        instance.save()

    def revert(self, context, result, flow_failures, instance, **kwargs):
        # Check if we have a cause which need to clean up networks.
        for failure in flow_failures.values():
            if failure.check(*self.network_cleaned_exc_types):
                LOG.debug("Instance %s: cleaning up node networks",
                          instance.uuid)
                if instance.nics:
                    self.manager.destroy_networks(context, instance)
                    # Unset nics here as we have destroyed it.
                    instance.nics = None
                return True

        return False


class CreateInstanceTask(flow_utils.MoganTask):
    """Build and deploy the instance."""

    def __init__(self, driver):
        requires = ['instance', 'context']
        super(CreateInstanceTask, self).__init__(addons=[ACTION],
                                                 requires=requires)
        self.driver = driver
        # These exception types will trigger the instance to be cleaned.
        self.instance_cleaned_exc_types = [
            exception.InstanceDeployFailure,
            loopingcall.LoopingCallTimeOut,
        ]

    def execute(self, context, instance):
        self.driver.spawn(context, instance)
        LOG.info(_LI('Successfully provisioned Ironic node %s'),
                 instance.node_uuid)

    def revert(self, context, result, flow_failures, instance, **kwargs):
        # Check if we have a cause which need to clean up instance.
        for failure in flow_failures.values():
            if failure.check(*self.instance_cleaned_exc_types):
                LOG.debug("Instance %s: destroy ironic node", instance.uuid)
                self.driver.destroy(instance)
                return True

        return False


def get_flow(context, manager, instance, requested_networks, request_spec,
             filter_properties):

    """Constructs and returns the manager entrypoint flow

    This flow will do the following:

    1. Schedule a node to create instance
    3. Build networks for the instance and set port id back to baremetal port
    4. Do node deploy and handle errors.
    """

    flow_name = ACTION.replace(":", "_") + "_manager"
    instance_flow = linear_flow.Flow(flow_name)

    # This injects the initial starting flow values into the workflow so that
    # the dependency order of the tasks provides/requires can be correctly
    # determined.
    create_what = {
        'context': context,
        'filter_properties': filter_properties,
        'request_spec': request_spec,
        'instance': instance,
        'requested_networks': requested_networks
    }

    instance_flow.add(ScheduleCreateInstanceTask(manager),
                      OnFailureRescheduleTask(manager.engine_rpcapi),
                      BuildNetworkTask(manager),
                      CreateInstanceTask(manager.driver))

    # Now load (but do not run) the flow using the provided initial data.
    return taskflow.engines.load(instance_flow, store=create_what)
