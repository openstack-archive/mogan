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
from wsme import types as wtypes

from mogan.api.controllers import base
from mogan.api.controllers.v1 import types
from mogan.api import expose
from mogan.common import policy
from mogan import objects


class Node(base.APIBase):
    """API representation of a node.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a node.
    """
    node_uuid = types.uuid
    """The UUID of the node"""

    availability_zone = wtypes.text
    """The availability zone of the node"""

    node_type = wtypes.text
    """The type of the node"""

    hypervisor_type = wtypes.text
    """The hypervisor type of the node"""

    extra_specs = {wtypes.text: types.jsontype}
    """The meta data of the node"""

    def __init__(self, **kwargs):
        super(Node, self).__init__(**kwargs)
        self.fields = []
        for field in objects.ComputeNode.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))


class NodeCollection(base.APIBase):
    """API representation of a collection of nodes."""

    nodes = [Node]
    """A list containing compute node objects"""


class NodeController(rest.RestController):
    """REST controller for Node."""

    @policy.authorize_wsgi("mogan:node", "get_all",
                           need_target=False)
    @expose.expose(NodeCollection)
    def get_all(self):
        """Retrieve a list of nodes."""

        nodes = objects.ComputeNodeList.get_all_available(
            pecan.request.context)
        nodes_data = [Node(**node.as_dict()) for node in nodes]

        return NodeCollection(nodes=nodes_data)
