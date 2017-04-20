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

import base64
import binascii

from oslo_log import log
from oslo_serialization import base64 as base64utils
from oslo_utils import excutils
from oslo_utils import uuidutils
import six

from mogan.common import exception
from mogan.common import states
from mogan.common import utils
from mogan.conf import CONF
from mogan.consoleauth import rpcapi as consoleauth_rpcapi
from mogan.engine import rpcapi
from mogan import image
from mogan import network
from mogan import objects
from mogan.objects import quota

LOG = log.getLogger(__name__)

MAX_USERDATA_SIZE = 65535


def check_instance_lock(function):
    @six.wraps(function)
    def inner(self, context, instance, *args, **kwargs):
        if instance.locked and not context.is_admin:
            raise exception.InstanceIsLocked(instance_uuid=instance.uuid)
        return function(self, context, instance, *args, **kwargs)
    return inner


def check_instance_maintenance(function):
    @six.wraps(function)
    def inner(self, context, instance, *args, **kwargs):
        if instance.status == states.MAINTENANCE:
            raise exception.InstanceInMaintenance(instance_uuid=instance.uuid)
        return function(self, context, instance, *args, **kwargs)
    return inner


class API(object):
    """API for interacting with the engine manager."""

    def __init__(self, image_api=None, **kwargs):
        super(API, self).__init__(**kwargs)
        self.image_api = image_api or image.API()
        self.engine_rpcapi = rpcapi.EngineAPI()
        self.network_api = network.API()
        self.quota = quota.Quota()
        self.quota.register_resource(objects.quota.InstanceResource())
        self.consoleauth_rpcapi = consoleauth_rpcapi.ConsoleAuthAPI()

    def _get_image(self, context, image_uuid):
        return self.image_api.get(context, image_uuid)

    def _validate_and_build_base_options(self, context, instance_type,
                                         image_uuid, name, description,
                                         availability_zone, extra,
                                         requested_networks, user_data,
                                         key_name, max_count):
        """Verify all the input parameters"""

        if user_data:
            l = len(user_data)
            if l > MAX_USERDATA_SIZE:
                raise exception.InstanceUserDataTooLarge(
                    length=l, maxsize=MAX_USERDATA_SIZE)

            try:
                base64utils.decode_as_bytes(user_data)
            except TypeError:
                raise exception.InstanceUserDataMalformed()

        # Note:  max_count is the number of instances requested by the user,
        # max_network_count is the maximum number of instances taking into
        # account any network quotas
        max_network_count = self._check_requested_networks(context,
                                                           requested_networks,
                                                           max_count)

        if key_name is not None:
            key_pair = objects.KeyPair.get_by_name(context,
                                                   context.user_id,
                                                   key_name)
        else:
            key_pair = None

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
        return base_options, max_network_count, key_pair

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
        ins_resource = self.quota.resources['instances']
        quotas = self.quota.get_quota_limit_and_usage(context,
                                                      {'instances':
                                                       ins_resource},
                                                      context.tenant)
        limit = quotas['instances']['limit']
        in_use = quotas['instances']['in_use']
        reserved = quotas['instances']['reserved']
        available_quota = limit - in_use - reserved
        if max_count <= available_quota:
            return max_count
        elif min_count <= available_quota and max_count > available_quota:
            return available_quota
        else:
            raise exception.OverQuota(overs='instances')

    def _decode_files(self, injected_files):
        """Base64 decode the list of files to inject."""
        if not injected_files:
            return []

        def _decode(f):
            path, contents = f
            # Py3 raises binascii.Error instead of TypeError as in Py27
            try:
                decoded = base64.b64decode(contents)
                return path, decoded
            except (TypeError, binascii.Error):
                raise exception.Base64Exception(path=path)

        return [_decode(f) for f in injected_files]

    def _provision_instances(self, context, base_options,
                             min_count, max_count):
        # Return num_instances according quota
        num_instances = self._check_num_instances_quota(
            context, min_count, max_count)

        # Create the instances reservations
        reserve_opts = {'instances': num_instances}
        reservations = self.quota.reserve(context, **reserve_opts)

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
                    self.quota.rollback(context, reservations)

        # Commit instances reservations
        if reservations:
            self.quota.commit(context, reservations)

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
                         requested_networks, user_data, injected_files,
                         key_name, min_count, max_count):
        """Verify all the input parameters"""

        # Verify the specified image exists
        if image_uuid:
            self._get_image(context, image_uuid)

        base_options, max_net_count, key_pair = \
            self._validate_and_build_base_options(
                context, instance_type, image_uuid, name, description,
                availability_zone, extra, requested_networks, user_data,
                key_name, max_count)

        # max_net_count is the maximum number of instances requested by the
        # user adjusted for any network quota constraints, including
        # consideration of connections to each requested network
        if max_net_count < min_count:
            raise exception.PortLimitExceeded()
        elif max_net_count < max_count:
            LOG.info("max count reduced from %(max_count)d to "
                     "%(max_net_count)d due to network port quota",
                     {'max_count': max_count,
                      'max_net_count': max_net_count})
            max_count = max_net_count

        # TODO(zhenguo): Check injected file quota
        # b64 decode the files to inject:
        decoded_files = self._decode_files(injected_files)

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
                                               user_data,
                                               decoded_files,
                                               request_spec,
                                               filter_properties=None)

        return instances

    def create(self, context, instance_type, image_uuid,
               name=None, description=None, availability_zone=None,
               extra=None, requested_networks=None, user_data=None,
               injected_files=None, key_name=None, min_count=None,
               max_count=None):
        """Provision instances

        Sending instance information to the engine and will handle
        creating the DB entries.

        Returns an instance object
        """

        # check availability zone
        if availability_zone:
            azs = self.list_availability_zones(context)
            if availability_zone not in azs['availability_zones']:
                raise exception.AZNotFound

        return self._create_instance(context, instance_type,
                                     image_uuid, name, description,
                                     availability_zone, extra,
                                     requested_networks, user_data,
                                     injected_files, key_name,
                                     min_count, max_count)

    def _delete_instance(self, context, instance):

        fsm = utils.get_state_machine(start_state=instance.status)

        try:
            utils.process_event(fsm, instance, event='delete')
        except exception.InstanceNotFound:
            LOG.debug("Instance is not found while deleting",
                      instance=instance)
            return
        reserve_opts = {'instances': -1}
        reservations = self.quota.reserve(context, **reserve_opts)
        if reservations:
            self.quota.commit(context, reservations)
        self.engine_rpcapi.delete_instance(context, instance)

    @check_instance_lock
    def delete(self, context, instance):
        """Delete an instance."""
        LOG.debug("Going to try to delete instance %s", instance.uuid)
        self._delete_instance(context, instance)

    @check_instance_lock
    @check_instance_maintenance
    def power(self, context, instance, target):
        """Set power state of an instance."""
        LOG.debug("Going to try to set instance power state to %s",
                  target, instance=instance)
        fsm = utils.get_state_machine(start_state=instance.status)
        try:
            utils.process_event(fsm, instance,
                                event=states.POWER_ACTION_MAP[target])
        except exception.InstanceNotFound:
            LOG.debug("Instance is not found while setting power state",
                      instance=instance)
            return

        self.engine_rpcapi.set_power_state(context, instance, target)

    @check_instance_lock
    @check_instance_maintenance
    def rebuild(self, context, instance):
        """Rebuild an instance."""
        fsm = utils.get_state_machine(start_state=instance.status)
        try:
            utils.process_event(fsm, instance, event='rebuild')
        except exception.InstanceNotFound:
            LOG.debug("Instance is not found while rebuilding",
                      instance=instance)
            return

        self.engine_rpcapi.rebuild_instance(context, instance)

    def list_availability_zones(self, context):
        """Get availability zone list."""
        compute_nodes = objects.ComputeNodeList.get_all_available(context)

        azs = set()
        for node in compute_nodes:
            az = node.availability_zone \
                or CONF.engine.default_availability_zone
            if az is not None:
                azs.add(az)

        return {'availability_zones': list(azs)}

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

    def get_serial_console(self, context, instance):
        """Get a url to an instance Console."""
        connect_info = self.engine_rpcapi.get_serial_console(
            context, instance=instance)
        self.consoleauth_rpcapi.authorize_console(
            context,
            connect_info['token'], 'serial',
            connect_info['host'], connect_info['port'],
            connect_info['internal_access_path'], instance.uuid,
            access_url=connect_info['access_url'])

        return {'url': connect_info['access_url']}
