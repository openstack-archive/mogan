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
from mogan.api.controllers.v1 import types
from mogan.api import expose
from mogan.common import exception
from mogan.common.i18n import _
from mogan import objects


class KeyPair(base.APIBase):
    """API representation of an keypair.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of
    an instance type.
    """
    user_id = types.uuid
    """The user id of the keypair"""

    name = wtypes.text
    """The name of the keypair"""

    fingerprint = wtypes.text
    """The fingerprint of the keypair"""

    public_key = wtypes.text
    """The public_key of the keypair"""

    type = wtypes.Enum(str, 'ssh', 'x509')
    """The type of the keypair"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link"""

    def __init__(self, **kwargs):
        self.fields = []
        for field in objects.KeyPair.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @classmethod
    def convert_with_links(cls, rpc_keypair):
        keypair = KeyPair(**rpc_keypair.as_dict())
        url = pecan.request.public_url
        keypair.links = [link.Link.make_link('self', url,
                                             'types',
                                             keypair.id),
                         link.Link.make_link('bookmark', url,
                                             'types',
                                             keypair.id,
                                             bookmark=True)
                         ]

        return keypair
