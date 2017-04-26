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

from mogan.scheduler import filters


class FlavorFilter(filters.BaseNodeFilter):
    """Filters Nodes by server type."""

    # Flavors do not change within a request
    run_filter_once_per_request = True

    def node_passes(self, node_state, filter_properties):
        spec = filter_properties.get('request_spec', {})
        flavor = spec.get('flavor', {})
        type_name = flavor.get('name')

        if type_name:
            return type_name == node_state.flavor
        return True
