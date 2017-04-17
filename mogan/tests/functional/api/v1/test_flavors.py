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
import six

from oslo_serialization import jsonutils

from mogan.tests.functional.api import v1 as v1_test


class TestFlavor(v1_test.APITestV1):

    FLAVOR_UUIDS = ['ff28b5a2-73e5-431c-b4b7-1b96b74bca7b',
                    '94baf80e-2bae-4c3e-8dab-38b5441e7097',
                    '4bcfff85-c55a-493b-b544-b6c90b8fb397',
                    'e50fb289-4ee1-47dd-b371-6ca39af12888']

    def setUp(self):
        super(TestFlavor, self).setUp()

    @mock.patch('oslo_utils.uuidutils.generate_uuid')
    def _prepare_flavors(self, mocked):
        mocked.side_effect = self.FLAVOR_UUIDS
        for i in six.moves.xrange(4):
            body = {"name": "test" + str(i),
                    "description": "just test" + str(i)}
            self.post_json('/flavors', body, status=201)

    def test_flavor_post(self):
        body = {"name": "test", "description": "just test"}
        resp = self.post_json('/flavors', body, status=201)
        resp = resp.json
        self.assertEqual('test', resp['name'])
        self.assertEqual('just test', resp['description'])
        self.assertEqual(True, resp['is_public'])
        self.assertIn('uuid', resp)
        self.assertIn('extra_specs', resp)
        self.assertIn('links', resp)

    def test_flavor_get_all(self):
        self._prepare_flavors()
        resp = self.get_json('/flavors')
        self.assertEqual(4, len(resp['flavors']))

    def test_flavor_get_one(self):
        self._prepare_flavors()
        resp = self.get_json('/flavors/' + self.FLAVOR_UUIDS[0])
        self.assertEqual('test0', resp['name'])
        self.assertEqual('just test0', resp['description'])

    def test_flavor_delete(self):
        self._prepare_flavors()
        resp = self.get_json('/flavors')
        self.assertEqual(4, len(resp['flavors']))
        self.delete('/flavors/' + self.FLAVOR_UUIDS[0], status=204)
        resp = self.get_json('/flavors')
        self.assertEqual(3, len(resp['flavors']))

    def test_flavor_update(self):
        self._prepare_flavors()
        resp = self.get_json('/flavors/' + self.FLAVOR_UUIDS[0])
        self.assertEqual('test0', resp['name'])
        self.assertEqual('just test0', resp['description'])
        values = {"name": "update_name", "description": "updated_description",
                  "is_public": False}
        self.put_json('/flavors/' + self.FLAVOR_UUIDS[0], values, status=200)
        resp = self.get_json('/flavors/' + self.FLAVOR_UUIDS[0])
        self.assertEqual('update_name', resp['name'])
        self.assertEqual('updated_description', resp['description'])
        self.assertEqual(False, resp['is_public'])


class TestFlavorExtra(v1_test.APITestV1):
    FLAVOR_UUID = 'ff28b5a2-73e5-431c-b4b7-1b96b74bca7b'

    def setUp(self):
        super(TestFlavorExtra, self).setUp()
        self._prepare_flavor()

    @mock.patch('oslo_utils.uuidutils.generate_uuid')
    def _prepare_flavor(self, mocked):
        mocked.return_value = self.FLAVOR_UUID
        body = {"name": "test_flavor_extra",
                "description": "just test flavor extra"}
        self.post_json('/flavors', body, status=201)

    def test_list_extra_empty(self):
        resp = self.get_json('/flavors/%s/extraspecs' % self.FLAVOR_UUID)
        self.assertEqual({}, resp['extra_specs'])

    def test_add_extra(self):
        resp = self.patch_json('/flavors/%s/extraspecs' % self.FLAVOR_UUID,
                               {'test_key': 'test_value'})
        resp = resp.json
        self.assertEqual({'extra_specs': {'test_key': 'test_value'}}, resp)

    def test_update_extra(self):
        resp = self.patch_json('/flavors/%s/extraspecs' % self.FLAVOR_UUID,
                               {'test_key': 'test_value1'})
        resp = resp.json
        self.assertEqual({'extra_specs': {'test_key': 'test_value1'}}, resp)

        resp = self.patch_json('/flavors/%s/extraspecs' % self.FLAVOR_UUID,
                               {'test_key': 'test_value2'})
        resp = resp.json
        self.assertEqual({'extra_specs': {'test_key': 'test_value2'}}, resp)

    def test_list_extra(self):
        resp = self.patch_json('/flavors/%s/extraspecs' % self.FLAVOR_UUID,
                               {'test_key1': 'test_value1',
                                'test_key2': 'test_value2'})
        resp = resp.json
        self.assertEqual(
            '{"test_key1": "test_value1", "test_key2": "test_value2"}',
            jsonutils.dumps(resp['extra_specs'], sort_keys=True))

        self.patch_json('/flavors/%s/extraspecs' % self.FLAVOR_UUID,
                        {'test_key3': 'test_value3'})
        resp = self.get_json('/flavors/%s/extraspecs' % self.FLAVOR_UUID)
        self.assertEqual(
            '{"test_key1": "test_value1", "test_key2": "test_value2", '
            '"test_key3": "test_value3"}',
            jsonutils.dumps(resp['extra_specs'], sort_keys=True))

    def test_delete_extra(self):
        resp = self.patch_json('/flavors/%s/extraspecs' % self.FLAVOR_UUID,
                               {'test_key1': 'test_value1',
                                'test_key2': 'test_value2'})
        resp = resp.json
        self.assertEqual(
            '{"test_key1": "test_value1", "test_key2": "test_value2"}',
            jsonutils.dumps(resp['extra_specs'], sort_keys=True))

        self.delete('/flavors/%s/extraspecs/test_key1' % self.FLAVOR_UUID)
        resp = self.get_json('/flavors/%s/extraspecs' % self.FLAVOR_UUID)
        self.assertEqual({'test_key2': 'test_value2'}, resp['extra_specs'])
