# Copyright (c) 2011 OpenStack Foundation.
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

"""
Scheduler node weights
"""

from mogan.scheduler import base_weight


class WeighedNode(base_weight.WeighedObject):
    def to_dict(self):
        return {
            'weight': self.weight,
            'node': self.obj.node_uuid,
        }

    def __repr__(self):
        return ("WeighedNode [node: %s, weight: %s]" %
                (self.obj.node_uuid, self.weight))


class BaseNodeWeigher(base_weight.BaseWeigher):
    """Base class for node weights."""
    pass


class OrderedNodeWeightHandler(base_weight.BaseWeightHandler):
    object_class = WeighedNode

    def __init__(self, namespace):
        super(OrderedNodeWeightHandler, self).__init__(BaseNodeWeigher,
                                                       namespace)
