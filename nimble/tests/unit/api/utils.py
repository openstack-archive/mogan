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
Utils for testing the API service.
"""

import datetime
import hashlib
import json

from nimble.tests.unit.db import utils


ADMIN_TOKEN = '4562138218392831'
MEMBER_TOKEN = '4562138218392832'

ADMIN_TOKEN_HASH = hashlib.sha256(ADMIN_TOKEN.encode()).hexdigest()
MEMBER_TOKEN_HASH = hashlib.sha256(MEMBER_TOKEN.encode()).hexdigest()

ADMIN_BODY = {
    'access': {
        'token': {'id': ADMIN_TOKEN,
                  'expires': '2100-09-11T00:00:00'},
        'user': {'id': 'user_id1',
                 'name': 'user_name1',
                 'tenantId': '123i2910',
                 'tenantName': 'mytenant',
                 'roles': [{'name': 'admin'}]},
    }
}

MEMBER_BODY = {
    'access': {
        'token': {'id': MEMBER_TOKEN,
                  'expires': '2100-09-11T00:00:00'},
        'user': {'id': 'user_id2',
                 'name': 'user-good',
                 'tenantId': 'project-good',
                 'tenantName': 'goodies',
                 'roles': [{'name': 'Member'}]},
    }
}


class FakeMemcache(object):
    """Fake cache that is used for keystone tokens lookup."""

    # NOTE(lucasagomes): keystonemiddleware >= 2.0.0 the token cache
    # keys are sha256 hashes of the token key. This was introduced in
    # https://review.openstack.org/#/c/186971
    _cache = {
        'tokens/%s' % ADMIN_TOKEN: ADMIN_BODY,
        'tokens/%s' % ADMIN_TOKEN_HASH: ADMIN_BODY,
        'tokens/%s' % MEMBER_TOKEN: MEMBER_BODY,
        'tokens/%s' % MEMBER_TOKEN_HASH: MEMBER_BODY,
    }

    def __init__(self):
        self.set_key = None
        self.set_value = None
        self.token_expiration = None

    def get(self, key):
        dt = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        return json.dumps((self._cache.get(key), dt.isoformat()))

    def set(self, key, value, time=0, min_compress_len=0):
        self.set_value = value
        self.set_key = key


def instance_post_data(**kw):
    instance = utils.get_test_instance(**kw)
    # These values are not part of the API object
    instance.pop('node_uuid')
    instance.pop('extra')
    instance.pop('launched_at')
    instance.pop('network_info')
    instance.pop('created_at')
    instance.pop('updated_at')
    instance.pop('project_id')
    instance.pop('user_id')
    instance.pop('status')
    instance.pop('uuid')
    instance.pop('id')

    instance['networks'] = [{"uuid": "17f3cd84-728e-47fe-b52a-233cb25c5800"}]

    return instance


def type_post_data(**kw):
    return {
        'name': kw.get('name', 'test'),
        'description': kw.get('description', 'test description'),
        'uuid': kw.get('uuid', '6ddba0d9-3abc-4535-9d05-2d6360c6c37b')
    }
