#
# Copyright 2016 Intel
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

import datetime
import mock
from oslo_utils import timeutils
from oslo_utils import uuidutils
from six.moves import http_client

from mogan.tests.functional.api import v1 as v1_test
from mogan.tests.unit.db import utils


def gen_post_body(**kw):
    fake_networks = [
        {
            "net_id": "c1940655-8b8e-4370-b8f9-03ba1daeca31"
        },
        {
            "net_id": "8e8ceb07-4641-4188-9b22-840755e92ee2",
            "port_type": "10GE"
        }
    ]
    return {
        "name": kw.get("name", "test_server"),
        "description": kw.get("description", "this is a test server"),
        "flavor_uuid": kw.get(
            "flavor_uuid", "0607b5f3-6111-424d-ba46-f5de39a6fa69"),
        "image_uuid": kw.get(
            "image_uuid", "efe0a06f-ca95-4808-b41e-9f55b9c5eb98"),
        "networks": kw.get("networks", fake_networks)
    }


class TestServerAuthorization(v1_test.APITestV1):

    DENY_MESSAGE = "Access was denied to the following resource: mogan:%s"

    def setUp(self):
        super(TestServerAuthorization, self).setUp()
        project_id = "0abcdef1-2345-6789-abcd-ef123456abc1"
        # evil_project is an wicked tenant, is used for unauthorization test.
        self.evil_project = "0abcdef1-2345-6789-abcd-ef123456abc9"
        self.server1 = utils.create_test_server(
            name="T1", project_id=project_id)

    @mock.patch('mogan.engine.api.API.create')
    @mock.patch('mogan.objects.Flavor.get')
    def test_server_post(self, mock_get, mock_engine_create):
        mock_get.side_effect = None
        mock_engine_create.side_effect = None
        mock_engine_create.return_value = [self.server1]
        body = gen_post_body()
        self.context.roles = "no-admin"
        # we can not prevent the evil tenant, quota will limite him.
        # Note(Shaohe): quota is in plan
        self.context.tenant = self.evil_project
        headers = self.gen_headers(self.context)
        self.post_json('/servers', body, headers=headers, status=201)

    def test_server_get_one_by_owner(self):
        # not admin but the owner
        self.context.tenant = self.server1.project_id
        headers = self.gen_headers(self.context, roles="no-admin")
        self.get_json('/servers/%s' % self.server1.uuid, headers=headers)

    def test_server_get_one_by_admin(self):
        # when the evil tenant is admin, he can do everything.
        self.context.tenant = self.evil_project
        headers = self.gen_headers(self.context, roles="admin")
        self.get_json('/servers/%s' % self.server1.uuid, headers=headers)

    def test_server_get_one_unauthorized(self):
        # not admin and not the owner
        self.context.tenant = self.evil_project
        headers = self.gen_headers(self.context, roles="no-admin")
        resp = self.get_json('/servers/%s' % self.server1.uuid,
                             True, headers=headers)
        error = self.parser_error_body(resp)
        self.assertEqual(error['faultstring'],
                         self.DENY_MESSAGE % 'server:get')


class TestPatch(v1_test.APITestV1):

    def setUp(self):
        super(TestPatch, self).setUp()
        self.server = utils.create_test_server(name="patch_server")
        self.context.tenant = self.server.project_id
        self.headers = self.gen_headers(self.context, roles="no-admin")

    def test_update_not_found(self):
        uuid = uuidutils.generate_uuid()
        response = self.patch_json('/servers/%s' % uuid,
                                   [{'path': '/extra/a', 'value': 'b',
                                     'op': 'add'}],
                                   headers=self.headers,
                                   expect_errors=True)
        self.assertEqual(http_client.NOT_FOUND, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(timeutils, 'utcnow')
    def test_replace_singular(self, mock_utcnow):
        description = 'server-new-description'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)

        mock_utcnow.return_value = test_time
        response = self.patch_json('/servers/%s' % self.server.uuid,
                                   [{'path': '/description',
                                     'value': description, 'op': 'replace'}],
                                   headers=self.headers)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(http_client.OK, response.status_code)
        result = self.get_json('/servers/%s' % self.server.uuid,
                               headers=self.headers)
        self.assertEqual(description, result['description'])
        return_updated_at = timeutils.parse_isotime(
            result['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    def test_replace_multi(self):
        extra = {"foo1": "bar1", "foo2": "bar2", "foo3": "bar3"}
        uuid = uuidutils.generate_uuid()
        server = utils.create_test_server(name='test1', uuid=uuid,
                                              extra=extra)
        new_value = 'new value'
        response = self.patch_json('/servers/%s' % server.uuid,
                                   [{'path': '/extra/foo2',
                                     'value': new_value, 'op': 'replace'}],
                                   headers=self.headers)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(http_client.OK, response.status_code)
        result = self.get_json('/servers/%s' % server.uuid,
                               headers=self.headers)

        extra["foo2"] = new_value
        self.assertEqual(extra, result['extra'])

    def test_remove_singular(self):
        uuid = uuidutils.generate_uuid()
        server = utils.create_test_server(name='test2', uuid=uuid,
                                              extra={'a': 'b'})
        response = self.patch_json('/servers/%s' % server.uuid,
                                   [{'path': '/description', 'op': 'remove'}],
                                   headers=self.headers)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(http_client.OK, response.status_code)
        result = self.get_json('/servers/%s' % server.uuid,
                               headers=self.headers)
        self.assertIsNone(result['description'])

        # Assert nothing else was changed
        self.assertEqual(server.uuid, result['uuid'])
        self.assertEqual(server.extra, result['extra'])

    def test_remove_multi(self):
        extra = {"foo1": "bar1", "foo2": "bar2", "foo3": "bar3"}
        uuid = uuidutils.generate_uuid()
        server = utils.create_test_server(name='test3', extra=extra,
                                              uuid=uuid, description="foobar")

        # Removing one item from the collection
        response = self.patch_json('/servers/%s' % server.uuid,
                                   [{'path': '/extra/foo2', 'op': 'remove'}],
                                   headers=self.headers)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(http_client.OK, response.status_code)
        result = self.get_json('/servers/%s' % server.uuid,
                               headers=self.headers)
        extra.pop("foo2")
        self.assertEqual(extra, result['extra'])

        # Removing the collection
        response = self.patch_json('/servers/%s' % server.uuid,
                                   [{'path': '/extra', 'op': 'remove'}],
                                   headers=self.headers)
        self.assertEqual(http_client.OK, response.status_code)
        result = self.get_json('/servers/%s' % server.uuid,
                               headers=self.headers)
        self.assertEqual({}, result['extra'])

        # Assert nothing else was changed
        self.assertEqual(server.uuid, result['uuid'])
        self.assertEqual(server.description, result['description'])

    def test_remove_non_existent_property_fail(self):
        response = self.patch_json(
            '/servers/%s' % self.server.uuid,
            [{'path': '/extra/non-existent', 'op': 'remove'}],
            headers=self.headers,
            expect_errors=True)
        self.assertEqual(http_client.BAD_REQUEST, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_add_root(self):
        response = self.patch_json('/servers/%s' % self.server.uuid,
                                   [{'path': '/description', 'value': 'test',
                                     'op': 'add'}],
                                   headers=self.headers)
        self.assertEqual(http_client.OK, response.status_int)
        self.assertEqual('application/json', response.content_type)

    def test_add_root_non_existent(self):
        response = self.patch_json('/servers/%s' % self.server.uuid,
                                   [{'path': '/foo', 'value': 'bar',
                                     'op': 'add'}],
                                   expect_errors=True,
                                   headers=self.headers)
        self.assertEqual(http_client.BAD_REQUEST, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_add_multi(self):
        response = self.patch_json('/servers/%s' % self.server.uuid,
                                   [{'path': '/extra/foo1', 'value': 'bar1',
                                     'op': 'add'},
                                    {'path': '/extra/foo2', 'value': 'bar2',
                                     'op': 'add'}],
                                   headers=self.headers)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(http_client.OK, response.status_code)
        result = self.get_json('/servers/%s' % self.server.uuid,
                               headers=self.headers)
        expected = {"foo1": "bar1", "foo2": "bar2"}
        self.assertEqual(expected, result['extra'])

    def test_remove_uuid(self):
        response = self.patch_json('/servers/%s' % self.server.uuid,
                                   [{'path': '/uuid', 'op': 'remove'}],
                                   expect_errors=True,
                                   headers=self.headers)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(http_client.BAD_REQUEST, response.status_int)
        self.assertTrue(response.json['error_message'])
