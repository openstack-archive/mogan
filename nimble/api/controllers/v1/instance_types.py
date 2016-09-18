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


class InstanceType(base.APIBase):
    """API representation of an instance type.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a flavor.
    """
    id = wsme.wsattr(wtypes.IntegerType(minimum=1))
    """The ID of the instance type"""

    uuid = types.uuid
    """The UUID of the instance type"""

    name = wtypes.text
    """The name of the instance type"""

    description = wtypes.text
    """The description of the instance type"""

    is_public = types.boolean
    """Indicates whether the instance type is public."""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link"""

    def __init__(self, **kwargs):
        self.fields = []
        for field in objects.InstanceType.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @classmethod
    def convert_with_links(cls, rpc_instance_type):
        instance_type = InstanceType(**rpc_instance_type.as_dict())
        url = pecan.request.public_url
        instance_type.links = [link.Link.make_link('self', url,
                                                   'instance_type',
                                                   instance_type.uuid),
                               link.Link.make_link('bookmark', url,
                                                   'instance_type',
                                                   instance_type.uuid,
                                                   bookmark=True)
                               ]

        return instance_type


class InstanceTypeCollection(base.APIBase):
    """API representation of a collection of flavor."""

    instance_type = [InstanceType]
    """A list containing Instance Type objects"""

    @staticmethod
    def convert_with_links(flavors, url=None, **kwargs):
        collection = InstanceTypeCollection()
        collection.instance_types = [InstanceType.convert_with_links(fl)
                                     for fl in flavors]
        return collection


class InstanceTypeController(rest.RestController):
    """REST controller for Instance Type."""

    @expose.expose(InstanceTypeCollection)
    def get_all(self):
        """Retrieve a list of flavor."""

        instance_types = objects.InstanceType.list(pecan.request.context)
        return InstanceType.convert_with_links(instance_types)

    @expose.expose(InstanceType, types.uuid)
    def get_one(self, instance_type_uuid):
        """Retrieve information about the given flavor.

        :param instance_type_uuid: UUID of a instance type.
        """
        rpc_instance_type = objects.InstanceType.get(pecan.request.context,
                                                     instance_type_uuid)
        return InstanceType.convert_with_links(rpc_instance_type)

    @expose.expose(InstanceType, body=InstanceType,
                   status_code=http_client.CREATED)
    def post(self, instance_type):
        """Create an new instance type.

        :param instance_type: a instance type within the request body.
        """
        new_instance_type = objects.InstanceType(pecan.request.context,
                                                 **instance_type.as_dict())
        new_instance_type.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('instance_type',
                                                 new_instance_type.uuid)
        return InstanceType.convert_with_links(new_instance_type)

    @expose.expose(None, types.uuid, status_code=http_client.NO_CONTENT)
    def delete(self, instance_type_uuid):
        """Delete an instance type.

        :param instance_type_uuid: UUID of an instance type.
        """
        rpc_flavor = objects.InstanceType.get(pecan.request.context,
                                              instance_type_uuid)
        rpc_flavor.destroy()
