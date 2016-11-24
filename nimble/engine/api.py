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

from nimble.engine import rpcapi
from nimble.engine import status
from nimble import objects

LOG = log.getLogger(__name__)


class API(object):
    """API for interacting with the engine manager."""

    def __init__(self, **kwargs):
        super(API, self).__init__(**kwargs)
        self.engine_rpcapi = rpcapi.EngineAPI()

    def _validate_and_build_base_options(self, context, instance_type,
                                         image_uuid, name, description,
                                         availability_zone, extra):
        """Verify all the input parameters"""

        base_options = {
            'image_uuid': image_uuid,
            'status': status.BUILDING,
            'user_id': context.user_id,
            'project_id': context.project_id,
            'instance_type_uuid': instance_type['uuid'],
            'name': name,
            'description': description,
            'extra': extra or {},
            'availability_zone': availability_zone}

        # return the validated options
        return base_options

    def _provision_instances(self, context, base_options):
        # TODO(zhenguo): Reserve quotas

        instance = objects.Instance(context=context)
        instance.update(base_options)
        instance.status = status.BUILDING
        instance.create()

        return instance

    def _create_instance(self, context, instance_type, image_uuid,
                         name, description, availability_zone, extra,
                         requested_networks):
        """Verify all the input parameters"""

        base_options = self._validate_and_build_base_options(
            context, instance_type, image_uuid, name, description,
            availability_zone, extra)

        instance = self._provision_instances(context, base_options)

        self.engine_rpcapi.create_instance(context, instance,
                                           requested_networks,
                                           instance_type)

        return instance

    def create(self, context, instance_type, image_uuid,
               name=None, description=None, availability_zone=None,
               extra=None, requested_networks=None):
        """Provision instances

        Sending instance information to the engine and will handle
        creating the DB entries.

        Returns an instance object
        """

        # check availability zone
        # if availability_zone:
        #     available_zones = availability_zones.\
        #         get_availability_zones(context.elevated(), True)
        #     if availability_zone not in available_zones:
        #         msg = _('The requested availability zone is not available')
        #         raise exception.InvalidRequest(msg)

        return self._create_instance(context, instance_type,
                                     image_uuid, name, description,
                                     availability_zone, extra,
                                     requested_networks)

    def _delete_instance(self, context, instance):
        self.engine_rpcapi.delete_instance(context, instance)

    def delete(self, context, instance):
        """Delete an instance."""
        LOG.debug("Going to try to delete instance %s", instance.uuid)
        self._delete_instance(context, instance)

    def states(self, context, instance):
        """Get instance states."""
        return self.engine_rpcapi.instance_states(context, instance)

    def power(self, context, instance, target):
        """Set power state of an instance."""
        self.engine_rpcapi.set_power_state(context, instance, target)

    def get_ironic_node(self, context, instance_uuid, fields):
        """Get a ironic node by instance UUID."""
        return self.engine_rpcapi.get_ironic_node(context,
                                                  instance_uuid,
                                                  fields)

    def get_ironic_node_list(self, context, fields):
        """Get a list of ironic node."""
        return self.engine_rpcapi.get_ironic_node_list(context, fields)

    def list_availability_zones(self, context):
        """Get a list of availability zones."""
        return self.engine_rpcapi.list_availability_zones(context)
