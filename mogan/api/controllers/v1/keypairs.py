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

import pecan
from pecan import rest
from six.moves import http_client
import wsme
from wsme import types as wtypes

from mogan.api.controllers import base
from mogan.api.controllers import link
from mogan.api.controllers.v1.schemas import keypairs as keypairs_schema
from mogan.api.controllers.v1 import types
from mogan.api import expose
from mogan.api import validation
from mogan import objects
from mogan.objects import keypair as keypair_obj


class KeyPair(base.APIBase):
    """API representation of a keypair.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    a keypair.
    """
    user_id = types.uuid
    """The user id of the keypair"""

    name = wtypes.text
    """The name of the keypair"""

    fingerprint = wtypes.text
    """The fingerprint of the keypair"""

    public_key = wtypes.text
    """The public_key of the keypair"""

    private_key = wtypes.text
    """The private_key of the keypair"""

    type = wtypes.Enum(str, 'ssh', 'x509')
    """The type of the keypair"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link"""

    def __init__(self, **kwargs):
        self.fields = []
        if 'private_key' in kwargs:
            self.fields.append('private_key')
            setattr(self, 'private_key',
                    kwargs.get('private_key', wtypes.Unset))
        for field in objects.KeyPair.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @classmethod
    def convert_with_links(cls, rpc_keypair):
        if hasattr(rpc_keypair, 'private_key') and rpc_keypair.private_key:
            keypair = KeyPair(private_key=rpc_keypair.private_key,
                              **rpc_keypair.as_dict())
        else:
            keypair = KeyPair(**rpc_keypair.as_dict())
        url = pecan.request.public_url
        keypair.links = [link.Link.make_link('self', url,
                                             'keypairs',
                                             keypair.name),
                         link.Link.make_link('bookmark', url,
                                             'keypairs',
                                             keypair.name,
                                             bookmark=True)
                         ]
        return keypair


class KeyPairCollection(base.APIBase):
    """API representation of a collection of keypairs."""

    keypairs = [KeyPair]
    """A list containing Instance Type objects"""

    @staticmethod
    def convert_with_links(keypairs, url=None, **kwargs):
        collection = KeyPairCollection()
        collection.keypairs = [KeyPair.convert_with_links(keypair)
                               for keypair in keypairs]
        return collection


class KeyPairController(rest.RestController):
    @expose.expose(KeyPair, body=types.jsontype,
                   status_code=http_client.CREATED)
    def post(self, body):
        """Generate a new keypair or import an existed keypair.

        :param body: the request body of keypair creation.
        """
        validation.check_schema(body, keypairs_schema.create_keypair)
        name = body['name']
        user_id = body.get('user_id') or pecan.request.context.user_id
        key_type = body.get('type', keypair_obj.KEYPAIR_TYPE_SSH)
        if 'public_key' in body:
            keypair = pecan.request.engine_api.import_key_pair(
                pecan.request.context, user_id, name,
                body['public_key'], key_type)
        else:
            keypair, private_key = pecan.request.engine_api.create_key_pair(
                pecan.request.context, user_id, name, key_type)
            keypair.private_key = private_key
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('keypairs',
                                                 keypair.name)
        return KeyPair.convert_with_links(keypair)

    @expose.expose(None, wtypes.text, wtypes.text,
                   status_code=http_client.NO_CONTENT)
    def delete(self, key_name, user_id=None):
        """Delete a keypair.

        :param key_name: the name of keypair to be deleted.
        """
        # TODO(liusheng): the input user_id should be only suport by admin
        # as default, need to add policy check here.
        user_id = user_id or pecan.request.context.user_id
        pecan.request.engine_api.delete_key_pair(
            pecan.request.context, user_id, key_name)

    @expose.expose(KeyPair, wtypes.text, wtypes.text)
    def get_one(self, key_name, user_id=None):
        """Query one keypair.

        :param key_name: the name of keypair to be queried.
        """
        # TODO(liusheng): the input user_id should be only suport by admin
        # as default, need to add policy check here.
        user_id = user_id or pecan.request.context.user_id
        keypair = pecan.request.engine_api.get_key_pair(
            pecan.request.context, user_id, key_name)
        return KeyPair.convert_with_links(keypair)

    @expose.expose(KeyPairCollection, wtypes.text)
    def get_all(self, user_id=None):
        """Query all keypairs of current user."""
        # TODO(liusheng): the input user_id should be only suport by admin
        # as default, need to add policy check here.
        user_id = user_id or pecan.request.context.user_id
        keypairs = pecan.request.engine_api.get_key_pairs(
            pecan.request.context, user_id)
        return KeyPairCollection.convert_with_links(keypairs)
