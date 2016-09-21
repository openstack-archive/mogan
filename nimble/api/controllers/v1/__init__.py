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

"""
Version 1 of the Nimble API

Specification can be found at doc/source/webapi/v1.rst
"""

from pecan import rest

from nimble.api.controllers.v1 import instance_types
from nimble.api.controllers.v1 import instances


class Controller(rest.RestController):
    """Version 1 API controller root."""

    types = instance_types.InstanceTypeController()
    instances = instances.InstanceController()


__all__ = ('Controller',)
