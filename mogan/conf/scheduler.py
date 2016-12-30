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

from oslo_config import cfg

from mogan.common.i18n import _

opts = [
    cfg.StrOpt('scheduler_driver',
               default='mogan.engine.scheduler.filter_scheduler.'
                       'FilterScheduler',
               help=_('Default scheduler driver to use')),
    cfg.StrOpt('scheduler_node_manager',
               default='mogan.engine.scheduler.node_manager.NodeManager',
               help=_('The scheduler node manager class to use')),
    cfg.IntOpt('scheduler_max_attempts',
               default=3,
               help=_('Maximum number of attempts to schedule a node')),
    cfg.StrOpt('scheduler_json_config_location',
               default='',
               help=_('Absolute path to scheduler configuration JSON file.')),
    cfg.ListOpt('scheduler_default_filters',
                default=[
                    'AvailabilityZoneFilter',
                    'InstanceTypeFilter',
                    'CapabilitiesFilter'
                ],
                help=_('Which filter class names to use for filtering nodes '
                       'when not specified in the request.')),
    cfg.ListOpt('scheduler_default_weighers',
                default=[],
                help=_('Which weigher class names to use for weighing '
                       'nodes.')),
    cfg.StrOpt('scheduler_weight_handler',
               default='mogan.engine.scheduler.weights.'
                       'OrderedNodeWeightHandler',
               help=_('Which handler to use for selecting the node after '
                      'weighing')),
]


def register_opts(conf):
    conf.register_opts(opts, group='scheduler')
