# Copyright 2017 Fiberhome Integration Technologies Co.,LTD.
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
from wsme import types as wtypes

from mogan.api.controllers import base
from mogan.api import expose
from mogan.common import policy


class AdoptableNodes(base.APIBase):
    """API representation of a collection of nodes."""

    nodes = [wtypes.text]
    """A list containing compute node names"""


class ManageableServersController(rest.RestController):
    """REST controller for manage existing servers."""

    @policy.authorize_wsgi("mogan:manageable_servers", "get_all", False)
    @expose.expose(AdoptableNodes, None, status_code=http_client.OK)
    def get_all(self):
        """List adoptable nodes from driver."""
        nodes = pecan.request.engine_api.get_adoptable_nodes(
            pecan.request.context)

        collection = AdoptableNodes()
        collection.nodes = nodes['manageable_servers']
        return collection
