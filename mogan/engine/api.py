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

from mogan.common import exception
from mogan.common import states
from mogan.conf import CONF
from mogan.engine import rpcapi
from mogan import image
from mogan import objects

LOG = log.getLogger(__name__)


class API(object):
    """API for interacting with the engine manager."""

    def __init__(self, image_api=None, **kwargs):
        super(API, self).__init__(**kwargs)
        self.image_api = image_api or image.API()
        self.engine_rpcapi = rpcapi.EngineAPI()

    def _get_image(self, context, image_uuid):
        return self.image_api.get(context, image_uuid)

    def _validate_and_build_base_options(self, context, instance_type,
                                         image_uuid, name, description,
                                         availability_zone, extra):
        """Verify all the input parameters"""

        base_options = {
            'image_uuid': image_uuid,
            'status': states.BUILDING,
            'user_id': context.user,
            'project_id': context.tenant,
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
        instance.status = states.BUILDING
        instance.create()

        return instance

    def _create_instance(self, context, instance_type, image_uuid,
                         name, description, availability_zone, extra,
                         requested_networks):
        """Verify all the input parameters"""

        # Verify the specified image exists
        if image_uuid:
            self._get_image(context, image_uuid)

        base_options = self._validate_and_build_base_options(
            context, instance_type, image_uuid, name, description,
            availability_zone, extra)

        instance = self._provision_instances(context, base_options)

        if not availability_zone:
            availability_zone = CONF.engine.default_schedule_zone
        request_spec = {
            'instance_id': instance.uuid,
            'instance_properties': {
                'instance_type_uuid': instance.instance_type_uuid,
                'networks': requested_networks,
            },
            'instance_type': dict(instance_type),
            'availability_zone': availability_zone,
        }

        self.engine_rpcapi.create_instance(context, instance,
                                           requested_networks,
                                           request_spec,
                                           filter_properties=None)

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
        if availability_zone:
            azs = self.engine_rpcapi.list_availability_zones(context)
            if availability_zone not in azs['availability_zones']:
                raise exception.AZNotFound

        return self._create_instance(context, instance_type,
                                     image_uuid, name, description,
                                     availability_zone, extra,
                                     requested_networks)

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

    def lock(self, context, instance):
        """Lock the given instance."""

        is_owner = instance.project_id == context.project_id
        if instance.locked and is_owner:
            return

        LOG.debug('Locking', instance=instance)
        instance.locked = True
        instance.locked_by = 'owner' if is_owner else 'admin'
        instance.save()

    def unlock(self, context, instance):
        """Unlock the given instance."""

        LOG.debug('Unlocking', instance=instance)
        instance.locked = False
        instance.locked_by = None
        instance.save()

    def is_expected_locked_by(self, context, instance):
        is_owner = instance.project_id == context.project_id
        expect_locked_by = 'owner' if is_owner else 'admin'
        locked_by = instance.locked_by
        if locked_by and locked_by != expect_locked_by:
            return False
        return True
