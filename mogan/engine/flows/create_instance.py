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
from oslo_utils import timeutils
import taskflow.engines
from taskflow.patterns import linear_flow

from mogan.common import exception
from mogan.common import flow_utils
from mogan.common.i18n import _
from mogan.common.i18n import _LE
from mogan.common.i18n import _LI
from mogan.common import utils
from mogan.engine.baremetal import ironic
from mogan.engine.baremetal import ironic_states
from mogan.engine import status

LOG = logging.getLogger(__name__)

ACTION = 'instance:create'
CONF = cfg.CONF


class ScheduleCreateInstanceTask(flow_utils.NimbleTask):
    """Activates a scheduler driver and handles any subsequent failure."""

    def __init__(self, manager):
        requires = ['filter_properties', 'request_spec', 'instance',
                    'context']
        super(ScheduleCreateInstanceTask, self).__init__(addons=[ACTION],
                                                         requires=requires)
        self.manager = manager

    def execute(self, context, instance, request_spec, filter_properties):
        with self.manager._lock:
            top_node = self.manager.scheduler.schedule(
                context,
                request_spec,
                self.manager.node_cache,
                filter_properties)
            self.manager.node_cache.pop(top_node, None)
        instance.node_uuid = top_node
        instance.save()


class OnFailureRescheduleTask(flow_utils.NimbleTask):
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
        except exception.NimbleException:
            LOG.exception(_LE("Instance %s: rescheduling failed"),
                          instance.uuid)

        return False


class SetInstanceInfoTask(flow_utils.NimbleTask):
    """Set instance info to ironic node and validate it."""

    def __init__(self, ironicclient):
        requires = ['instance', 'context']
        super(SetInstanceInfoTask, self).__init__(addons=[ACTION],
                                                  requires=requires)
        self.ironicclient = ironicclient
        # These exception types will trigger the instance info to be cleaned.
        self.instance_info_cleaned_exc_types = [
            exception.ValidationError,
            exception.InterfacePlugException,
            exception.NetworkError,
        ]

    def execute(self, context, instance):
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

    def revert(self, context, result, flow_failures, instance, **kwargs):
        # Check if we have a cause which need to clean up ironic node
        # instance info.
        for failure in flow_failures.values():
            if failure.check(*self.instance_info_cleaned_exc_types):
                LOG.debug("Instance %s: cleaning up node instance info",
                          instance.uuid)
                ironic.unset_instance_info(self.ironicclient, instance)
                return True

        return False


class BuildNetworkTask(flow_utils.NimbleTask):
    """Build network for the instance."""

    def __init__(self, network_api, ironicclient):
        requires = ['instance', 'requested_networks', 'context']
        super(BuildNetworkTask, self).__init__(addons=[ACTION],
                                               requires=requires)
        self.network_api = network_api
        self.ironicclient = ironicclient
        # These exception types will trigger the network to be cleaned.
        self.network_cleaned_exc_types = [
            exception.NetworkError,
            # include instance create task failure here
            exception.InstanceDeployFailure,
            loopingcall.LoopingCallTimeOut,
        ]

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
                    try:
                        port = self.network_api.create_port(
                            context, vif['net_id'], pif.address, instance.uuid)
                        port_dict = port['port']
                        network_info[port_dict['id']] = {
                            'network': port_dict['network_id'],
                            'mac_address': port_dict['mac_address'],
                            'fixed_ips': port_dict['fixed_ips']}
                        ironic.plug_vif(self.ironicclient, pif.uuid,
                                        port_dict['id'])
                    except Exception:
                        # Set network_info here, so we can clean up the created
                        # networks during reverting.
                        instance.network_info = network_info
                        LOG.error(_LE("Instance %s: create network failed"),
                                  instance.uuid)
                        raise exception.NetworkError(_(
                            "Build network for instance failed."))

        return network_info

    def _destroy_networks(self, context, instance):
        LOG.debug("unplug: instance_uuid=%(uuid)s vif=%(network_info)s",
                  {'uuid': instance.uuid,
                   'network_info': str(instance.network_info)})

        ports = instance.network_info.keys()
        for port in ports:
            self.network_api.delete_port(context, port, instance.uuid)

        ironic_ports = ironic.get_ports_from_node(self.ironicclient,
                                                  instance.node_uuid,
                                                  detail=True)
        for pif in ironic_ports:
            if 'vif_port_id' in pif.extra:
                ironic.unplug_vif(self.ironicclient, pif.uuid)

    def execute(self, context, instance, requested_networks):
        network_info = self._build_networks(
            context,
            instance,
            requested_networks)

        instance.network_info = network_info
        instance.save()

    def revert(self, context, result, flow_failures, instance, **kwargs):
        # Check if we have a cause which need to clean up networks.
        for failure in flow_failures.values():
            if failure.check(*self.network_cleaned_exc_types):
                LOG.debug("Instance %s: cleaning up node networks",
                          instance.uuid)
                if instance.network_info:
                    self._destroy_networks(context, instance)
                    # Unset network_info here as we have destroyed it.
                    instance.network_info = {}
                return True

        return False


class CreateInstanceTask(flow_utils.NimbleTask):
    """Set instance info to ironic node and validate it."""

    def __init__(self, ironicclient):
        requires = ['instance', 'context']
        super(CreateInstanceTask, self).__init__(addons=[ACTION],
                                                 requires=requires)
        self.ironicclient = ironicclient
        # These exception types will trigger the instance to be cleaned.
        self.instance_cleaned_exc_types = [
            exception.InstanceDeployFailure,
            loopingcall.LoopingCallTimeOut,
        ]

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
        self._build_instance(context, instance)

    def revert(self, context, result, flow_failures, instance, **kwargs):
        # Check if we have a cause which need to clean up instance.
        for failure in flow_failures.values():
            if failure.check(*self.instance_cleaned_exc_types):
                LOG.debug("Instance %s: destroy ironic node", instance.uuid)
                ironic.destroy_node(self.ironicclient, instance.node_uuid)
                return True

        return False


def get_flow(context, manager, instance, requested_networks, request_spec,
             filter_properties):

    """Constructs and returns the manager entrypoint flow

    This flow will do the following:

    1. Schedule a node to create instance
    2. Set instance info to ironic node and validate it's ready to deploy
    3. Build networks for the instance and set port id back to ironic port
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
                      SetInstanceInfoTask(manager.ironicclient),
                      BuildNetworkTask(manager.network_api,
                                       manager.ironicclient),
                      CreateInstanceTask(manager.ironicclient))

    # Now load (but do not run) the flow using the provided initial data.
    return taskflow.engines.load(instance_flow, store=create_what)
