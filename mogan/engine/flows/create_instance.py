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

import base64
import gzip
import shutil
import tempfile
import traceback

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import excutils
import six
import taskflow.engines
from taskflow.patterns import linear_flow

from mogan.common import exception
from mogan.common import flow_utils
from mogan.common.i18n import _
from mogan.common import utils
from mogan.engine import configdrive
from mogan.engine import metadata as instance_metadata
from mogan import objects


LOG = logging.getLogger(__name__)

ACTION = 'instance:create'
CONF = cfg.CONF


class OnFailureRescheduleTask(flow_utils.MoganTask):
    """Triggers a rescheduling request to be sent when reverting occurs.

    If rescheduling doesn't occur this task errors out the instance.
    """

    def __init__(self, engine_api):
        requires = ['filter_properties', 'request_spec', 'instance',
                    'requested_networks', 'user_data', 'injected_files',
                    'context']
        super(OnFailureRescheduleTask, self).__init__(addons=[ACTION],
                                                      requires=requires)
        self.engine_api = engine_api
        # These exception types will trigger the instance to be set into error
        # status rather than being rescheduled.
        self.no_reschedule_exc_types = [
            # The instance has been removed from the database, that can not
            # be fixed by rescheduling.
            exception.InstanceNotFound,
            exception.InstanceDeployAborted,
            exception.NetworkError,
        ]

    def execute(self, **kwargs):
        pass

    def _reschedule(self, context, cause, request_spec, filter_properties,
                    instance, requested_networks, user_data, injected_files):
        """Actions that happen during the rescheduling attempt occur here."""

        create_instance = self.engine_api.schedule_and_create_instances
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
                               user_data=user_data,
                               injected_files=injected_files,
                               request_spec=request_spec,
                               filter_properties=filter_properties)

    def revert(self, context, result, flow_failures, instance, **kwargs):
        # Cleanup associated instance node uuid
        if instance.node_uuid:
            # If the compute node is still in DB, release it.
            try:
                cn = objects.ComputeNode.get(context, instance.node_uuid)
            except exception.ComputeNodeNotFound:
                pass
            else:
                cn.destroy()
            instance.node_uuid = None
            instance.save()

        # Check if we have a cause which can tell us not to reschedule and
        # set the instance's status to error.
        for failure in flow_failures.values():
            if failure.check(*self.no_reschedule_exc_types):
                LOG.error("Instance %s: create failed and no reschedule.",
                          instance.uuid)
                return False

        cause = list(flow_failures.values())[0]
        try:
            self._reschedule(context, cause, instance=instance, **kwargs)
            return True
        except exception.MoganException:
            LOG.exception("Instance %s: rescheduling failed",
                          instance.uuid)

        return False


class BuildNetworkTask(flow_utils.MoganTask):
    """Build network for the instance."""

    def __init__(self, manager):
        requires = ['instance', 'requested_networks', 'ports', 'context']
        super(BuildNetworkTask, self).__init__(addons=[ACTION],
                                               requires=requires)
        self.manager = manager

    def _build_networks(self, context, instance, requested_networks, ports):

        # TODO(zhenguo): This seems not needed as our scheduler has already
        # guaranteed this.
        if len(requested_networks) > len(ports):
            raise exception.InterfacePlugException(_(
                "Ironic node: %(id)s virtual to physical interface count"
                "  mismatch"
                " (Vif count: %(vif_count)d, Pif count: %(pif_count)d)")
                % {'id': instance.node_uuid,
                   'vif_count': len(requested_networks),
                   'pif_count': len(ports)})

        nics_obj = objects.InstanceNics(context)
        for vif in requested_networks:
            for pif in ports:
                # Match the specified port type with physical interface type
                if vif.get('port_type', 'None') == pif.port_type:
                    try:
                        port = self.manager.network_api.create_port(
                            context, vif['net_id'], pif.address, instance.uuid)
                        port_dict = port['port']

                        self.manager.driver.plug_vif(pif.port_uuid,
                                                     port_dict['id'])
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
                        LOG.error("Instance %s: create network failed",
                                  instance.uuid)
                        raise exception.NetworkError(_(
                            "Build network for instance failed."))
        return nics_obj

    def execute(self, context, instance, requested_networks, ports):
        instance_nics = self._build_networks(
            context,
            instance,
            requested_networks,
            ports)

        instance.nics = instance_nics
        instance.save()

    def revert(self, context, result, flow_failures, instance, **kwargs):
        # Check if we need to clean up networks.
        if instance.nics:
            LOG.debug("Instance %s: cleaning up node networks",
                      instance.uuid)
            self.manager.destroy_networks(context, instance)
            # Unset nics here as we have destroyed it.
            instance.nics = None
            return True

        return False


class GenerateConfigDriveTask(flow_utils.MoganTask):
    """Generate ConfigDrive value the instance."""

    def __init__(self):
        requires = ['instance', 'user_data', 'injected_files', 'configdrive',
                    'context']
        super(GenerateConfigDriveTask, self).__init__(addons=[ACTION],
                                                      requires=requires)

    def _generate_configdrive(self, context, instance, user_data=None,
                              files=None):
        """Generate a config drive."""

        i_meta = instance_metadata.InstanceMetadata(
            instance, content=files, user_data=user_data)

        with tempfile.NamedTemporaryFile() as uncompressed:
            with configdrive.ConfigDriveBuilder(instance_md=i_meta) as cdb:
                cdb.make_drive(uncompressed.name)

            with tempfile.NamedTemporaryFile() as compressed:
                # compress config drive
                with gzip.GzipFile(fileobj=compressed, mode='wb') as gzipped:
                    uncompressed.seek(0)
                    shutil.copyfileobj(uncompressed, gzipped)

                # base64 encode config drive
                compressed.seek(0)
                return base64.b64encode(compressed.read())

    def execute(self, context, instance, user_data, injected_files,
                configdrive):

        try:
            configdrive['value'] = self._generate_configdrive(
                context, instance, user_data=user_data, files=injected_files)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                msg = ("Failed to build configdrive: %s" %
                       six.text_type(e))
                LOG.error(msg, instance=instance)

        LOG.info("Config drive for instance %(instance)s created.",
                 {'instance': instance.uuid})


class CreateInstanceTask(flow_utils.MoganTask):
    """Build and deploy the instance."""

    def __init__(self, driver):
        requires = ['instance', 'configdrive', 'context']
        super(CreateInstanceTask, self).__init__(addons=[ACTION],
                                                 requires=requires)
        self.driver = driver
        # These exception types will trigger the instance to be cleaned.
        self.instance_cleaned_exc_types = [
            exception.InstanceDeployFailure,
            loopingcall.LoopingCallTimeOut,
        ]

    def execute(self, context, instance, configdrive):
        configdrive_value = configdrive.get('value')
        self.driver.spawn(context, instance, configdrive_value)
        LOG.info('Successfully provisioned Ironic node %s',
                 instance.node_uuid)

    def revert(self, context, result, flow_failures, instance, **kwargs):
        # Check if we have a cause which need to clean up instance.
        for failure in flow_failures.values():
            if failure.check(*self.instance_cleaned_exc_types):
                LOG.debug("Instance %s: destroy ironic node", instance.uuid)
                self.driver.destroy(context, instance)
                return True

        return False


def get_flow(context, manager, instance, requested_networks, user_data,
             injected_files, ports, request_spec, filter_properties):

    """Constructs and returns the manager entrypoint flow

    This flow will do the following:

    1. Build networks for the instance and set port id back to baremetal port
    2. Generate configdrive value for instance.
    3. Do node deploy and handle errors.
    4. Reschedule if the tasks are on failure.
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
        'requested_networks': requested_networks,
        'user_data': user_data,
        'injected_files': injected_files,
        'ports': ports,
        'configdrive': {}
    }

    instance_flow.add(OnFailureRescheduleTask(manager.engine_api),
                      BuildNetworkTask(manager),
                      GenerateConfigDriveTask(),
                      CreateInstanceTask(manager.driver))

    # Now load (but do not run) the flow using the provided initial data.
    return taskflow.engines.load(instance_flow, store=create_what)
