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
Scheduler node filters
"""

from mogan.engine.scheduler import base_filter


class BaseNodeFilter(base_filter.BaseFilter):
    """Base class for node filters."""
    def _filter_one(self, obj, filter_properties):
        """Return True if the object passes the filter, otherwise False."""
        return self.node_passes(obj, filter_properties)

    def node_passes(self, node_state, filter_properties):
        """Return True if the NodeState passes the filter, otherwise False.

        Override this in a subclass.
        """
        raise NotImplementedError()


class NodeFilterHandler(base_filter.BaseFilterHandler):
    def __init__(self, namespace):
        super(NodeFilterHandler, self).__init__(BaseNodeFilter, namespace)
