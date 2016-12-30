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

from mogan.api.controllers import base
from mogan.api.controllers import link
from mogan.api.controllers.v1 import types
from mogan.api import expose
from mogan.common import exception
from mogan.common.i18n import _
from mogan import objects


class InstanceType(base.APIBase):
    """API representation of an instance type.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    an instance type.
    """
    uuid = types.uuid
    """The UUID of the instance type"""

    name = wtypes.text
    """The name of the instance type"""

    description = wtypes.text
    """The description of the instance type"""

    is_public = types.boolean
    """Indicates whether the instance type is public."""

    extra_specs = {wtypes.text: types.jsontype}
    """The extra specs of the instance type"""

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
                                                   'types',
                                                   instance_type.uuid),
                               link.Link.make_link('bookmark', url,
                                                   'types',
                                                   instance_type.uuid,
                                                   bookmark=True)
                               ]

        return instance_type


class InstanceTypeCollection(base.APIBase):
    """API representation of a collection of instance type."""

    types = [InstanceType]
    """A list containing Instance Type objects"""

    @staticmethod
    def convert_with_links(instance_types, url=None, **kwargs):
        collection = InstanceTypeCollection()
        collection.types = [InstanceType.convert_with_links(type1)
                            for type1 in instance_types]
        return collection


class TypeExtraSpecController(rest.RestController):
    """REST controller for Instance Type extra spec."""

    @expose.expose(wtypes.text, types.uuid)
    def get_all(self, instance_type_uuid):
        """Retrieve a list of extra specs of the queried instance type."""

        instance_type = objects.InstanceType.get(pecan.request.context,
                                                 instance_type_uuid)
        return dict(extra_specs=instance_type.extra_specs)

    @expose.expose(types.jsontype, types.uuid, body=types.jsontype,
                   status_code=http_client.ACCEPTED)
    def patch(self, instance_type_uuid, extra_spec):
        """Create/update extra specs for the given instance type."""

        instance_type = objects.InstanceType.get(pecan.request.context,
                                                 instance_type_uuid)
        instance_type.extra_specs = dict(instance_type.extra_specs,
                                         **extra_spec)
        instance_type.save()
        return dict(extra_specs=instance_type.extra_specs)

    @expose.expose(None, types.uuid, wtypes.text,
                   status_code=http_client.NO_CONTENT)
    def delete(self, instance_type_uuid, spec_name):
        """Delete an extra specs for the given instance type."""

        instance_type = objects.InstanceType.get(pecan.request.context,
                                                 instance_type_uuid)
        del instance_type.extra_specs[spec_name]
        instance_type.save()


class InstanceTypeController(rest.RestController):
    """REST controller for Instance Type."""

    extraspecs = TypeExtraSpecController()

    @expose.expose(InstanceTypeCollection)
    def get_all(self):
        """Retrieve a list of instance type."""

        instance_types = objects.InstanceType.list(pecan.request.context)
        return InstanceTypeCollection.convert_with_links(instance_types)

    @expose.expose(InstanceType, types.uuid)
    def get_one(self, instance_type_uuid):
        """Retrieve information about the given instance type.

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
        pecan.response.location = link.build_url('types',
                                                 new_instance_type.uuid)
        return InstanceType.convert_with_links(new_instance_type)

    @expose.expose(InstanceType, types.uuid, body=InstanceType)
    def put(self, instance_type_uuid, instance_type):
        """Update an instance type.

        :param instance_type_uuid: the uuid of instance_type to be updated.
        :param instance_type: a instance type within the request body.
        """
        try:
            inst_type_in_db = objects.InstanceType.get(
                pecan.request.context, instance_type_uuid)
        except exception.InstanceTypeNotFound:
            msg = (_("InstanceType %s could not be found") %
                   instance_type_uuid)
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)
        need_to_update = False
        for attr in ('name', 'description', 'is_public'):
            if getattr(instance_type, attr) != wtypes.Unset:
                need_to_update = True
                setattr(inst_type_in_db, attr, getattr(instance_type, attr))
        # don't need to call db_api if no update
        if need_to_update:
            inst_type_in_db.save()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('instance_type',
                                                 inst_type_in_db.uuid)
        return InstanceType.convert_with_links(inst_type_in_db)

    @expose.expose(None, types.uuid, status_code=http_client.NO_CONTENT)
    def delete(self, instance_type_uuid):
        """Delete an instance type.

        :param instance_type_uuid: UUID of an instance type.
        """
        rpc_instance_type = objects.InstanceType.get(pecan.request.context,
                                                     instance_type_uuid)
        rpc_instance_type.destroy()
