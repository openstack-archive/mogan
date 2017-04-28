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

from mogan.api.controllers import base
from mogan.api.controllers import link
from mogan.api.controllers.v1.schemas import flavor_access
from mogan.api.controllers.v1 import types
from mogan.api import expose
from mogan.api import validation
from mogan.common import exception
from mogan.common.i18n import _
from mogan.common import policy
from mogan import objects


def _marshall_flavor_access(flavor):
    rval = []
    for project_id in flavor.projects:
        rval.append(project_id)

    return {'flavor_access': rval}


class Flavor(base.APIBase):
    """API representation of a flavor.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a flavor.
    """
    uuid = types.uuid
    """The UUID of the flavor"""

    name = wtypes.text
    """The name of the flavor"""

    description = wtypes.text
    """The description of the flavor"""

    is_public = types.boolean
    """Indicates whether the flavor is public."""

    extra_specs = {wtypes.text: types.jsontype}
    """The extra specs of the flavor"""

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
        flavor.links = [link.Link.make_link('self', url,
                                            'flavors',
                                            flavor.uuid),
                        link.Link.make_link('bookmark', url,
                                            'flavors',
                                            flavor.uuid,
                                            bookmark=True)
                        ]

        return flavor


class FlavorCollection(base.APIBase):
    """API representation of a collection of flavor."""

    flavors = [Flavor]
    """A list containing Flavor objects"""

    @staticmethod
    def convert_with_links(flavors, url=None, **kwargs):
        collection = FlavorCollection()
        collection.flavors = [Flavor.convert_with_links(flavor)
                              for flavor in flavors]
        return collection


class FlavorExtraSpecsController(rest.RestController):
    """REST controller for flavor extra specs."""

    @policy.authorize_wsgi("mogan:flavor_extra_specs", "get_all")
    @expose.expose(wtypes.text, types.uuid)
    def get_all(self, flavor_uuid):
        """Retrieve a list of extra specs of the queried flavor."""

        flavor = objects.Flavor.get(pecan.request.context, flavor_uuid)
        return dict(extra_specs=flavor.extra_specs)

    @policy.authorize_wsgi("mogan:flavor_extra_specs", "patch")
    @expose.expose(types.jsontype, types.uuid, body=types.jsontype,
                   status_code=http_client.ACCEPTED)
    def patch(self, flavor_uuid, extra_spec):
        """Create/update extra specs for the given flavor."""

        flavor = objects.Flavor.get(pecan.request.context, flavor_uuid)
        flavor.extra_specs = dict(flavor.extra_specs, **extra_spec)
        flavor.save()
        return dict(extra_specs=flavor.extra_specs)

    @policy.authorize_wsgi("mogan:flavor_extra_specs", "delete")
    @expose.expose(None, types.uuid, wtypes.text,
                   status_code=http_client.NO_CONTENT)
    def delete(self, flavor_uuid, spec_name):
        """Delete an extra specs for the given flavor."""

        flavor = objects.Flavor.get(pecan.request.context, flavor_uuid)
        del flavor.extra_specs[spec_name]
        flavor.save()


class FlavorAccessController(rest.RestController):
    """REST controller for flavor access."""

    @policy.authorize_wsgi("mogan:flavor_access", "get_all")
    @expose.expose(wtypes.text, types.uuid)
    def get_all(self, flavor_uuid):
        """Retrieve a list of extra specs of the queried flavor."""

        flavor = objects.Flavor.get(pecan.request.context,
                                    flavor_uuid)

        # public flavor to all projects
        if flavor.is_public:
            msg = _("Access list not available for public flavors.")
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.NOT_FOUND)

        # private flavor to listed projects only
        return _marshall_flavor_access(flavor)

    @policy.authorize_wsgi("mogan:flavor_access", "add_tenant_access")
    @expose.expose(None, types.uuid, body=types.jsontype,
                   status_code=http_client.NO_CONTENT)
    def post(self, flavor_uuid, tenant):
        """Add flavor access for the given tenant."""
        validation.check_schema(tenant, flavor_access.add_tenant_access)

        flavor = objects.Flavor.get(pecan.request.context,
                                    flavor_uuid)
        if flavor.is_public:
            msg = _("Can not add access to a public flavor.")
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.CONFLICT)

        try:
            flavor.projects.append(tenant['tenant_id'])
            flavor.save()
        except exception.FlavorNotFound as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.NOT_FOUND)
        except exception.FlavorAccessExists as err:
            raise wsme.exc.ClientSideError(
                err.message, status_code=http_client.CONFLICT)

    @policy.authorize_wsgi("mogan:flavor_access", "remove_tenant_access")
    @expose.expose(None, types.uuid, types.uuid,
                   status_code=http_client.NO_CONTENT)
    def delete(self, flavor_uuid, tenant_id):
        """Remove flavor access for the given tenant."""

        flavor = objects.Flavor.get(pecan.request.context,
                                    flavor_uuid)
        try:
            # TODO(zhenguo): this should be synchronized.
            if tenant_id in flavor.projects:
                flavor.projects.remove(tenant_id)
                flavor.save()
            else:
                raise exception.FlavorAccessNotFound(flavor_id=flavor.uuid,
                                                     project_id=tenant_id)
        except (exception.FlavorAccessNotFound,
                exception.FlavorNotFound) as e:
            raise wsme.exc.ClientSideError(
                e.message, status_code=http_client.NOT_FOUND)


class FlavorsController(rest.RestController):
    """REST controller for Flavors."""

    extraspecs = FlavorExtraSpecsController()
    access = FlavorAccessController()

    @policy.authorize_wsgi("mogan:flavor", "get_all")
    @expose.expose(FlavorCollection)
    def get_all(self):
        """Retrieve a list of flavor."""

        flavors = objects.Flavor.list(pecan.request.context)
        return FlavorCollection.convert_with_links(flavors)

    @policy.authorize_wsgi("mogan:flavor", "get_one")
    @expose.expose(Flavor, types.uuid)
    def get_one(self, flavor_uuid):
        """Retrieve information about the given flavor.

        :param flavor_uuid: UUID of a flavor.
        """
        rpc_flavor = objects.Flavor.get(pecan.request.context, flavor_uuid)
        return Flavor.convert_with_links(rpc_flavor)

    @policy.authorize_wsgi("mogan:flavor", "create")
    @expose.expose(Flavor, body=Flavor,
                   status_code=http_client.CREATED)
    def post(self, flavor):
        """Create an new flavor.

        :param flavor: a flavor within the request body.
        """
        new_flavor = objects.Flavor(pecan.request.context,
                                    **flavor.as_dict())
        new_flavor.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('flavors',
                                                 new_flavor.uuid)
        return Flavor.convert_with_links(new_flavor)

    @policy.authorize_wsgi("mogan:flavor", "update")
    @expose.expose(Flavor, types.uuid, body=Flavor)
    def put(self, flavor_uuid, flavor):
        """Update a flavor.

        :param flavor_uuid: the uuid of the flavor to be updated.
        :param flavor: a flavor within the request body.
        """
        try:
            flavor_in_db = objects.Flavor.get(
                pecan.request.context, flavor_uuid)
        except exception.FlavorTypeNotFound:
            msg = (_("Flavor %s could not be found") %
                   flavor_uuid)
            raise wsme.exc.ClientSideError(
                msg, status_code=http_client.BAD_REQUEST)
        need_to_update = False
        for attr in ('name', 'description', 'is_public'):
            if getattr(flavor, attr) != wtypes.Unset:
                need_to_update = True
                setattr(flavor_in_db, attr, getattr(flavor, attr))
        # don't need to call db_api if no update
        if need_to_update:
            flavor_in_db.save()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('flavor',
                                                 flavor_in_db.uuid)
        return Flavor.convert_with_links(flavor_in_db)

    @policy.authorize_wsgi("mogan:flavor", "delete")
    @expose.expose(None, types.uuid, status_code=http_client.NO_CONTENT)
    def delete(self, flavor_uuid):
        """Delete a flavor.

        :param flavor_uuid: UUID of a flavor.
        """
        rpc_flavor = objects.Flavor.get(pecan.request.context, flavor_uuid)
        rpc_flavor.destroy()
