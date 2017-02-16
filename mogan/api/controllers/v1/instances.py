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
import wsme
from wsme import types as wtypes

from mogan.api.controllers import base
from mogan.api.controllers import link
from mogan.api.controllers.v1.schemas import floating_ips as fip_schemas
from mogan.api.controllers.v1.schemas import instances as inst_schemas
from mogan.api.controllers.v1 import types
from mogan.api.controllers.v1 import utils as api_utils
from mogan.api import expose
from mogan.api import validation
from mogan.common import exception
from mogan.common.i18n import _
from mogan.common.i18n import _LW
from mogan.common import policy
from mogan.common import states
from mogan.engine.baremetal import ironic_states as ir_states
from mogan import network
from mogan import objects

_DEFAULT_INSTANCE_RETURN_FIELDS = ('uuid', 'name', 'description',
                                   'status', 'power_state')

LOG = log.getLogger(__name__)


class InstanceStates(base.APIBase):
    """API representation of the states of a instance."""

    power_state = wtypes.text
    """Represent the current power state of the instance"""

    status = wtypes.text
    """Represent the current status of the instance"""

    @classmethod
    def sample(cls):
        sample = cls(power_state=ir_states.POWER_ON, status=states.ACTIVE)
        return sample


class InstanceControllerBase(rest.RestController):
    _resource = None

    # This _resource is used for authorization.
    def _get_resource(self, uuid, *args, **kwargs):
        self._resource = objects.Instance.get(pecan.request.context, uuid)
        return self._resource


class InstanceStatesController(InstanceControllerBase):

    _custom_actions = {
        'power': ['PUT'],
    }

    @policy.authorize_wsgi("mogan:instance", "get_states")
    @expose.expose(InstanceStates, types.uuid)
    def get(self, instance_uuid):
        """List the states of the instance, just support power state at present.

        :param instance_uuid: the UUID of a instance.
        """
        rpc_instance = self._resource or self._get_resource(instance_uuid)

        return InstanceStates(power_state=rpc_instance.power_state,
                              status=rpc_instance.status)

    @policy.authorize_wsgi("mogan:instance", "set_power_state")
    @expose.expose(None, types.uuid, wtypes.text,
                   status_code=http_client.ACCEPTED)
    def power(self, instance_uuid, target):
        """Set the power state of the instance.

        :param instance_uuid: the UUID of a instance.
        :param target: the desired target to change power state,
                       on, off or reboot.
        :raises: Conflict (HTTP 409) if a power operation is
                 already in progress.
        :raises: BadRequest (HTTP 400) if the requested target
                 state is not valid or if the instance is in CLEANING state.

        """
        if target not in ["on", "off", "reboot"]:
            # ironic will throw InvalidStateRequested
            raise exception.InvalidActionParameterValue(
                value=target, action="power",
                instance=instance_uuid)

        rpc_instance = self._resource or self._get_resource(instance_uuid)
        pecan.request.engine_api.power(
            pecan.request.context, rpc_instance, target)
        # At present we do not catch the Exception from ironicclient.
        # Such as Conflict and BadRequest.
        # varify provision_state, if instance is being cleaned,
        # don't change power state?

        # Set the HTTP Location Header, user can get the power_state
        # by locaton.
        url_args = '/'.join([instance_uuid, 'states'])
        pecan.response.location = link.build_url('instances', url_args)


class FloatingIPController(InstanceControllerBase):
    """REST controller for Instance floatingips."""

    def __init__(self, *args, **kwargs):
        super(FloatingIPController, self).__init__(*args, **kwargs)
        self.network_api = network.API()

    @policy.authorize_wsgi("mogan:instance", "associate_floatingip", False)
    @expose.expose(None, types.uuid, body=types.jsontype,
                   status_code=http_client.NO_CONTENT)
    def post(self, instance_uuid, floatingip):
        """Add(Associate) Floating Ip.

        :param instance_uuid: UUID of a instance.
        :param floatingip: The floating IP within the request body.
        """
        validation.check_schema(floatingip, fip_schemas.add_floating_ip)

        instance = self._resource or self._get_resource(instance_uuid)
        address = floatingip['address']
        ports = instance.network_info

        if not ports:
            msg = _('No ports associated to instance')
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)

        fixed_address = None
        if 'fixed_address' in floatingip:
            fixed_address = floatingip['fixed_address']
            for port_id, port in ports.items():
                for port_address in port['fixed_ips']:
                    if port_address['ip_address'] == fixed_address:
                        break
                else:
                    continue
                break
            else:
                msg = _('Specified fixed address not assigned to instance')
                raise wsme.exc.ClientSideError(
                    msg, status_code=http_client.BAD_REQUEST)

        if not fixed_address:
            for port_id, port in ports.items():
                for port_address in port['fixed_ips']:
                    if netutils.is_valid_ipv4(port_address['ip_address']):
                        fixed_address = port_address['ip_address']
                        break
                else:
                    continue
                break
            else:
                msg = _('Unable to associate floating IP %(address)s '
                        'to any fixed IPs for instance %(id)s. '
                        'Instance has no fixed IPv4 addresses to '
                        'associate.') % ({'address': address,
                                          'id': instance.uuid})
                raise wsme.exc.ClientSideError(
                    msg, status_code=http_client.BAD_REQUEST)
            if len(ports) > 1:
                LOG.warning(_LW('multiple ports exist, using the first '
                                'IPv4 fixed_ip: %s'), fixed_address)

        try:
            self.network_api.associate_floating_ip(
                pecan.request.context, floating_address=address,
                port_id=port_id, fixed_address=fixed_address)
        except exception.FloatingIpNotFoundForAddress as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.NOT_FOUND)
        except exception.Forbidden as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.FORBIDDEN)
        except Exception as e:
            msg = _('Unable to associate floating IP %(address)s to '
                    'fixed IP %(fixed_address)s for instance %(id)s. '
                    'Error: %(error)s') % ({'address': address,
                                            'fixed_address': fixed_address,
                                            'id': instance.uuid, 'error': e})
            LOG.exception(msg)
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)

    @policy.authorize_wsgi("mogan:instance", "disassociate_floatingip")
    @expose.expose(None, types.uuid, wtypes.text,
                   status_code=http_client.NO_CONTENT)
    def delete(self, instance_uuid, address):
        """Dissociate floating_ip from an instance.

        :param instance_uuid: UUID of a instance.
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

        # get the associated instance object (if any)
        try:
            instance_id =\
                self.network_api.get_instance_id_by_floating_address(
                    pecan.request.context, address)
        except exception.FloatingIpNotFoundForAddress as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.NOT_FOUND)
        except exception.FloatingIpMultipleFoundForAddress as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.CONFLICT)

        # disassociate if associated
        if (floating_ip.get('port_id') and instance_id == instance_uuid):
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
            msg = _("Floating IP %(address)s is not associated with instance "
                    "%(id)s.") % {'address': address, 'id': instance_uuid}
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)


class InstanceNetworks(base.APIBase):
    """API representation of the networks of an instance."""

    ports = {wtypes.text: types.jsontype}
    """The network information of the instance"""


class InstanceNetworksController(InstanceControllerBase):
    """REST controller for Instance networks."""

    floatingips = FloatingIPController()
    """Expose floatingip as a sub-element of networks"""

    @policy.authorize_wsgi("mogan:instance", "get_networks")
    @expose.expose(InstanceNetworks, types.uuid)
    def get(self, instance_uuid):
        """List the networks info of the instance.

        :param instance_uuid: the UUID of a instance.
        """
        rpc_instance = self._resource or self._get_resource(instance_uuid)

        return InstanceNetworks(ports=rpc_instance.network_info)


class Instance(base.APIBase):
    """API representation of a instance.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a instance.
    """
    uuid = types.uuid
    """The UUID of the instance"""

    name = wsme.wsattr(wtypes.text, mandatory=True)
    """The name of the instance"""

    description = wtypes.text
    """The description of the instance"""

    project_id = types.uuid
    """The project UUID of the instance"""

    user_id = types.uuid
    """The user UUID of the instance"""

    status = wtypes.text
    """The status of the instance"""

    power_state = wtypes.text
    """The power state of the instance"""

    availability_zone = wtypes.text
    """The availability zone of the instance"""

    instance_type_uuid = types.uuid
    """The instance type UUID of the instance"""

    image_uuid = types.uuid
    """The image UUID of the instance"""

    network_info = {wtypes.text: types.jsontype}
    """The network information of the instance"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link"""

    launched_at = datetime.datetime
    """The UTC date and time of the instance launched"""

    extra = {wtypes.text: types.jsontype}
    """The meta data of the instance"""

    def __init__(self, **kwargs):
        super(Instance, self).__init__(**kwargs)
        self.fields = []
        for field in objects.Instance.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @classmethod
    def convert_with_links(cls, instance_data, fields=None):
        instance = Instance(**instance_data)
        instance_uuid = instance.uuid
        if fields is not None:
            instance.unset_fields_except(fields)
        url = pecan.request.public_url
        instance.links = [link.Link.make_link('self',
                                              url,
                                              'instances', instance_uuid),
                          link.Link.make_link('bookmark',
                                              url,
                                              'instances', instance_uuid,
                                              bookmark=True)
                          ]
        return instance


class InstancePatchType(types.JsonPatchType):

    _api_base = Instance

    @staticmethod
    def internal_attrs():
        defaults = types.JsonPatchType.internal_attrs()
        return defaults + ['/project_id', '/user_id', '/status',
                           '/power_state', '/availability_zone',
                           '/instance_type_uuid', 'image_uuid',
                           '/network_info', '/launched_at']


class InstanceCollection(base.APIBase):
    """API representation of a collection of instance."""

    instances = [Instance]
    """A list containing instance objects"""

    @staticmethod
    def convert_with_links(instances_data, fields=None):
        collection = InstanceCollection()
        collection.instances = [Instance.convert_with_links(inst, fields)
                                for inst in instances_data]
        return collection


class InstanceController(InstanceControllerBase):
    """REST controller for Instance."""

    states = InstanceStatesController()
    """Expose the state controller action as a sub-element of instances"""

    networks = InstanceNetworksController()
    """Expose the network controller action as a sub-element of instances"""

    _custom_actions = {
        'detail': ['GET']
    }

    def _get_instance_collection(self, fields=None, all_tenants=False):
        context = pecan.request.context
        project_only = True
        if context.is_admin and all_tenants:
            project_only = False

        instances = objects.Instance.list(pecan.request.context,
                                          project_only=project_only)
        instances_data = [instance.as_dict() for instance in instances]

        return InstanceCollection.convert_with_links(instances_data,
                                                     fields=fields)

    @expose.expose(InstanceCollection, types.listtype, types.boolean)
    def get_all(self, fields=None, all_tenants=None):
        """Retrieve a list of instance.

        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        :param all_tenants: Optional, allows administrators to see the
                            servers owned by all tenants, otherwise only the
                            servers associated with the calling tenant are
                            included in the response.
        """
        if fields is None:
            fields = _DEFAULT_INSTANCE_RETURN_FIELDS
        return self._get_instance_collection(fields=fields,
                                             all_tenants=all_tenants)

    @policy.authorize_wsgi("mogan:instance", "get")
    @expose.expose(Instance, types.uuid, types.listtype)
    def get_one(self, instance_uuid, fields=None):
        """Retrieve information about the given instance.

        :param instance_uuid: UUID of a instance.
        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        rpc_instance = self._resource or self._get_resource(instance_uuid)
        instance_data = rpc_instance.as_dict()

        return Instance.convert_with_links(instance_data, fields=fields)

    @expose.expose(InstanceCollection, types.boolean)
    def detail(self, all_tenants=None):
        """Retrieve detail of a list of instances."""
        # /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "instances":
            raise exception.NotFound()
        return self._get_instance_collection(all_tenants=all_tenants)

    @policy.authorize_wsgi("mogan:instance", "create", False)
    @expose.expose(Instance, body=types.jsontype,
                   status_code=http_client.CREATED)
    def post(self, instance):
        """Create a new instance.

        :param instance: a instance within the request body.
        """
        validation.check_schema(instance, inst_schemas.create_instance)

        min_count = instance.get('min_count', 1)
        max_count = instance.get('max_count', min_count)

        if min_count > max_count:
            msg = _('min_count must be <= max_count')
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)

        requested_networks = instance.pop('networks', None)
        instance_type_uuid = instance.get('instance_type_uuid')
        image_uuid = instance.get('image_uuid')

        try:
            instance_type = objects.InstanceType.get(pecan.request.context,
                                                     instance_type_uuid)

            instances = pecan.request.engine_api.create(
                pecan.request.context,
                instance_type,
                image_uuid=image_uuid,
                name=instance.get('name'),
                description=instance.get('description'),
                availability_zone=instance.get('availability_zone'),
                extra=instance.get('extra'),
                requested_networks=requested_networks,
                min_count=min_count,
                max_count=max_count)
        except exception.InstanceTypeNotFound:
            msg = (_("InstanceType %s could not be found") %
                   instance_type_uuid)
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)
        except exception.ImageNotFound:
            msg = (_("Requested image %s could not be found") % image_uuid)
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
                exception.exception.NetworkRequiresSubnet,
                exception.NetworkNotFound) as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.BAD_REQUEST)

        # Set the HTTP Location Header for the first instance.
        pecan.response.location = link.build_url('instance', instances[0].uuid)
        return Instance.convert_with_links(instances[0])

    @policy.authorize_wsgi("mogan:instance", "update")
    @wsme.validate(types.uuid, [InstancePatchType])
    @expose.expose(Instance, types.uuid, body=[InstancePatchType])
    def patch(self, instance_uuid, patch):
        """Update an instance.

        :param instance_uuid: UUID of an instance.
        :param patch: a json PATCH document to apply to this instance.
        """
        rpc_instance = self._resource or self._get_resource(instance_uuid)
        try:
            instance = Instance(
                **api_utils.apply_jsonpatch(rpc_instance.as_dict(), patch))

        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Instance.fields:
            try:
                patch_val = getattr(instance, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if rpc_instance[field] != patch_val:
                rpc_instance[field] = patch_val

        rpc_instance.save()

        return Instance.convert_with_links(rpc_instance)

    @policy.authorize_wsgi("mogan:instance", "delete")
    @expose.expose(None, types.uuid, status_code=http_client.NO_CONTENT)
    def delete(self, instance_uuid):
        """Delete a instance.

        :param instance_uuid: UUID of a instance.
        """
        rpc_instance = self._resource or self._get_resource(instance_uuid)
        pecan.request.engine_api.delete(pecan.request.context, rpc_instance)
