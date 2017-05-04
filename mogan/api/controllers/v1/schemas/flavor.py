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


from mogan.api.validation import parameter_types


create_flavor = {
    "type": "object",
    "properties": {
        'name': parameter_types.name,
        'description': parameter_types.description,
        'is_public': parameter_types.boolean,
        'cpus': parameter_types.flavor_cpus,
        'memory': parameter_types.flavor_memory,
    },
    'required': ['name', 'description'],
    'additionalProperties': False,
}
