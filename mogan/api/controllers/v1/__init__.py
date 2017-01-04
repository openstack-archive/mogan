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
Version 1 of the Mogan API

Specification can be found at doc/source/webapi/v1.rst
"""

import pecan
from pecan import rest
from wsme import types as wtypes

from mogan.api.controllers import base
from mogan.api.controllers import link
from mogan.api.controllers.v1 import availability_zone
from mogan.api.controllers.v1 import instance_types
from mogan.api.controllers.v1 import instances
from mogan.api import expose


class V1(base.APIBase):
    """The representation of the version 1 of the API."""

    id = wtypes.text
    """The ID of the version, also acts as the release number"""

    instances = [link.Link]
    """Links to the instances resource"""

    types = [link.Link]
    """Links to the instance types resource"""

    availability_zones = [link.Link]
    """Links to the availability zones resource"""

    @staticmethod
    def convert():
        v1 = V1()
        v1.id = "v1"
        v1.instances = [link.Link.make_link('self', pecan.request.public_url,
                                            'instances', ''),
                        link.Link.make_link('bookmark',
                                            pecan.request.public_url,
                                            'instances', '',
                                            bookmark=True)
                        ]
        v1.types = [link.Link.make_link('self', pecan.request.public_url,
                                        'types', ''),
                    link.Link.make_link('bookmark',
                                        pecan.request.public_url,
                                        'types', '',
                                        bookmark=True)
                    ]
        v1.availability_zones = [link.Link.make_link('self',
                                                     pecan.request.public_url,
                                                     'availability_zones', ''),
                                 link.Link.make_link('bookmark',
                                                     pecan.request.public_url,
                                                     'availability_zones', '',
                                                     bookmark=True)
                                 ]
        return v1


class Controller(rest.RestController):
    """Version 1 API controller root."""

    types = instance_types.InstanceTypeController()
    instances = instances.InstanceController()
    availability_zones = availability_zone.AvailabilityZoneController()

    @expose.expose(V1)
    def get(self):
        return V1.convert()


__all__ = ('Controller',)
