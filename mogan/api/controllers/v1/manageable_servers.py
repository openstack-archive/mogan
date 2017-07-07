# Copyright 2017 Fiberhome Technologies Co.,LTD.
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


from oslo_log import log
import pecan
from six.moves import http_client

from mogan.api.controllers import link
from mogan.api.controllers.v1.schemas import servers as server_schemas
from mogan.api.controllers.v1.servers import Server
from mogan.api.controllers.v1.servers import ServerControllerBase
from mogan.api.controllers.v1 import types
from mogan.api import expose
from mogan.api import validation
from mogan.common import exception
from mogan.common import policy
from mogan import objects


LOG = log.getLogger(__name__)


class ManageableServersController(ServerControllerBase):
    """REST controller for Manageable Server."""

    @policy.authorize_wsgi("mogan:manageable_servers", "create", False)
    @expose.expose(Server, body=types.jsontype,
                   status_code=http_client.CREATED)
    def post(self, server):
        """Manage an existing bare metal node.

        :param server: A server within the request body
        :return: The server information.
        """
        validation.check_schema(server, server_schemas.manage_server)

        node_uuid = server.pop('node_uuid', None)
        flavor_uuid = server.pop('flavor_uuid', None)
        requested_networks = server.pop('networks', None)
        flavor = objects.Flavor.get(pecan.request.context, flavor_uuid)
        if flavor.disabled:
            raise exception.FlavorDisabled(flavor_id=flavor.uuid)

        servers = pecan.request.engine_api.manage(
            pecan.request.context, flavor, node_uuid,
            server.get('name'),
            server.get('description'),
            requested_networks,
            availability_zone=server.get('availability_zone'))

        # Set the HTTP Location Header for the first server.
        pecan.response.location = link.build_url('server', servers[0].uuid)
        return Server.convert_with_links(servers[0])
