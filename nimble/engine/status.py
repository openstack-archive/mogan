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

"""Possible status for instances.

Compute instance status represent the state of an instance as it pertains to
a user or administrator.
"""

# Instance is running
ACTIVE = 'active'

# Instance only exists in DB
BUILDING = 'building'

DELETING = 'deleting'

DELETED = 'deleted'

ERROR = 'error'
