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

"""Handles all requests relating to compute resources"""

from oslo_log import log
from oslo_utils import excutils
from oslo_utils import uuidutils

from mogan.common import exception
from mogan.common.i18n import _LI
from mogan.common import states
from mogan.conf import CONF
from mogan.engine import rpcapi
from mogan import image
from mogan import network
from mogan import objects

LOG = log.getLogger(__name__)


class API(object):
    """API for interacting with the engine manager."""

    def __init__(self, image_api=None, **kwargs):
        super(API, self).__init__(**kwargs)
        self.image_api = image_api or image.API()
        self.engine_rpcapi = rpcapi.EngineAPI()
        self.network_api = network.API()

    def _get_image(self, context, image_uuid):
        return self.image_api.get(context, image_uuid)

    def _validate_and_build_base_options(self, context, instance_type,
                                         image_uuid, name, description,
                                         availability_zone, extra,
                                         requested_networks,
                                         max_count):
        """Verify all the input parameters"""

        # Note:  max_count is the number of instances requested by the user,
        # max_network_count is the maximum number of instances taking into
        # account any network quotas
        max_network_count = self._check_requested_networks(context,
                                                           requested_networks,
                                                           max_count)

        base_options = {
            'image_uuid': image_uuid,
            'status': states.BUILDING,
            'user_id': context.user,
            'project_id': context.tenant,
            'power_state': states.NOSTATE,
            'instance_type_uuid': instance_type['uuid'],
            'name': name,
            'description': description,
            'locked': False,
            'extra': extra or {},
            'availability_zone': availability_zone}

        # return the validated options
        return base_options, max_network_count

    def _new_instance_name_from_template(self, uuid, name, index):
        """Apply the template to instance name.

        Apply name template for multi-instance scenario.

        :param uuid: The uuid of instance.
        :param name: The name of instance.
        :param index: The index of instance.
        :return: The new name of instance.
        """
        params = {
            'uuid': uuid,
            'name': name,
            'count': index + 1,
        }
        try:
            new_name = (CONF.api.multi_instance_name_template %
                        params)
        except (KeyError, TypeError):
            LOG.exception('Failed to set instance name using '
                          'multi_instance_name_template.')
            new_name = name
        return new_name

    def _populate_instance_names(self, instance, num_instances, index):
        """Rename the instance name in multi-instance scenario.

        This is for rename instance in multi-instance scenario.

        :param instance: The instance object.
        :param num_instances: The number of instances
        :param index: the index of the instance
        :return: The instance object
        """
        if num_instances > 1:
            instance.name = self._new_instance_name_from_template(
                instance.uuid, instance.name, index)

        return instance

    def _check_num_instances_quota(self, context, min_count, max_count):
        # TODO(little): check quotas and return reserved quotas
        return max_count, None

    def _provision_instances(self, context, base_options,
                             min_count, max_count):
        # TODO(little): finish to return num_instances according quota
        num_instances, quotas = self._check_num_instances_quota(
            context, min_count, max_count)

        LOG.debug("Going to run %s instances...", num_instances)

        instances = []
        try:
            for num in range(num_instances):
                instance = objects.Instance(context=context)
                instance.update(base_options)
                instance.uuid = uuidutils.generate_uuid()
                # Refactor name of the instance.
                self._populate_instance_names(instance, num_instances, num)

                instance.create()
                instances.append(instance)
        except Exception:
            with excutils.save_and_reraise_exception():
                try:
                    for instance in instances:
                        try:
                            instance.destroy()
                        except exception.ObjectActionError:
                            pass
                finally:
                    # TODO(little): quota release
                    pass

        return instances

    def _check_requested_networks(self, context, requested_networks,
                                  max_count):
        """Check if the networks requested belongs to the project
        and the fixed IP address for each network provided is within
        same the network block
        """

        return self.network_api.validate_networks(context, requested_networks,
                                                  max_count)

    def _create_instance(self, context, instance_type, image_uuid,
                         name, description, availability_zone, extra,
                         requested_networks, min_count, max_count):
        """Verify all the input parameters"""

        # Verify the specified image exists
        if image_uuid:
            self._get_image(context, image_uuid)

        base_options, max_net_count = self._validate_and_build_base_options(
            context, instance_type, image_uuid, name, description,
            availability_zone, extra, requested_networks, max_count)

        # max_net_count is the maximum number of instances requested by the
        # user adjusted for any network quota constraints, including
        # consideration of connections to each requested network
        if max_net_count < min_count:
            raise exception.PortLimitExceeded()
        elif max_net_count < max_count:
            LOG.info(_LI("max count reduced from %(max_count)d to "
                         "%(max_net_count)d due to network port quota"),
                     {'max_count': max_count,
                      'max_net_count': max_net_count})
            max_count = max_net_count

        instances = self._provision_instances(context, base_options,
                                              min_count, max_count)

        if not availability_zone:
            availability_zone = CONF.engine.default_schedule_zone
        request_spec = {
            'instance_id': instances[0].uuid,
            'instance_properties': {
                'instance_type_uuid': instances[0].instance_type_uuid,
                'networks': requested_networks,
            },
            'instance_type': dict(instance_type),
            'availability_zone': availability_zone,
        }

        for instance in instances:
            self.engine_rpcapi.create_instance(context, instance,
                                               requested_networks,
                                               request_spec,
                                               filter_properties=None)

        return instances

    def create(self, context, instance_type, image_uuid,
               name=None, description=None, availability_zone=None,
               extra=None, requested_networks=None, min_count=None,
               max_count=None):
        """Provision instances

        Sending instance information to the engine and will handle
        creating the DB entries.

        Returns an instance object
        """

        # check availability zone
        if availability_zone:
            azs = self.engine_rpcapi.list_availability_zones(context)
            if availability_zone not in azs['availability_zones']:
                raise exception.AZNotFound

        return self._create_instance(context, instance_type,
                                     image_uuid, name, description,
                                     availability_zone, extra,
                                     requested_networks, min_count,
                                     max_count)

    def _delete_instance(self, context, instance):
        # Initialize state machine
        fsm = states.machine.copy()
        fsm.initialize(start_state=instance.status)

        fsm.process_event('delete')
        try:
            instance.status = fsm.current_state
            instance.save()
        except exception.InstanceNotFound:
            LOG.debug("Instance is not found while deleting",
                      instance=instance)
            return
        self.engine_rpcapi.delete_instance(context, instance)

    def delete(self, context, instance):
        """Delete an instance."""
        LOG.debug("Going to try to delete instance %s", instance.uuid)
        self._delete_instance(context, instance)

    def power(self, context, instance, target):
        """Set power state of an instance."""
        LOG.debug("Going to try to set instance power state to %s",
                  target, instance=instance)
        fsm = states.machine.copy()
        fsm.initialize(start_state=instance.status)
        fsm.process_event(states.POWER_ACTION_MAP[target])
        try:
            instance.status = fsm.current_state
            instance.save()
        except exception.InstanceNotFound:
            LOG.debug("Instance is not found while setting power state",
                      instance=instance)
            return

        self.engine_rpcapi.set_power_state(context, instance, target)

    def list_availability_zones(self, context):
        """Get a list of availability zones."""
        return self.engine_rpcapi.list_availability_zones(context)
