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
from nimble.engine.baremetal import ironic_states as ir_states
from nimble import objects


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
                     last_error=None,
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
    id = wsme.wsattr(wtypes.IntegerType(minimum=1))
    """The ID of the instance"""

    uuid = types.uuid
    """The UUID of the instance"""

    name = wtypes.text
    """The name of the instance"""

    description = wtypes.text
    """The description of the instance"""

    status = wtypes.text
    """The status of the instance"""

    power_state = wtypes.text
    """The power state of the instance"""

    task_state = wtypes.text
    """The task state of the instance"""

    availability_zone = wtypes.text
    """The availability zone of the instance"""

    instance_type_id = wsme.wsattr(wtypes.IntegerType(minimum=1))
    """The instance type ID of the instance"""

    image_uuid = types.uuid
    """The image UUID of the instance"""

    network_uuid = types.uuid
    """The network UUID of the instance"""

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
    def convert_with_links(cls, rpc_instance):
        instance = Instance(**rpc_instance.as_dict())
        url = pecan.request.public_url
        instance.links = [link.Link.make_link('self',
                                              url,
                                              'instance', instance.uuid),
                          link.Link.make_link('bookmark',
                                              url,
                                              'instance', instance.uuid,
                                              bookmark=True)
                          ]

        return instance


class InstanceCollection(base.APIBase):
    """API representation of a collection of instance."""

    instances = [Instance]
    """A list containing instance objects"""

    @staticmethod
    def convert_with_links(instances, url=None, **kwargs):
        collection = InstanceCollection()
        collection.instances = [Instance.convert_with_links(inst)
                                for inst in instances]
        return collection


class InstanceController(rest.RestController):
    """REST controller for Instance."""

    states = InstanceStatesController()

    @expose.expose(InstanceCollection)
    def get_all(self):
        """Retrieve a list of instance."""

        instances = objects.Instance.list(pecan.request.context)
        return InstanceCollection.convert_with_links(instances)

    @expose.expose(Instance, types.uuid)
    def get_one(self, instance_uuid):
        """Retrieve information about the given instance.

        :param instance_uuid: UUID of a instance.
        """
        rpc_instance = objects.Instance.get(pecan.request.context,
                                            instance_uuid)
        return Instance.convert_with_links(rpc_instance)

    @expose.expose(Instance, body=Instance, status_code=http_client.CREATED)
    def post(self, instance):
        """Create a new instance.

        :param instance: a instance within the request body.
        """
        instance_obj = objects.Instance(pecan.request.context,
                                        **instance.as_dict())
        instance_obj.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('instance', instance_obj.uuid)

        pecan.request.rpcapi.create_instance(pecan.request.context,
                                             instance_obj)
        instance_obj.status = 'building'
        instance_obj.save()
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
