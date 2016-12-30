# Copyright 2016 Huawei Technologies Co.,LTD.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import pecan
from pecan import rest
from wsme import types as wtypes

from mogan.api.controllers import base
from mogan.api.controllers import v1
from mogan.api import expose

ID_VERSION1 = 'v1'


class Root(base.APIBase):

    name = wtypes.text
    """The name of the API"""

    description = wtypes.text
    """Some information about this API"""

    @staticmethod
    def convert():
        root = Root()
        root.name = "OpenStack Mogan API"
        root.description = ("Mogan is an OpenStack project which aims to "
                            "facilitate baremetal machines management.")
        return root


class RootController(rest.RestController):

    _versions = [ID_VERSION1]
    """All supported API versions"""

    _default_version = ID_VERSION1
    """The default API version"""

    v1 = v1.Controller()

    @expose.expose(Root)
    def get(self):
        return Root.convert()

    @pecan.expose()
    def _route(self, args):
        """Overrides the default routing behavior.

        It redirects the request to the default version of the mogan API
        if the version number is not specified in the url.
        """

        if args[0] and args[0] not in self._versions:
            args = [self._default_version] + args
        return super(RootController, self)._route(args)
