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

import jsonschema
import pecan
from pecan import rest
from six.moves import http_client
import wsme
from wsme import types as wtypes

from nimble.api.controllers import base
from nimble.api.controllers import link
from nimble.api.controllers.v1 import types
from nimble.api import expose
from nimble.common import exception
from nimble.common.i18n import _
from nimble.engine.baremetal.ironic import get_node_by_instance
from nimble import objects

_DEFAULT_INSTANCE_RETURN_FIELDS = ('id', 'uuid', 'name', 'description',
                                   'status')


_CREATE_INSTANCE_SCHEMA = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Create instance schema",
    "type": "object",
    "properties": {
        'name': {'type': 'string', 'minLength': 1, 'maxLength': 255},
        'description': {'type': 'string', 'minLength': 1, 'maxLength': 255},
        'availability_zone': {'type': 'string', 'minLength': 1,
                              'maxLength': 255},
        'image_uuid': {'type': 'string', 'format': 'uuid'},
        'instance_type_uuid': {'type': 'string', 'format': 'uuid'},
        'networks': {
            'type': 'array', 'minItems': 1,
            'items': {
                'type': 'object',
                'properties': {
                    'uuid': {'type': 'string', 'format': 'uuid'},
                    'type': {'type': 'string', 'minLength': 1,
                             'maxLength': 255},
                },
                'required': ['uuid'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['name', 'image_uuid', 'instance_type_uuid', 'networks'],
    'additionalProperties': False,
}


class Instance(base.APIBase):
    """API representation of a instance.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a instance.
    """
    id = wsme.wsattr(wtypes.IntegerType(minimum=1))
    """The ID of the instance"""

    uuid = types.uuid
    """The UUID of the instance"""

    name = wtypes.text
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

    target_power_state = wtypes.text
    """The user modified desired power state of the instance"""

    provision_state = wtypes.text
    """The provision state of the instance"""

    target_provision_state = wtypes.text
    """The user modified desired provision state of the instance"""

    last_error = wtypes.text
    """Any error from the most recent transaction that started
       but failed to finish
    """

    maintenance = wtypes.text
    """Whether or not this node is currently in maintenance mode"""

    properties = {wtypes.text: types.jsontype}
    """The physical characteristics of this node"""

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

    def __init__(self, **kwargs):
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
        instance.unset_fields_except(fields)
        url = pecan.request.public_url
        instance.links = [link.Link.make_link('self',
                                              url,
                                              'instances', instance.uuid),
                          link.Link.make_link('bookmark',
                                              url,
                                              'instances', instance.uuid,
                                              bookmark=True)
                          ]

        return instance


class InstanceCollection(base.APIBase):
    """API representation of a collection of instance."""

    instances = [Instance]
    """A list containing instance objects"""

    @staticmethod
    def convert_with_links(instances, fields=None, **kwargs):
        collection = InstanceCollection()
        collection.instances = [Instance.convert_with_links(inst, fields)
                                for inst in instances]
        return collection


class InstanceActionController(rest.RestController):

    _custom_actions = {
        'power': ['PUT'],
    }


class InstanceController(rest.RestController):
    """REST controller for Instance."""

    action = InstanceActionController()

    _custom_actions = {
        'detail': ['GET']
    }

    def _get_instance_collection(self, instance_uuid,
                                 detail=False, fields=None):
        if instance_uuid:
            instances = objects.Instance.get(pecan.request.context,
                                             instance_uuid)
        else:
            instances = objects.Instance.list(pecan.request.context)
        instance_data = []

        if detail:
            for instance in instances:
                node_info = get_node_by_instance(instance.uuid)
                instance_data.append(
                    self._merge_node(instance.as_dict(), node_info))

        return InstanceCollection.convert_with_links(instance_data,
                                                     fields=fields)

    def _merge_node(self, rpc_instance, node):
        instance_data = rpc_instance.as_dict()
        instance_data.update(node)
        return instance_data

    @expose.expose(InstanceCollection, types.uuid, types.listtype)
    def get_all(self, instance_uuid=None, fields=None):
        """Retrieve a list of instance.

        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        if fields is None:
            fields = _DEFAULT_INSTANCE_RETURN_FIELDS
        return self._get_instance_collection(instance_uuid, fields=fields)

    @expose.expose(Instance, types.uuid)
    def get_one(self, instance_uuid):
        """Retrieve information about the given instance.

        :param instance_uuid: UUID of a instance.
        """
        rpc_instance = objects.Instance.get(pecan.request.context,
                                            instance_uuid)
        node = get_node_by_instance(instance_uuid)
        instance_data = self._merge_node(rpc_instance, node)
        return Instance.convert_with_links(Instance(**instance_data), node)

    @expose.expose(InstanceCollection, types.uuid)
    def detail(self, instance_uuid=None):
        """Retrieve detail of a list of instances.

        :param instance_uuid: Optional UUID of an instance, to find the node
                              associated with that instance.
        """
        # /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "instances":
            raise exception.NotFound()
        return self._get_instance_collection(instance_uuid, detail=True)

    @expose.expose(Instance, body=types.jsontype,
                   status_code=http_client.CREATED)
    def post(self, instance):
        """Create a new instance.

        :param instance: a instance within the request body.
        """
        # Add jsonschema validate
        _check_create_body(instance)

        requested_networks = instance.pop('networks', None)
        instance_type_uuid = instance.get('instance_type_uuid')

        try:
            instance_type = objects.InstanceType.get(pecan.request.context,
                                                     instance_type_uuid)
        except exception.InstanceTypeNotFound:
            msg = (_("InstanceType %s could not be found") %
                   instance_type_uuid)
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)

        instance_obj = objects.Instance(pecan.request.context, **instance)
        instance_obj.create()

        instance_obj.user_id = pecan.request.context.user_id
        instance_obj.project_id = pecan.request.context.project_id
        instance_obj.save()

        # TODO(zhenguo): Catch exceptions
        pecan.request.rpcapi.create_instance(pecan.request.context,
                                             instance_obj,
                                             requested_networks,
                                             instance_type)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('instance', instance_obj.uuid)
        return Instance.convert_with_links(instance_obj)

    @expose.expose(None, types.uuid, status_code=http_client.NO_CONTENT)
    def delete(self, instance_uuid):
        """Delete a instance.

        :param instance_uuid: UUID of a instance.
        """
        rpc_instance = objects.Instance.get(pecan.request.context,
                                            instance_uuid)
        pecan.request.rpcapi.delete_instance(pecan.request.context,
                                             rpc_instance)


def _check_create_body(body):
    """Ensure all necessary keys are present and correct in create body.

    Check that the user-specified create body is in the expected format and
    include the required information.

    :param body: create instance body
    :raises: InvalidParameterValue if validation of create body fails.
    """
    try:
        jsonschema.validate(body, _CREATE_INSTANCE_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise exception.InvalidParameterValue(_('Invalid create body: %s') %
                                              exc)
