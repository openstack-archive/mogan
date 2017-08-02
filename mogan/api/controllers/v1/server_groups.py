# Copyright 2017 Huawei Technologies Co.,LTD.
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
from mogan.api.controllers.v1.schemas import server_groups as sg_schema
from mogan.api.controllers.v1 import types
from mogan.api import expose
from mogan.api import validation
from mogan.common import policy
from mogan import objects


class ServerGroup(base.APIBase):
    """API representation of a server group.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a server group.
    """
    uuid = types.uuid
    """The UUID of the server group"""

    name = wtypes.text
    """The name of the server group"""

    project_id = types.uuid
    """The project UUID of the server group"""

    user_id = types.uuid
    """The user UUID of the server group"""

    policies = [wtypes.text]
    """The policies of the server group"""

    members = [types.uuid]
    """The server members of the server group"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link"""

    def __init__(self, **kwargs):
        self.fields = []
        for field in objects.ServerGroup.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @classmethod
    def convert_with_links(cls, db_server_groups):
        server_group = ServerGroup(**db_server_groups.as_dict())
        url = pecan.request.public_url
        server_group.links = [link.Link.make_link('self', url,
                                                  'server_groups',
                                                  server_group.uuid),
                              link.Link.make_link('bookmark', url,
                                                  'server_groups',
                                                  server_group.uuid,
                                                  bookmark=True)
                              ]

        return server_group


class ServerGroupCollection(base.APIBase):
    """API representation of a collection of server groups."""

    server_groups = [ServerGroup]
    """A list containing ServerGroup objects"""

    @staticmethod
    def convert_with_links(server_groups, url=None, **kwargs):
        collection = ServerGroupCollection()
        collection.server_groups = [ServerGroup.convert_with_links(
            server_group) for server_group in server_groups]
        return collection


class ServerGroupController(rest.RestController):
    """REST controller for server groups."""

    @policy.authorize_wsgi("mogan:server_group", "get_all")
    @expose.expose(ServerGroupCollection, types.boolean)
    def get_all(self, all_tenants=False):
        """Retrieve a list of server groups."""

        if pecan.request.context.is_admin and all_tenants:
            server_groups = objects.ServerGroupList.get_all(
                pecan.request.context)
        else:
            project_id = pecan.request.context.project_id
            server_groups = objects.ServerGroupList.get_by_project_id(
                pecan.request.context, project_id)
        return ServerGroupCollection.convert_with_links(server_groups)

    @policy.authorize_wsgi("mogan:server_group", "create")
    @expose.expose(ServerGroup, body=types.jsontype,
                   status_code=http_client.CREATED)
    def post(self, server_group):
        """Create an new server group.

        :param server_group: a server group within the request body.
        """
        validation.check_schema(server_group, sg_schema.create_server_group)
        new_server_group = objects.ServerGroup(pecan.request.context,
                                               **server_group)
        new_server_group.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('server_groups',
                                                 new_server_group.uuid)
        return ServerGroup.convert_with_links(new_server_group)

    @policy.authorize_wsgi("mogan:server_group", "get_one")
    @expose.expose(ServerGroup, types.uuid)
    def get_one(self, server_group_uuid):
        """Retrieve information about the given server group.

        :param server_group_uuid: UUID of a server group.
        """
        db_server_group = objects.ServerGroup.get(pecan.request.context,
                                                  server_group_uuid)
        return ServerGroup.convert_with_links(db_server_group)

    @policy.authorize_wsgi("mogan:server_group", "delete")
    @expose.expose(None, types.uuid, status_code=http_client.NO_CONTENT)
    def delete(self, server_group_uuid):
        """Delete a server group.

        :param server_group_uuid: UUID of a server group.
        """
        db_server_group = objects.ServerGroup.get(pecan.request.context,
                                                  server_group_uuid)
        db_server_group.destroy()
