#
# Copyright 2016 Huawei Technologies Co., Ltd.
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

import mock

from nimble.tests.functional.api import v1 as v1_test


class TestInstanceType(v1_test.APITestV1):

    TYPE_UUIDS = ['ff28b5a2-73e5-431c-b4b7-1b96b74bca7b',
                  '94baf80e-2bae-4c3e-8dab-38b5441e7097',
                  '4bcfff85-c55a-493b-b544-b6c90b8fb397',
                  'e50fb289-4ee1-47dd-b371-6ca39af12888']

    def setUp(self):
        super(TestInstanceType, self).setUp()

    @mock.patch('oslo_utils.uuidutils.generate_uuid')
    def _prepare_instance_types(self, mocked):
        mocked.side_effect = self.TYPE_UUIDS
        for i in range(4):
            body = {"name": "test" + str(i),
                    "description": "just test" + str(i)}
            self.post_json('/types', body, status=201)

    def test_instance_type_post(self):
        body = {"name": "test", "description": "just test"}
        resp = self.post_json('/types', body, status=201)
        self.assertEqual('test', resp['name'])
        self.assertEqual('just test', resp['description'])
        self.assertEqual(True, resp['is_public'])
        self.assertIn('uuid', resp)
        self.assertIn('extra_specs', resp)
        self.assertIn('links', resp)

    def test_instance_type_get_all(self):
        self._prepare_instance_types()
        resp = self.get_json('/types')
        self.assertEqual(4, len(resp['types']))

    def test_instance_type_get_one(self):
        self._prepare_instance_types()
        resp = self.get_json('/types/' + self.TYPE_UUIDS[0])
        self.assertEqual('test0', resp['name'])
        self.assertEqual('just test0', resp['description'])

    def test_instance_type_delete(self):
        self._prepare_instance_types()
        resp = self.get_json('/types')
        self.assertEqual(4, len(resp['types']))
        self.delete('/types/' + self.TYPE_UUIDS[0], status=204)
        resp = self.get_json('/types')
        self.assertEqual(3, len(resp['types']))
