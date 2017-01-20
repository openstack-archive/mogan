# Copyright (c) 2011 OpenStack Foundation
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
Manage nodes.
"""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from mogan.common import exception
from mogan.engine.scheduler import filters


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class NodeState(object):
    """Mutable and immutable information tracked for a Ironic node."""

    def __init__(self, node):
        self.node = node.uuid
        self.capabilities = node.properties.get('capabilities')
        self.availability_zone = node.properties.get('availability_zone') \
            or CONF.engine.default_schedule_zone
        self.instance_type = node.properties.get('instance_type')
        self.ports = node.ports


class NodeManager(object):
    """Base NodeManager class."""

    node_state_cls = NodeState

    def __init__(self):
        self.filter_handler = filters.NodeFilterHandler('mogan.engine.'
                                                        'scheduler.filters')
        self.filter_classes = self.filter_handler.get_all_classes()
        self.weight_handler = importutils.import_object(
            CONF.scheduler.scheduler_weight_handler,
            'mogan.engine.scheduler.weights')
        self.weight_classes = self.weight_handler.get_all_classes()

    def _choose_node_filters(self, filter_cls_names):
        """Return a list of available filter names.

        This function checks input filter names against a predefined set
        of acceptable filterss (all loaded filters).  If input is None,
        it uses CONF.scheduler_default_filters instead.
        """
        if filter_cls_names is None:
            filter_cls_names = CONF.scheduler.scheduler_default_filters
        if not isinstance(filter_cls_names, (list, tuple)):
            filter_cls_names = [filter_cls_names]
        good_filters = []
        bad_filters = []
        for filter_name in filter_cls_names:
            found_class = False
            for cls in self.filter_classes:
                if cls.__name__ == filter_name:
                    found_class = True
                    good_filters.append(cls)
                    break
            if not found_class:
                bad_filters.append(filter_name)
        if bad_filters:
            raise exception.SchedulerNodeFilterNotFound(
                filter_name=", ".join(bad_filters))
        return good_filters

    def _choose_node_weighers(self, weight_cls_names):
        """Return a list of available weigher names.

        This function checks input weigher names against a predefined set
        of acceptable weighers (all loaded weighers).  If input is None,
        it uses CONF.scheduler_default_weighers instead.
        """
        if weight_cls_names is None:
            weight_cls_names = CONF.scheduler.scheduler_default_weighers
        if not isinstance(weight_cls_names, (list, tuple)):
            weight_cls_names = [weight_cls_names]

        good_weighers = []
        bad_weighers = []
        for weigher_name in weight_cls_names:
            found_class = False
            for cls in self.weight_classes:
                if cls.__name__ == weigher_name:
                    good_weighers.append(cls)
                    found_class = True
                    break
            if not found_class:
                bad_weighers.append(weigher_name)
        if bad_weighers:
            raise exception.SchedulerNodeWeigherNotFound(
                weigher_name=", ".join(bad_weighers))
        return good_weighers

    def get_filtered_nodes(self, nodes, filter_properties,
                           filter_class_names=None):
        """Filter nodes and return only ones passing all filters."""
        filter_classes = self._choose_node_filters(filter_class_names)
        return self.filter_handler.get_filtered_objects(filter_classes,
                                                        nodes,
                                                        filter_properties)

    def get_weighed_nodes(self, nodes, weight_properties,
                          weigher_class_names=None):
        """Weigh the nodes."""
        weigher_classes = self._choose_node_weighers(weigher_class_names)
        return self.weight_handler.get_weighed_objects(weigher_classes,
                                                       nodes,
                                                       weight_properties)

    def get_all_node_states(self, node_cache):
        """Returns a list of all the nodes the NodeManager knows about."""

        node_states = []
        for node_uuid, node in node_cache.items():
            node_state = self.node_state_cls(node)
            node_states.append(node_state)

        return node_states
