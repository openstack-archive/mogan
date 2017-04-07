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

import pecan
from pecan import rest
from wsme import types as wtypes

from mogan.api.controllers import base
from mogan.api import expose
from mogan.common import policy


class AvailabilityZones(base.APIBase):
    """API representation of a collection of availability zone."""

    availability_zones = [wtypes.text]
    """A list containing availability zone names"""


class AvailabilityZoneController(rest.RestController):
    """REST controller for Availability Zone."""

    @policy.authorize_wsgi("mogan:availability_zone", "get_all",
                           need_target=False)
    @expose.expose(AvailabilityZones)
    def get_all(self):
        """Retrieve a list of availability zone."""

        azs = pecan.request.engine_api.list_availability_zones(
            pecan.request.context)

        collection = AvailabilityZones()
        collection.availability_zones = azs['availability_zones']
        return collection
