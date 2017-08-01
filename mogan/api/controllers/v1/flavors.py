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
from mogan.api.controllers.v1.schemas import flavor as flavor_schema
from mogan.api.controllers.v1.schemas import flavor_access
from mogan.api.controllers.v1 import types
from mogan.api.controllers.v1 import utils as api_utils
from mogan.api import expose
from mogan.api import validation
from mogan.common import exception
from mogan.common.i18n import _
from mogan.common import policy
from mogan import objects


_DEFAULT_FLAVOR_RETURN_FIELDS = ['uuid', 'name', 'description', 'is_public']


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

    disabled = types.boolean
    """Indicates whether the flavor is disabled."""

    resources = {wtypes.text: types.jsontype}
    """The resources of the flavor"""

    resource_traits = {wtypes.text: types.jsontype}
    """The resource traits of the flavor"""

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
    def convert_with_links(cls, db_flavor, fields=None):
        flavor = Flavor(**db_flavor.as_dict())
        url = pecan.request.public_url
        if fields is not None:
            flavor.unset_fields_except(fields)
        flavor.links = [link.Link.make_link('self', url,
                                            'flavors',
                                            flavor.uuid),
                        link.Link.make_link('bookmark', url,
                                            'flavors',
                                            flavor.uuid,
                                            bookmark=True)
                        ]
        return flavor


class FlavorPatchType(types.JsonPatchType):

    _api_base = Flavor


class FlavorCollection(base.APIBase):
    """API representation of a collection of flavor."""

    flavors = [Flavor]
    """A list containing Flavor objects"""

    @staticmethod
    def convert_with_links(flavors, fields=None):
        collection = FlavorCollection()
        collection.flavors = [Flavor.convert_with_links(flavor, fields=fields)
                              for flavor in flavors]
        return collection


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

        flavor.projects.append(tenant['tenant_id'])
        flavor.save()

    @policy.authorize_wsgi("mogan:flavor_access", "remove_tenant_access")
    @expose.expose(None, types.uuid, types.uuid,
                   status_code=http_client.NO_CONTENT)
    def delete(self, flavor_uuid, tenant_id):
        """Remove flavor access for the given tenant."""

        flavor = objects.Flavor.get(pecan.request.context,
                                    flavor_uuid)
        # TODO(zhenguo): this should be synchronized.
        if tenant_id in flavor.projects:
            flavor.projects.remove(tenant_id)
            flavor.save()
        else:
            raise exception.FlavorAccessNotFound(flavor_id=flavor.uuid,
                                                 project_id=tenant_id)


class FlavorsController(rest.RestController):
    """REST controller for Flavors."""

    access = FlavorAccessController()

    @policy.authorize_wsgi("mogan:flavor", "get_all")
    @expose.expose(FlavorCollection)
    def get_all(self):
        """Retrieve a list of flavor."""
        flavors = objects.Flavor.list(pecan.request.context)
        if not pecan.request.context.is_admin:
            return FlavorCollection.convert_with_links(
                flavors, fields=_DEFAULT_FLAVOR_RETURN_FIELDS)
        else:
            return FlavorCollection.convert_with_links(flavors)

    @policy.authorize_wsgi("mogan:flavor", "get_one")
    @expose.expose(Flavor, types.uuid)
    def get_one(self, flavor_uuid):
        """Retrieve information about the given flavor.

        :param flavor_uuid: UUID of a flavor.
        """
        db_flavor = objects.Flavor.get(pecan.request.context, flavor_uuid)
        if not pecan.request.context.is_admin:
            return Flavor.convert_with_links(
                db_flavor, fields=_DEFAULT_FLAVOR_RETURN_FIELDS)
        else:
            return Flavor.convert_with_links(db_flavor)

    @policy.authorize_wsgi("mogan:flavor", "create")
    @expose.expose(Flavor, body=types.jsontype,
                   status_code=http_client.CREATED)
    def post(self, flavor):
        """Create an new flavor.

        :param flavor: a flavor within the request body.
        """
        validation.check_schema(flavor, flavor_schema.create_flavor)
        new_flavor = objects.Flavor(pecan.request.context, **flavor)
        new_flavor.create()
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('flavors',
                                                 new_flavor.uuid)
        return Flavor.convert_with_links(new_flavor)

    @policy.authorize_wsgi("mogan:flavor", "update")
    @wsme.validate(types.uuid, [FlavorPatchType])
    @expose.expose(Flavor, types.uuid, body=[FlavorPatchType])
    def patch(self, flavor_uuid, patch):
        """Update a flavor.

        :param flavor_uuid: the uuid of the flavor to be updated.
        :param flavor: a json PATCH document to apply to this flavor.
        """

        db_flavor = objects.Flavor.get(pecan.request.context, flavor_uuid)

        try:
            flavor = Flavor(
                **api_utils.apply_jsonpatch(db_flavor.as_dict(), patch))

        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Flavor.fields:
            try:
                patch_val = getattr(flavor, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if db_flavor[field] != patch_val:
                db_flavor[field] = patch_val

        db_flavor.save()

        return Flavor.convert_with_links(db_flavor)

    @policy.authorize_wsgi("mogan:flavor", "delete")
    @expose.expose(None, types.uuid, status_code=http_client.NO_CONTENT)
    def delete(self, flavor_uuid):
        """Delete a flavor.

        :param flavor_uuid: UUID of a flavor.
        """
        db_flavor = objects.Flavor.get(pecan.request.context, flavor_uuid)
        db_flavor.destroy()
