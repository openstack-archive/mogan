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
from nimble import objects


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


class InstanceActionController(rest.RestController):

    _custom_actions = {
        'power': ['PUT'],
    }


class InstanceController(rest.RestController):
    """REST controller for Instance."""

    action = InstanceActionController()

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
