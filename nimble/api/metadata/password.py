# Copyright 2012 Nebula, Inc.
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

from six.moves import range
from webob import exc

from nimble import context
from nimble.i18n import _
from nimble import objects
from nimble import utils


CHUNKS = 4
CHUNK_LENGTH = 255
MAX_SIZE = CHUNKS * CHUNK_LENGTH


def extract_password(instance):
    result = ''
    sys_meta = utils.instance_sys_meta(instance)
    for key in sorted(sys_meta.keys()):
        if key.startswith('password_'):
            result += sys_meta[key]
    return result or None


def convert_password(context, password):
    """Stores password as system_metadata items.

    Password is stored with the keys 'password_0' -> 'password_3'.
    """
    password = password or ''
    meta = {}
    for i in range(CHUNKS):
        meta['password_%d' % i] = password[:CHUNK_LENGTH]
        password = password[CHUNK_LENGTH:]
    return meta


def handle_password(req, meta_data):
    ctxt = context.get_admin_context()
    if req.method == 'GET':
        return meta_data.password
    elif req.method == 'POST':
        # NOTE(vish): The conflict will only happen once the metadata cache
        #             updates, but it isn't a huge issue if it can be set for
        #             a short window.
        if meta_data.password:
            raise exc.HTTPConflict()
        if (req.content_length > MAX_SIZE or len(req.body) > MAX_SIZE):
            msg = _("Request is too large.")
            raise exc.HTTPBadRequest(explanation=msg)

        instance = objects.Instance.get_by_uuid(ctxt, meta_data.uuid)
        instance.system_metadata.update(convert_password(ctxt, req.body))
        instance.save()
    else:
        raise exc.HTTPBadRequest()
