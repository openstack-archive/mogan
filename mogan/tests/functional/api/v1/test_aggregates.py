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

import mock
import six
from six.moves import http_client

from mogan.tests.functional.api import v1 as v1_test


class TestAggregate(v1_test.APITestV1):

    AGGREGATE_UUIDS = ['ff28b5a2-73e5-431c-b4b7-1b96b74bca7b',
                       '94baf80e-2bae-4c3e-8dab-38b5441e7097',
                       '4bcfff85-c55a-493b-b544-b6c90b8fb397',
                       'e50fb289-4ee1-47dd-b371-6ca39af12888']

    def setUp(self):
        super(TestAggregate, self).setUp()
        self.headers = self.gen_headers(self.context, roles="admin")

    @mock.patch('oslo_utils.uuidutils.generate_uuid')
    def _prepare_aggregates(self, mocked):
        mocked.side_effect = self.AGGREGATE_UUIDS
        for i in six.moves.xrange(4):
            body = {"name": "test" + str(i),
                    "metadata": {"k1": "v1"}}
            self.post_json('/aggregates', body,
                           headers=self.headers, status=201)

    def test_aggregate_post(self):
        body = {"name": "test",
                "metadata": {"k1": "v1"}}
        resp = self.post_json(
            '/aggregates', body, headers=self.headers, status=201)
        resp = resp.json
        self.assertEqual('test', resp['name'])
        self.assertEqual({'k1': 'v1'}, resp['metadata'])
        self.assertIn('uuid', resp)
        self.assertIn('links', resp)

    def test_aggregate_get_all(self):
        self._prepare_aggregates()
        resp = self.get_json('/aggregates', headers=self.headers)
        self.assertEqual(4, len(resp['aggregates']))

    def test_aggregate_get_one(self):
        self._prepare_aggregates()
        resp = self.get_json('/aggregates/' + self.AGGREGATE_UUIDS[0],
                             headers=self.headers)
        self.assertEqual('test0', resp['name'])
        self.assertEqual({'k1': 'v1'}, resp['metadata'])

    def test_aggregate_delete(self):
        self._prepare_aggregates()
        resp = self.get_json('/aggregates', headers=self.headers)
        self.assertEqual(4, len(resp['aggregates']))
        self.delete('/aggregates/' + self.AGGREGATE_UUIDS[0],
                    headers=self.headers, status=204)
        resp = self.get_json('/aggregates', headers=self.headers)
        self.assertEqual(3, len(resp['aggregates']))

    def test_aggregate_update(self):
        self._prepare_aggregates()
        resp = self.get_json('/aggregates/' + self.AGGREGATE_UUIDS[0],
                             headers=self.headers)
        self.assertEqual('test0', resp['name'])
        self.patch_json('/aggregates/' + self.AGGREGATE_UUIDS[0],
                        [{'path': '/name', 'value': 'updated_name',
                          'op': 'replace'},
                         {'path': '/metadata/k2', 'value': 'v2',
                          'op': 'add'}],
                        headers=self.headers, status=200)
        resp = self.get_json('/aggregates/' + self.AGGREGATE_UUIDS[0],
                             headers=self.headers)
        self.assertEqual('updated_name', resp['name'])
        self.assertItemsEqual({'k1': 'v1', 'k2': 'v2'}, resp['metadata'])

    def test_aggregate_update_with_empty_az(self):
        self._prepare_aggregates()
        response = self.patch_json('/aggregates/' + self.AGGREGATE_UUIDS[0],
                                   [{'path': '/metadata/availability_zone',
                                     'value': '', 'op': 'add'}],
                                   headers=self.headers,
                                   expect_errors=True)
        self.assertEqual(http_client.BAD_REQUEST, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
