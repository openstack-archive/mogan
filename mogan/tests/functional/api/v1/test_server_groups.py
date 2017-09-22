# Copyright 2017 Huawei Technologies Co., Ltd.
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

import random
import six

from mogan.tests.functional.api import v1 as v1_test


class TestServerGroup(v1_test.APITestV1):
    def setUp(self):
        super(TestServerGroup, self).setUp()
        self.headers = self.gen_headers(self.context, roles="admin")

    def _prepare_server_groups(self):
        server_groups = []
        for i in six.moves.xrange(4):
            body = {"name": "test_sg" + str(i),
                    "policies": [random.choice(['anti-affinity', 'affinity'])]}
            resp = self.post_json('/server_groups', body,
                                  headers=self.headers,
                                  status=201)
            server_groups.append(resp.json)
        return server_groups

    def test_server_group_post(self):
        body = {"name": "test_server_group",
                "policies": ['anti-affinity']}
        resp = self.post_json(
            '/server_groups', body, headers=self.headers, status=201)
        resp = resp.json
        self.assertEqual('test_server_group', resp['name'])
        self.assertEqual(['anti-affinity'], resp['policies'])
        self.assertEqual([], resp['members'])
        self.assertIn('uuid', resp)
        self.assertIn('links', resp)
        self.assertIn('project_id', resp)
        self.assertIn('user_id', resp)
        self.assertIn('updated_at', resp)
        self.assertIn('created_at', resp)

    def test_server_group_get_all(self):
        self._prepare_server_groups()
        resp = self.get_json('/server_groups', headers=self.headers)
        self.assertEqual(4, len(resp['server_groups']))

    def test_server_group_get_one(self):
        sgs = self._prepare_server_groups()
        resp = self.get_json('/server_groups/' + sgs[0]['uuid'],
                             headers=self.headers)
        self.assertEqual('test_sg0', resp['name'])
        self.assertEqual([], resp['members'])
        self.assertIn('policies', resp)
        self.assertIn('uuid', resp)
        self.assertIn('links', resp)
        self.assertIn('project_id', resp)
        self.assertIn('user_id', resp)
        self.assertIn('updated_at', resp)
        self.assertIn('created_at', resp)

    def test_server_group_delete(self):
        sgs = self._prepare_server_groups()
        resp = self.get_json('/server_groups', headers=self.headers)
        self.assertEqual(4, len(resp['server_groups']))
        self.delete('/server_groups/' + sgs[0]['uuid'],
                    headers=self.headers, status=204)
        resp = self.get_json('/server_groups', headers=self.headers)
        self.assertEqual(3, len(resp['server_groups']))
