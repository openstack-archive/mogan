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
import string

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
from mogan.objects import keypair as keypair_obj
from mogan.objects import quota

LOG = log.getLogger(__name__)

MAX_USERDATA_SIZE = 65535


def check_server_lock(function):
    @six.wraps(function)
    def inner(self, context, server, *args, **kwargs):
        if server.locked and not context.is_admin:
            raise exception.ServerIsLocked(server_uuid=server.uuid)
        return function(self, context, server, *args, **kwargs)
    return inner


def check_server_maintenance(function):
    @six.wraps(function)
    def inner(self, context, server, *args, **kwargs):
        if server.status == states.MAINTENANCE:
            raise exception.ServerInMaintenance(server_uuid=server.uuid)
        return function(self, context, server, *args, **kwargs)
    return inner


class API(object):
    """API for interacting with the engine manager."""

    def __init__(self, image_api=None, **kwargs):
        super(API, self).__init__(**kwargs)
        self.image_api = image_api or image.API()
        self.engine_rpcapi = rpcapi.EngineAPI()
        self.network_api = network.API()
        self.quota = quota.Quota()
        self.quota.register_resource(objects.quota.ServerResource())
        self.quota.register_resource(objects.quota.KeyPairResource())
        self.consoleauth_rpcapi = consoleauth_rpcapi.ConsoleAuthAPI()

    def _get_image(self, context, image_uuid):
        return self.image_api.get(context, image_uuid)

    def _validate_and_build_base_options(self, context, flavor,
                                         image_uuid, name, description,
                                         availability_zone, metadata,
                                         requested_networks, user_data,
                                         key_name, max_count):
        """Verify all the input parameters"""
        if flavor['disabled']:
            raise exception.FlavorNotFound(flavor_id=flavor['uuid'])

        if user_data:
            l = len(user_data)
            if l > MAX_USERDATA_SIZE:
                raise exception.ServerUserDataTooLarge(
                    length=l, maxsize=MAX_USERDATA_SIZE)

            try:
                base64utils.decode_as_bytes(user_data)
            except TypeError:
                raise exception.ServerUserDataMalformed()

        # Note:  max_count is the number of servers requested by the user,
        # max_network_count is the maximum number of servers taking into
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
            'flavor_uuid': flavor['uuid'],
            'name': name,
            'description': description,
            'locked': False,
            'metadata': metadata or {},
            'availability_zone': availability_zone}

        # return the validated options
        return base_options, max_network_count, key_pair

    def _new_server_name_from_template(self, uuid, name, index):
        """Apply the template to server name.

        Apply name template for multi-server scenario.

        :param uuid: The uuid of server.
        :param name: The name of server.
        :param index: The index of server.
        :return: The new name of server.
        """
        params = {
            'uuid': uuid,
            'name': name,
            'count': index + 1,
        }
        try:
            new_name = (CONF.api.multi_server_name_template %
                        params)
        except (KeyError, TypeError):
            LOG.exception('Failed to set server name using '
                          'multi_server_name_template.')
            new_name = name
        return new_name

    def _populate_server_names(self, server, num_servers, index):
        """Rename the server name in multi-server scenario.

        This is for rename server in multi-server scenario.

        :param server: The server object.
        :param num_servers: The number of servers
        :param index: the index of the server
        :return: The server object
        """
        if num_servers > 1:
            server.name = self._new_server_name_from_template(
                server.uuid, server.name, index)

        return server

    def _check_num_servers_quota(self, context, min_count, max_count):
        ins_resource = self.quota.resources['servers']
        quotas = self.quota.get_quota_limit_and_usage(context,
                                                      {'servers':
                                                       ins_resource},
                                                      context.tenant)
        limit = quotas['servers']['limit']
        in_use = quotas['servers']['in_use']
        reserved = quotas['servers']['reserved']
        available_quota = limit - in_use - reserved
        if max_count <= available_quota:
            return max_count
        elif min_count <= available_quota and max_count > available_quota:
            return available_quota
        else:
            raise exception.OverQuota(overs='servers')

    def _check_num_keypairs_quota(self, context, count):
        keypair_resource = self.quota.resources['keypairs']
        quotas = self.quota.get_quota_limit_and_usage(context,
                                                      {'keyparis':
                                                       keypair_resource},
                                                      context.tenant)
        limit = quotas['keypairs']['limit']
        in_use = quotas['keypairs']['in_use']
        reserved = quotas['keypairs']['reserved']
        available_quota = limit - in_use - reserved
        if count <= available_quota:
            return count
        else:
            raise exception.OverQuota(overs='keypairs')

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

    def _provision_servers(self, context, base_options,
                           min_count, max_count):
        # Return num_servers according quota
        num_servers = self._check_num_servers_quota(
            context, min_count, max_count)

        # Create the servers reservations
        reserve_opts = {'servers': num_servers}
        reservations = self.quota.reserve(context, **reserve_opts)

        LOG.debug("Going to run %s servers...", num_servers)

        servers = []
        try:
            for num in range(num_servers):
                server = objects.Server(context=context)
                server.update(base_options)
                server.uuid = uuidutils.generate_uuid()
                # Refactor name of the server.
                self._populate_server_names(server, num_servers, num)

                server.create()
                servers.append(server)
        except Exception:
            with excutils.save_and_reraise_exception():
                try:
                    for server in servers:
                        try:
                            server.destroy()
                        except exception.ObjectActionError:
                            pass
                finally:
                    self.quota.rollback(context, reservations)

        # Commit servers reservations
        if reservations:
            self.quota.commit(context, reservations)

        return servers

    def _check_requested_networks(self, context, requested_networks,
                                  max_count):
        """Check if the networks requested belongs to the project
        and the fixed IP address for each network provided is within
        same the network block
        """

        return self.network_api.validate_networks(context, requested_networks,
                                                  max_count)

    def _create_server(self, context, flavor, image_uuid,
                       name, description, availability_zone, metadata,
                       requested_networks, user_data, injected_files,
                       key_name, min_count, max_count):
        """Verify all the input parameters"""

        # Verify the specified image exists
        if image_uuid:
            self._get_image(context, image_uuid)

        if not availability_zone:
            availability_zone = CONF.engine.default_availability_zone

        base_options, max_net_count, key_pair = \
            self._validate_and_build_base_options(
                context, flavor, image_uuid, name, description,
                availability_zone, metadata, requested_networks, user_data,
                key_name, max_count)

        # max_net_count is the maximum number of servers requested by the
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

        servers = self._provision_servers(context, base_options,
                                          min_count, max_count)
        request_spec = {
            'server_properties': {
                'flavor_uuid': servers[0].flavor_uuid,
                'networks': requested_networks,
            },
            'flavor': dict(flavor),
            'availability_zone': availability_zone,
        }

        self.engine_rpcapi.schedule_and_create_servers(context, servers,
                                                       requested_networks,
                                                       user_data,
                                                       decoded_files,
                                                       key_pair,
                                                       request_spec,
                                                       filter_properties=None)
        return servers

    def create(self, context, flavor, image_uuid,
               name=None, description=None, availability_zone=None,
               metadata=None, requested_networks=None, user_data=None,
               injected_files=None, key_name=None, min_count=None,
               max_count=None):
        """Provision servers

        Sending server information to the engine and will handle
        creating the DB entries.

        Returns a server object
        """

        # check availability zone
        if availability_zone:
            azs = self.list_availability_zones(context)
            if availability_zone not in azs['availability_zones']:
                raise exception.AZNotFound

        return self._create_server(context, flavor,
                                   image_uuid, name, description,
                                   availability_zone, metadata,
                                   requested_networks, user_data,
                                   injected_files, key_name,
                                   min_count, max_count)

    def _delete_server(self, context, server):

        fsm = utils.get_state_machine(start_state=server.status)

        try:
            utils.process_event(fsm, server, event='delete')
        except exception.ServerNotFound:
            LOG.debug("Server is not found while deleting",
                      server=server)
            return
        reserve_opts = {'servers': -1}
        reservations = self.quota.reserve(context, **reserve_opts)
        if reservations:
            self.quota.commit(context, reservations)
        self.engine_rpcapi.delete_server(context, server)

    @check_server_lock
    def delete(self, context, server):
        """Delete a server."""
        LOG.debug("Going to try to delete server %s", server.uuid)
        self._delete_server(context, server)

    @check_server_lock
    @check_server_maintenance
    def power(self, context, server, target):
        """Set power state of a server."""
        LOG.debug("Going to try to set server power state to %s",
                  target, server=server)
        fsm = utils.get_state_machine(start_state=server.status)
        try:
            utils.process_event(fsm, server,
                                event=states.POWER_ACTION_MAP[target])
        except exception.ServerNotFound:
            LOG.debug("Server is not found while setting power state",
                      server=server)
            return

        self.engine_rpcapi.set_power_state(context, server, target)

    @check_server_lock
    @check_server_maintenance
    def rebuild(self, context, server):
        """Rebuild a server."""
        fsm = utils.get_state_machine(start_state=server.status)
        try:
            utils.process_event(fsm, server, event='rebuild')
        except exception.ServerNotFound:
            LOG.debug("Server is not found while rebuilding",
                      server=server)
            return

        self.engine_rpcapi.rebuild_server(context, server)

    def list_availability_zones(self, context):
        """Get availability zone list."""
        aggregates = objects.AggregateList.get_by_metadata_key(
            context, 'availability_zone')
        azs = set([agg.metadata['availability_zone'] for agg in aggregates
                   if 'availability_zone' in agg.metadata])
        azs.add(CONF.engine.default_availability_zone)
        return {'availability_zones': list(azs)}

    def lock(self, context, server):
        """Lock the given server."""

        is_owner = server.project_id == context.project_id
        if server.locked and is_owner:
            return

        LOG.debug('Locking', server=server)
        server.locked = True
        server.locked_by = 'owner' if is_owner else 'admin'
        server.save()

    def unlock(self, context, server):
        """Unlock the given server."""

        LOG.debug('Unlocking', server=server)
        server.locked = False
        server.locked_by = None
        server.save()

    def is_expected_locked_by(self, context, server):
        is_owner = server.project_id == context.project_id
        expect_locked_by = 'owner' if is_owner else 'admin'
        locked_by = server.locked_by
        if locked_by and locked_by != expect_locked_by:
            return False
        return True

    def get_serial_console(self, context, server):
        """Get a url to a server Console."""
        connect_info = self.engine_rpcapi.get_serial_console(
            context, server=server)
        self.consoleauth_rpcapi.authorize_console(
            context,
            connect_info['token'], 'serial',
            connect_info['host'], connect_info['port'],
            connect_info['internal_access_path'], server.uuid,
            access_url=connect_info['access_url'])

        return {'url': connect_info['access_url']}

    def _validate_new_key_pair(self, context, user_id, key_name, key_type):
        safe_chars = "_- " + string.digits + string.ascii_letters
        clean_value = "".join(x for x in key_name if x in safe_chars)
        if clean_value != key_name:
            raise exception.InvalidKeypair(
                reason="Keypair name contains unsafe characters")

        try:
            utils.check_string_length(key_name, min_length=1, max_length=255)
        except exception.Invalid:
            raise exception.InvalidKeypair(
                reason='Keypair name must be string and between '
                       '1 and 255 characters long')

            # TODO(liusheng) add quota check
            # count = objects.Quotas.count(context, 'key_pairs', user_id)
            #
            # try:
            #     objects.Quotas.limit_check(context, key_pairs=count + 1)
            # except exception.OverQuota:
            #     raise exception.KeypairLimitExceeded()

    def import_key_pair(self, context, user_id, key_name, public_key,
                        key_type=keypair_obj.KEYPAIR_TYPE_SSH):
        """Import a key pair using an existing public key."""
        self._validate_new_key_pair(context, user_id, key_name, key_type)
        fingerprint = self._generate_fingerprint(public_key, key_type)

        keypair = objects.KeyPair(context)
        keypair.user_id = user_id
        keypair.name = key_name
        keypair.type = key_type
        keypair.fingerprint = fingerprint
        keypair.public_key = public_key
        keypair.create()
        return keypair

    def create_key_pair(self, context, user_id, key_name,
                        key_type=keypair_obj.KEYPAIR_TYPE_SSH):
        """Create a new key pair."""
        self._validate_new_key_pair(context, user_id, key_name, key_type)
        private_key, public_key, fingerprint = self._generate_key_pair(
            user_id, key_type)
        # Create the keypair reservations
        num_keypairs = self._check_num_keypairs_quota(context, 1)
        reserve_opts = {'keypairs': num_keypairs}
        reservations = self.quota.reserve(context, **reserve_opts)
        keypair = objects.KeyPair(context)
        keypair.user_id = user_id
        keypair.name = key_name
        keypair.type = key_type
        keypair.fingerprint = fingerprint
        keypair.public_key = public_key
        keypair.project_id = context.tenant
        keypair.create()
        # Commit keypairs reservations
        if reservations:
            self.quota.commit(context, reservations)
        return keypair, private_key

    def _generate_fingerprint(self, public_key, key_type):
        if key_type == keypair_obj.KEYPAIR_TYPE_SSH:
            return utils.generate_fingerprint(public_key)
        elif key_type == keypair_obj.KEYPAIR_TYPE_X509:
            return utils.generate_x509_fingerprint(public_key)

    def _generate_key_pair(self, user_id, key_type):
        if key_type == keypair_obj.KEYPAIR_TYPE_SSH:
            return utils.generate_key_pair()
        elif key_type == keypair_obj.KEYPAIR_TYPE_X509:
            return utils.generate_winrm_x509_cert(user_id)

    def delete_key_pair(self, context, user_id, key_name):
        """Delete a keypair by name."""
        objects.KeyPair.destroy_by_name(context, user_id, key_name)
        reserve_opts = {'keypairs': -1}
        reservations = self.quota.reserve(context, **reserve_opts)
        if reservations:
            self.quota.commit(context, reservations)

    def get_key_pairs(self, context, user_id):
        """List key pairs."""
        return objects.KeyPairList.get_by_user(context, user_id)

    def get_key_pair(self, context, user_id, key_name):
        """Get a keypair by name."""
        return objects.KeyPair.get_by_name(context, user_id, key_name)

    @check_server_lock
    def attach_interface(self, context, server, net_id):
        self.engine_rpcapi.attach_interface(context, server, net_id)

    @check_server_lock
    def detach_interface(self, context, server, port_id):
        self.engine_rpcapi.detach_interface(context, server=server,
                                            port_id=port_id)

    def list_compute_nodes(self, context):
        """Get compute node list."""
        return self.engine_rpcapi.list_compute_nodes(context)

    def list_aggregate_nodes(self, context, aggregate_uuid):
        """Get aggregate node list."""
        return self.engine_rpcapi.list_aggregate_nodes(context,
                                                       aggregate_uuid)

    def add_aggregate_node(self, context, aggregate_uuid, node):
        """Add a node to the aggregate."""
        return self.engine_rpcapi.add_aggregate_node(context,
                                                     aggregate_uuid,
                                                     node)

    def remove_aggregate_node(self, context, aggregate_uuid, node):
        """Remove a node to the aggregate."""
        return self.engine_rpcapi.remove_aggregate_node(context,
                                                        aggregate_uuid,
                                                        node)

    def get_manageable_servers(self, context):
        self.engine_rpcapi.get_manageable_servers(context)
