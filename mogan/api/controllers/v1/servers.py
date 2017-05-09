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

import datetime

from oslo_log import log
from oslo_utils import netutils
import pecan
from pecan import rest
from six.moves import http_client
from webob import exc
import wsme
from wsme import types as wtypes

from mogan.api.controllers import base
from mogan.api.controllers import link
from mogan.api.controllers.v1.schemas import floating_ips as fip_schemas
from mogan.api.controllers.v1.schemas import interfaces as interface_schemas
from mogan.api.controllers.v1.schemas import servers as server_schemas
from mogan.api.controllers.v1 import types
from mogan.api.controllers.v1 import utils as api_utils
from mogan.api import expose
from mogan.api import validation
from mogan.common import exception
from mogan.common.i18n import _
from mogan.common import policy
from mogan.common import states
from mogan import network
from mogan import objects

_DEFAULT_SERVER_RETURN_FIELDS = ('uuid', 'name', 'description',
                                 'status', 'power_state')

LOG = log.getLogger(__name__)


class ServerStates(base.APIBase):
    """API representation of the states of a server."""

    power_state = wtypes.text
    """Represent the current power state of the server"""

    status = wtypes.text
    """Represent the current status of the server"""

    locked = types.boolean
    """Represent the current lock state of the server"""

    @classmethod
    def sample(cls):
        sample = cls(power_state=states.POWER_ON,
                     status=states.ACTIVE, locked=False)
        return sample


class ServerControllerBase(rest.RestController):
    _resource = None

    # This _resource is used for authorization.
    def _get_resource(self, uuid, *args, **kwargs):
        self._resource = objects.Server.get(pecan.request.context, uuid)
        return self._resource


class ServerStatesController(ServerControllerBase):

    _custom_actions = {
        'power': ['PUT'],
        'lock': ['PUT'],
        'provision': ['PUT'],
    }

    @policy.authorize_wsgi("mogan:server", "get_states")
    @expose.expose(ServerStates, types.uuid)
    def get(self, server_uuid):
        """List the states of the server, just support power state at present.

        :param server_uuid: the UUID of a server.
        """
        rpc_server = self._resource or self._get_resource(server_uuid)

        return ServerStates(power_state=rpc_server.power_state,
                            status=rpc_server.status,
                            locked=rpc_server.locked)

    @policy.authorize_wsgi("mogan:server", "set_power_state")
    @expose.expose(None, types.uuid, wtypes.text,
                   status_code=http_client.ACCEPTED)
    def power(self, server_uuid, target):
        """Set the power state of the server.

        :param server_uuid: the UUID of a server.
        :param target: the desired target to change power state,
                       on, off or reboot.
        :raises Conflict (HTTP 409): if a power operation is
                 already in progress.
        :raises BadRequest (HTTP 400): if the requested target
                 state is not valid or if the server is in CLEANING state.

        """
        if target not in ["on", "off", "reboot", "soft_off", "soft_reboot"]:
            # ironic will throw InvalidStateRequested
            raise exception.InvalidActionParameterValue(
                value=target, action="power",
                server=server_uuid)

        rpc_server = self._resource or self._get_resource(server_uuid)
        pecan.request.engine_api.power(
            pecan.request.context, rpc_server, target)
        # At present we do not catch the Exception from ironicclient.
        # Such as Conflict and BadRequest.
        # varify provision_state, if server is being cleaned,
        # don't change power state?

        # Set the HTTP Location Header, user can get the power_state
        # by locaton.
        url_args = '/'.join([server_uuid, 'states'])
        pecan.response.location = link.build_url('servers', url_args)

    @policy.authorize_wsgi("mogan:server", "set_lock_state")
    @expose.expose(None, types.uuid, types.boolean,
                   status_code=http_client.ACCEPTED)
    def lock(self, server_uuid, target):
        """Set the lock state of the server.

        :param server_uuid: the UUID of a server.
        :param target: the desired target to change lock state,
                       true or false
        """
        rpc_server = self._resource or self._get_resource(server_uuid)
        context = pecan.request.context

        # Target is True, means lock a server
        if target:
            pecan.request.engine_api.lock(context, rpc_server)

        # Else, unlock the server
        else:
            # Try to unlock a server with non-admin or non-owner
            if not pecan.request.engine_api.is_expected_locked_by(
                    context, rpc_server):
                raise exception.Forbidden()
            pecan.request.engine_api.unlock(context, rpc_server)

    @policy.authorize_wsgi("mogan:server", "set_provision_state")
    @expose.expose(None, types.uuid, wtypes.text,
                   status_code=http_client.ACCEPTED)
    def provision(self, server_uuid, target):
        """Asynchronous trigger the provisioning of the server.

        This will set the target provision state of the server, and
        a background task will begin which actually applies the state
        change. This call will return a 202 (Accepted) indicating the
        request was accepted and is in progress; the client should
        continue to GET the status of this server to observe the
        status of the requested action.

        :param server_uuid: UUID of a server.
        :param target: The desired provision state of the server or verb.
        """

        # Currently we only support rebuild target
        if target not in (states.REBUILD,):
            raise exception.InvalidActionParameterValue(
                value=target, action="provision",
                server=server_uuid)

        rpc_server = self._resource or self._get_resource(server_uuid)
        if target == states.REBUILD:
            try:
                pecan.request.engine_api.rebuild(pecan.request.context,
                                                 rpc_server)
            except exception.ServerNotFound:
                msg = (_("Server %s could not be found") %
                       server_uuid)
                raise wsme.exc.ClientSideError(
                    msg, status_code=http_client.NOT_FOUND)

        # Set the HTTP Location Header
        url_args = '/'.join([server_uuid, 'states'])
        pecan.response.location = link.build_url('servers', url_args)


class FloatingIPController(ServerControllerBase):
    """REST controller for Server floatingips."""

    def __init__(self, *args, **kwargs):
        super(FloatingIPController, self).__init__(*args, **kwargs)
        self.network_api = network.API()

    @policy.authorize_wsgi("mogan:server", "associate_floatingip", False)
    @expose.expose(None, types.uuid, body=types.jsontype,
                   status_code=http_client.NO_CONTENT)
    def post(self, server_uuid, floatingip):
        """Add(Associate) Floating Ip.

        :param server_uuid: UUID of a server.
        :param floatingip: The floating IP within the request body.
        """
        validation.check_schema(floatingip, fip_schemas.add_floating_ip)

        server = self._resource or self._get_resource(server_uuid)
        address = floatingip['address']
        server_nics = server.nics

        if not server_nics:
            msg = _('No ports associated to server')
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)

        fixed_address = None
        if 'fixed_address' in floatingip:
            fixed_address = floatingip['fixed_address']
            for nic in server_nics:
                for port_address in nic.fixed_ips:
                    if port_address['ip_address'] == fixed_address:
                        break
                else:
                    continue
                break
            else:
                msg = _('Specified fixed address not assigned to server')
                raise wsme.exc.ClientSideError(
                    msg, status_code=http_client.BAD_REQUEST)

        if not fixed_address:
            for nic in server_nics:
                for port_address in nic.fixed_ips:
                    if netutils.is_valid_ipv4(port_address['ip_address']):
                        fixed_address = port_address['ip_address']
                        break
                else:
                    continue
                break
            else:
                msg = _('Unable to associate floating IP %(address)s '
                        'to any fixed IPs for server %(id)s. '
                        'Server has no fixed IPv4 addresses to '
                        'associate.') % ({'address': address,
                                          'id': server.uuid})
                raise wsme.exc.ClientSideError(
                    msg, status_code=http_client.BAD_REQUEST)
            if len(server_nics) > 1:
                LOG.warning('multiple ports exist, using the first '
                            'IPv4 fixed_ip: %s', fixed_address)

        try:
            self.network_api.associate_floating_ip(
                pecan.request.context, floating_address=address,
                port_id=nic.port_id, fixed_address=fixed_address)
        except exception.FloatingIpNotFoundForAddress as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.NOT_FOUND)
        except exception.Forbidden as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.FORBIDDEN)
        except Exception as e:
            msg = _('Unable to associate floating IP %(address)s to '
                    'fixed IP %(fixed_address)s for server %(id)s. '
                    'Error: %(error)s') % ({'address': address,
                                            'fixed_address': fixed_address,
                                            'id': server.uuid, 'error': e})
            LOG.exception(msg)
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)

    @policy.authorize_wsgi("mogan:server", "disassociate_floatingip")
    @expose.expose(None, types.uuid, wtypes.text,
                   status_code=http_client.NO_CONTENT)
    def delete(self, server_uuid, address):
        """Dissociate floating_ip from a server.

        :param server_uuid: UUID of a server.
        :param floatingip: The floating IP within the request body.
        """
        if not netutils.is_valid_ipv4(address):
            msg = "Invalid IP address %s" % address
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)
        # get the floating ip object
        try:
            floating_ip = self.network_api.get_floating_ip_by_address(
                pecan.request.context, address)
        except exception.FloatingIpNotFoundForAddress:
            msg = _("floating IP not found")
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.NOT_FOUND)

        # get the associated server object (if any)
        try:
            server_id =\
                self.network_api.get_server_id_by_floating_address(
                    pecan.request.context, address)
        except exception.FloatingIpNotFoundForAddress as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.NOT_FOUND)
        except exception.FloatingIpMultipleFoundForAddress as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.CONFLICT)

        # disassociate if associated
        if (floating_ip.get('port_id') and server_id == server_uuid):
            try:
                self.network_api.disassociate_floating_ip(
                    pecan.request.context, address)
            except exception.Forbidden as e:
                raise wsme.exc.ClientSideError(
                    e.message, status_code=http_client.FORBIDDEN)
            except exception.CannotDisassociateAutoAssignedFloatingIP:
                msg = _('Cannot disassociate auto assigned floating IP')
                raise wsme.exc.ClientSideError(
                    msg, status_code=http_client.FORBIDDEN)
            except exception.FloatingIpNotAssociated:
                msg = _('Floating IP is not associated')
                raise wsme.exc.ClientSideError(
                    msg, status_code=http_client.BAD_REQUEST)
        else:
            msg = _("Floating IP %(address)s is not associated with server "
                    "%(id)s.") % {'address': address, 'id': server_uuid}
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)


class InterfaceController(ServerControllerBase):
    def __init__(self, *args, **kwargs):
        super(InterfaceController, self).__init__(*args, **kwargs)

    @policy.authorize_wsgi("mogan:server", "attach_interface", False)
    @expose.expose(None, types.uuid, body=types.jsontype,
                   status_code=http_client.NO_CONTENT)
    def post(self, server_uuid, interface):
        """Attach Interface.

        :param server_uuid: UUID of a server.
        :param interface: The Baremetal Network ID within the request body.
        """
        validation.check_schema(interface, interface_schemas.attach_interface)

        net_id = interface.get('net_id', None)

        if not net_id:
            msg = _("Must input network_id")
            raise exc.HTTPBadRequest(explanation=msg)

        server = self._resource or self._get_resource(server_uuid)
        try:
            pecan.request.engine_api.attach_interface(
                pecan.request.context,
                server, net_id)
        except (exception.ServerIsLocked,
                exception.ComputePortNotAvailable,
                exception.NetworkNotFound) as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.BAD_REQUEST)
        except exception.InterfaceAttachFailed as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.CONFLICT)


class ServerNetworks(base.APIBase):
    """API representation of the networks of a server."""

    nics = types.jsontype
    """The instance nics information of the server"""

    def __init__(self, **kwargs):
        self.fields = ['nics']
        ret_nics = api_utils.show_nics(kwargs.get('nics') or [])
        super(ServerNetworks, self).__init__(nics=ret_nics)


class ServerNetworksController(ServerControllerBase):
    """REST controller for Server networks."""

    floatingips = FloatingIPController()
    """Expose floatingip as a sub-element of networks"""
    interfaces = InterfaceController()
    """Expose interface as a sub-element of networks"""

    @policy.authorize_wsgi("mogan:server", "get_networks")
    @expose.expose(ServerNetworks, types.uuid)
    def get(self, server_uuid):
        """List the networks info of the server.

        :param server_uuid: the UUID of a server.
        """
        rpc_server = self._resource or self._get_resource(server_uuid)
        return ServerNetworks(nics=rpc_server.nics.as_list_of_dict())


class Server(base.APIBase):
    """API representation of a server.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a server.
    """
    uuid = types.uuid
    """The UUID of the server"""

    name = wsme.wsattr(wtypes.text, mandatory=True)
    """The name of the server"""

    description = wtypes.text
    """The description of the server"""

    project_id = types.uuid
    """The project UUID of the server"""

    user_id = types.uuid
    """The user UUID of the server"""

    status = wtypes.text
    """The status of the server"""

    power_state = wtypes.text
    """The power state of the server"""

    availability_zone = wtypes.text
    """The availability zone of the server"""

    flavor_uuid = types.uuid
    """The server type UUID of the server"""

    image_uuid = types.uuid
    """The image UUID of the server"""

    nics = types.jsontype
    """The nics information of the server"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link"""

    launched_at = datetime.datetime
    """The UTC date and time of the server launched"""

    extra = {wtypes.text: types.jsontype}
    """The meta data of the server"""

    fault_info = {wtypes.text: types.jsontype}
    """The fault info of the server"""

    def __init__(self, **kwargs):
        super(Server, self).__init__(**kwargs)
        self.fields = []
        for field in objects.Server.fields:
            if field == 'nics':
                self.fields.append(field)
                nics = api_utils.show_nics(kwargs.get('nics') or [])
                setattr(self, field, nics)
                continue
            if field == 'fault':
                if kwargs.get('status', None) == 'error':
                    fault_info = kwargs.get(field, None)
                    if fault_info is not None:
                        fault_info = fault_info.return_dict()
                        setattr(self, 'fault_info', fault_info)
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @classmethod
    def convert_with_links(cls, server_data, fields=None):
        server = Server(**server_data)
        server_uuid = server.uuid
        if fields is not None:
            server.unset_fields_except(fields)
        url = pecan.request.public_url
        server.links = [link.Link.make_link('self',
                                            url,
                                            'servers', server_uuid),
                        link.Link.make_link('bookmark',
                                            url,
                                            'servers', server_uuid,
                                            bookmark=True)
                        ]
        return server


class ServerPatchType(types.JsonPatchType):

    _api_base = Server

    @staticmethod
    def internal_attrs():
        defaults = types.JsonPatchType.internal_attrs()
        return defaults + ['/project_id', '/user_id', '/status',
                           '/power_state', '/availability_zone',
                           '/flavor_uuid', '/image_uuid',
                           '/nics', '/launched_at']


class ServerCollection(base.APIBase):
    """API representation of a collection of server."""

    servers = [Server]
    """A list containing server objects"""

    @staticmethod
    def convert_with_links(servers_data, fields=None):
        collection = ServerCollection()
        collection.servers = [Server.convert_with_links(server, fields)
                              for server in servers_data]
        return collection


class ServerConsole(base.APIBase):
    """API representation of the console of a server."""

    console = {wtypes.text: types.jsontype}
    """The console information of the server"""


class ServerSerialConsoleController(ServerControllerBase):
    """REST controller for Server."""

    @policy.authorize_wsgi("mogan:server", "get_serial_console")
    @expose.expose(ServerConsole, types.uuid)
    def get(self, server_uuid):
        """Get the serial console info of the server.

        :param server_uuid: the UUID of a server.
        """
        server_obj = self._resource or self._get_resource(server_uuid)
        console = pecan.request.engine_api.get_serial_console(
            pecan.request.context, server_obj)
        return ServerConsole(console=console)


class ServerController(ServerControllerBase):
    """REST controller for Server."""

    states = ServerStatesController()
    """Expose the state controller action as a sub-element of servers"""

    networks = ServerNetworksController()
    """Expose the network controller action as a sub-element of servers"""

    serial_console = ServerSerialConsoleController()
    """Expose the console controller of servers"""

    _custom_actions = {
        'detail': ['GET']
    }

    def _get_server_collection(self, fields=None, all_tenants=False):
        context = pecan.request.context
        project_only = True
        if context.is_admin and all_tenants:
            project_only = False

        servers = objects.Server.list(pecan.request.context,
                                      project_only=project_only)
        servers_data = [server.as_dict() for server in servers]

        return ServerCollection.convert_with_links(servers_data,
                                                   fields=fields)

    @expose.expose(ServerCollection, types.listtype, types.boolean)
    def get_all(self, fields=None, all_tenants=None):
        """Retrieve a list of server.

        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        :param all_tenants: Optional, allows administrators to see the
                            servers owned by all tenants, otherwise only the
                            servers associated with the calling tenant are
                            included in the response.
        """
        if fields is None:
            fields = _DEFAULT_SERVER_RETURN_FIELDS
        return self._get_server_collection(fields=fields,
                                           all_tenants=all_tenants)

    @policy.authorize_wsgi("mogan:server", "get")
    @expose.expose(Server, types.uuid, types.listtype)
    def get_one(self, server_uuid, fields=None):
        """Retrieve information about the given server.

        :param server_uuid: UUID of a server.
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        rpc_server = self._resource or self._get_resource(server_uuid)
        server_data = rpc_server.as_dict()

        return Server.convert_with_links(server_data, fields=fields)

    @expose.expose(ServerCollection, types.boolean)
    def detail(self, all_tenants=None):
        """Retrieve detail of a list of servers."""
        # /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "servers":
            raise exception.NotFound()
        return self._get_server_collection(all_tenants=all_tenants)

    def _check_flavor_and_networks(self, flavor, networks):
        if len(networks) > len(flavor.nics):
            raise exception.NetworksNotMatch(
                _("Requested networks require more nics than the "
                  "selected flavor."))

        nics = flavor.nics
        for net in networks:
            if 'port_type' in net:
                try:
                    index = [nic.get('type')
                             for nic in nics].index(net.get('port_type'))
                    nics.pop(index)
                except ValueError:
                    raise exception.NetworksNotMatch(
                        _("Requested networks require more specific nic "
                          "type %s than the selected flavor."),
                        net.get('port_type'))

    @policy.authorize_wsgi("mogan:server", "create", False)
    @expose.expose(Server, body=types.jsontype,
                   status_code=http_client.CREATED)
    def post(self, server):
        """Create a new server.

        :param server: a server within the request body.
        """
        validation.check_schema(server, server_schemas.create_server)
        server = server['server']
        scheduler_hints = server.get('scheduler_hints', {})

        min_count = server.get('min_count', 1)
        max_count = server.get('max_count', min_count)

        if min_count > max_count:
            msg = _('min_count must be <= max_count')
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)

        requested_networks = server.pop('networks', None)
        flavor_uuid = server.get('flavor_uuid')
        image_uuid = server.get('image_uuid')
        user_data = server.get('user_data')
        key_name = server.get('key_name')
        personality = server.pop('personality', None)

        injected_files = []
        if personality:
            for item in personality:
                injected_files.append((item['path'], item['contents']))

        try:
            flavor = objects.Flavor.get(pecan.request.context, flavor_uuid)
            self._check_flavor_and_networks(flavor, requested_networks)

            servers = pecan.request.engine_api.create(
                pecan.request.context,
                flavor,
                image_uuid=image_uuid,
                name=server.get('name'),
                description=server.get('description'),
                availability_zone=server.get('availability_zone'),
                extra=server.get('extra'),
                requested_networks=requested_networks,
                user_data=user_data,
                injected_files=injected_files,
                key_name=key_name,
                min_count=min_count,
                max_count=max_count,
                scheduler_hints=scheduler_hints)
        except exception.FlavorNotFound:
            msg = (_("Flavor %s could not be found") %
                   flavor_uuid)
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)
        except exception.ImageNotFound:
            msg = (_("Requested image %s could not be found") % image_uuid)
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)
        except exception.KeypairNotFound:
            msg = (_("Invalid key_name %s provided.") % key_name)
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)
        except exception.PortLimitExceeded as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.FORBIDDEN)
        except exception.AZNotFound:
            msg = _('The requested availability zone is not available')
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)
        except (exception.GlanceConnectionFailed,
                exception.ServerUserDataMalformed,
                exception.ServerUserDataTooLarge,
                exception.Base64Exception,
                exception.NetworkRequiresSubnet,
                exception.NetworkNotFound,
                exception.NetworksNotMatch) as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.BAD_REQUEST)

        # Set the HTTP Location Header for the first server.
        pecan.response.location = link.build_url('server', servers[0].uuid)
        return Server.convert_with_links(servers[0])

    @policy.authorize_wsgi("mogan:server", "update")
    @wsme.validate(types.uuid, [ServerPatchType])
    @expose.expose(Server, types.uuid, body=[ServerPatchType])
    def patch(self, server_uuid, patch):
        """Update a server.

        :param server_uuid: UUID of a server.
        :param patch: a json PATCH document to apply to this server.
        """
        rpc_server = self._resource or self._get_resource(server_uuid)
        try:
            server = Server(
                **api_utils.apply_jsonpatch(rpc_server.as_dict(), patch))

        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Server.fields:
            if field == 'nics':
                continue
            try:
                patch_val = getattr(server, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if rpc_server[field] != patch_val:
                rpc_server[field] = patch_val

        rpc_server.save()

        return Server.convert_with_links(rpc_server.as_dict())

    @policy.authorize_wsgi("mogan:server", "delete")
    @expose.expose(None, types.uuid, status_code=http_client.NO_CONTENT)
    def delete(self, server_uuid):
        """Delete a server.

        :param server_uuid: UUID of a server.
        """
        rpc_server = self._resource or self._get_resource(server_uuid)
        pecan.request.engine_api.delete(pecan.request.context, rpc_server)
