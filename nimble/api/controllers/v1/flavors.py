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
from six.moves import http_client
import wsme
from wsme import types as wtypes

from nimble.api.controllers import base
from nimble.api.controllers import link
from nimble.api.controllers.v1 import types
from nimble.api import expose
from nimble import objects


class Flavor(base.APIBase):
    """API representation of a flavor.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a flavor.
    """
    id = wsme.wsattr(wtypes.IntegerType(minimum=1))
    """The ID of the flavor"""

    uuid = types.uuid
    """The UUID of the flavor"""

    name = wtypes.text
    """The name of the flavor"""

    description = wtypes.text
    """The description of the flavor"""

    is_public = types.boolean
    """Indicates whether the flavor is public."""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link"""

    def __init__(self, **kwargs):
        self.fields = []
        for field in objects.Flavor.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @classmethod
    def convert_with_links(cls, rpc_flavor):
        flavor = Flavor(**rpc_flavor.as_dict())
        url = pecan.request.public_url
        flavor.links = [link.Link.make_link('self',
                                            url,
                                            'flavor', flavor.uuid),
                        link.Link.make_link('bookmark',
                                            url,
                                            'flavor', flavor.uuid,
                                            bookmark=True)
                        ]

        return flavor


class FlavorCollection(base.APIBase):
    """API representation of a collection of flavor."""

    flavor = [Flavor]
    """A list containing flavor objects"""

    @staticmethod
    def convert_with_links(flavor, url=None, **kwargs):
        collection = FlavorCollection()
        collection.flavor = [Flavor.convert_with_links(fl)
                             for fl in flavor]
        return collection


class FlavorController(rest.RestController):
    """REST controller for Chassis."""

    @expose.expose(FlavorCollection)
    def get_all(self):
        """Retrieve a list of flavor."""

        flavor = objects.Flavor.list(pecan.request.context)
        return FlavorCollection.convert_with_links(flavor)

    @expose.expose(Flavor, types.uuid)
    def get_one(self, flavor_uuid):
        """Retrieve information about the given flavor.

        :param flavor_uuid: UUID of a flavor.
        """
        rpc_flavor = objects.Flavor.get(pecan.request.context,
                                        flavor_uuid)
        return Flavor.convert_with_links(rpc_flavor)

    @expose.expose(Flavor, body=Flavor, status_code=http_client.CREATED)
    def post(self, flavor):
        """Create a new flavor.

        :param flavor: a flavor within the request body.
        """
        new_flavor = objects.Flavor(pecan.request.context,
                                    **flavor.as_dict())
        new_flavor.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('flavor', new_flavor.uuid)
        return Flavor.convert_with_links(new_flavor)

    @expose.expose(None, types.uuid, status_code=http_client.NO_CONTENT)
    def delete(self, flavor_uuid):
        """Delete a flavor.

        :param flavor_uuid: UUID of a flavor.
        """
        rpc_flavor = objects.Flavor.get(pecan.request.context, flavor_uuid)
        rpc_flavor.destroy()
