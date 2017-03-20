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
"""
Port Weigher.  Weigh nodes by their ports quantity.

The default is to preferably choose nodes with less ports. If you prefer
choosing more ports nodes, you can set the 'port_weight_multiplier' option
to a positive number and the weighing has the opposite effect of the default.
"""

from oslo_config import cfg

from mogan.scheduler import weights

CONF = cfg.CONF


class PortWeigher(weights.BaseNodeWeigher):
    minval = 0

    def weight_multiplier(self):
        """Override the weight multiplier."""
        return CONF.scheduler.port_weight_multiplier

    def _weigh_object(self, node_state, weight_properties):
        """Higher weights win. We want to choose less ports node to be the
        default.
        """
        return len(node_state.ports)
