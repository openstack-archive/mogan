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
from oslo_log import log
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
from nimble.common.i18n import _LW
from nimble.engine.baremetal.ironic import get_node_by_instance
from nimble.engine.baremetal.ironic import get_node_list
from nimble.engine.baremetal import ironic_states as ir_states
from nimble import objects

_DEFAULT_INSTANCE_RETURN_FIELDS = ('uuid', 'name', 'description',
                                   'status')

_NODE_DETAIL_FIELDS = ('power_state', 'instance_uuid')

LOG = log.getLogger(__name__)

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
                    'port_type': {'type': 'string', 'minLength': 1,
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


class InstanceStates(base.APIBase):
    """API representation of the states of a instance."""
    # Just support power state at present.
    # We can expend other fields for other type state.
    power_state = wtypes.text
    """Represent the current (not transition) power state of the instance"""

    target_power_state = wtypes.text
    """The user modified desired power state of the instance."""

    @staticmethod
    def convert(instance_states):
        attr_list = ['power_state', 'target_power_state']
        states = InstanceStates()
        for attr in attr_list:
            setattr(states, attr, getattr(instance_states, attr))
        return states

    @classmethod
    def sample(cls):
        sample = cls(target_power_state=ir_states.POWER_ON,
                     power_state=ir_states.POWER_ON)
        return sample


class InstanceStatesController(rest.RestController):
    # Note(Shaohe Feng) we follow ironic restful api define.
    # We can refactor this API, if we do not like ironic pattern.

    _custom_actions = {
        'power': ['PUT'],
    }

    @expose.expose(InstanceStates, types.uuid)
    def get(self, instance_uuid):
        """List the states of the instance, just support power state at present.

        :param instance_uuid: the UUID of a instance.
        """
        rpc_instance = objects.Instance.get(pecan.request.context,
                                            instance_uuid)

        rpc_states = pecan.request.rpcapi.instance_states(
            pecan.request.context, rpc_instance)
        return InstanceStates.convert(rpc_states.to_dict())

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
        # No policy check at present.
        rpc_instance = objects.Instance.get(pecan.request.context,
                                            instance_uuid)

        if target not in ["on", "off", "reboot"]:
            # ironic will throw InvalidStateRequested
            raise exception.InvalidActionParameterValue(
                value=target, action="power",
                instance=instance_uuid)
        pecan.request.rpcapi.set_power_state(pecan.request.context,
                                             rpc_instance, target)
        # At present we do not catch the Exception from ironicclient.
        # Such as Conflict and BadRequest.
        # varify provision_state, if instance is being cleaned,
        # don't change power state?

        # Set the HTTP Location Header, user can get the power_state
        # by locaton.
        url_args = '/'.join([instance_uuid, 'states'])
        pecan.response.location = link.build_url('instances', url_args)


class Instance(base.APIBase):
    """API representation of a instance.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a instance.
    """
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
        url = pecan.request.public_url
        instance.links = [link.Link.make_link('self',
                                              url,
                                              'instances', instance.uuid),
                          link.Link.make_link('bookmark',
                                              url,
                                              'instances', instance.uuid,
                                              bookmark=True)
                          ]
        instance.unset_fields_except(fields)
        return instance


class InstanceCollection(base.APIBase):
    """API representation of a collection of instance."""

    instances = [Instance]
    """A list containing instance objects"""

    @staticmethod
    def convert_with_links(instances, fields=None):
        collection = InstanceCollection()
        collection.instances = [Instance.convert_with_links(inst, fields)
                                for inst in instances]
        return collection


class InstanceController(rest.RestController):
    """REST controller for Instance."""

    states = InstanceStatesController()

    _custom_actions = {
        'detail': ['GET']
    }

    def _get_instance_collection(self, detail=False, fields=None):
        instances = objects.Instance.list(pecan.request.context)
        instances_data = [instance.as_dict() for instance in instances]

        if detail:
            fields = None
            node_list = []
            try:
                node_list = get_node_list(
                    associated=False, limit=0, fields=_NODE_DETAIL_FIELDS)
                node_dict = {node.instance_uuid: node.to_dict()
                             for node in node_list}
            except Exception as e:
                LOG.warning(
                    _LW("Failed to retrieve node list from"
                        "ironic api: %(msg)s") % {"msg": str(e)})

            # Merge nimble instance info with ironic node power state
            for instance_data in instances_data:
                uuid = instance_data['uuid']
                if uuid in node_dict:
                    for field in _NODE_DETAIL_FIELDS:
                        instances_data[field] = node_dict[uuid][field]

        return InstanceCollection.convert_with_links(instances_data,
                                                     fields=fields)

    @expose.expose(InstanceCollection, types.listtype)
    def get_all(self, fields=None):
        """Retrieve a list of instance.

        :param fields: Optional, a list with a specified set of fields
                       of the resource to be returned.
        """
        if fields is None:
            fields = _DEFAULT_INSTANCE_RETURN_FIELDS
        return self._get_instance_collection(fields=fields)

    @expose.expose(Instance, types.uuid)
    def get_one(self, instance_uuid):
        """Retrieve information about the given instance.

        :param instance_uuid: UUID of a instance.
        """
        rpc_instance = objects.Instance.get(pecan.request.context,
                                            instance_uuid)
        node = get_node_by_instance(instance_uuid)
        instance_data = rpc_instance.as_dict()
        for field in _NODE_DETAIL_FIELDS:
            instance_data[field] = node.get(field)
        return Instance.convert_with_links(instance_data)

    @expose.expose(InstanceCollection)
    def detail(self):
        """Retrieve detail of a list of instances."""
        # /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "instances":
            raise exception.NotFound()
        return self._get_instance_collection(detail=True)

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
