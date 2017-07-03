# Copyright 2017 Fiberhome Integration Technologies Co.,LTD.
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
from mogan.api.controllers.v1 import types
from mogan.api import expose
from mogan.common import policy


class ManageableServer(base.APIBase):
    """API representation of manageable server."""

    uuid = types.uuid
    """The UUID of the manageable server"""

    name = wtypes.text
    """The name of the manageable server"""

    resource_class = wtypes.text
    """The resource_class of the manageable server"""

    power_state = wtypes.text
    """The power_state of the manageable server"""

    provision_state = wtypes.text
    """The provision_state of the manageable server"""

    ports = types.jsontype
    """The ports of the manageable server"""

    portgroups = types.jsontype
    """The portgroups of the manageable server"""

    image_source = types.uuid
    """The UUID of the image id which manageable server use"""

    def __init__(self, **kwargs):
        super(ManageableServer, self).__init__(**kwargs)
        self.fields = []
        for field in kwargs.keys():
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))


class ManageableServerCollection(base.APIBase):
    """API representation of a collection of manageable server."""

    manageableservers = [ManageableServer]
    """A list containing manageable server objects"""

    @staticmethod
    def convert_with_list_of_dicts(manageableservers):
        collection = ManageableServerCollection()
        collection.manageableservers = [ManageableServer(**mserver)
                                        for mserver in manageableservers]
        return collection


class ManageableServersController(rest.RestController):
    """REST controller for manage existing servers."""

    @policy.authorize_wsgi("mogan:manageable_servers", "get_all", False)
    @expose.expose(ManageableServerCollection)
    def get_all(self):
        """List manageable servers from driver."""
        nodes = pecan.request.engine_api.get_manageable_servers(
            pecan.request.context)
        return ManageableServerCollection.convert_with_list_of_dicts(nodes)
