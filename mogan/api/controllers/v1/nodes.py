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

from pecan import rest

from mogan.api.controllers import base
from mogan.api.controllers.v1 import types
from mogan.api import expose
from mogan.common import policy


class NodeCollection(base.APIBase):
    """API representation of a collection of nodes."""

    nodes = [types.jsontype]
    """A list containing compute node objects"""


class NodeController(rest.RestController):
    """REST controller for Node."""

    @policy.authorize_wsgi("mogan:node", "get_all",
                           need_target=False)
    @expose.expose(Nodes)
    def get_all(self):
        """Retrieve a list of nodes."""

        nodes = objects.ComputeNodeList.get_all_available(context)
        nodes_data = [node.as_dict() for node in nodes]

        return NodeCollection(nodes=nodes_data)
