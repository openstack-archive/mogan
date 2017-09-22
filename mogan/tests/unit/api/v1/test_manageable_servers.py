#
# Copyright 2017 Fiberhome
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
from oslo_utils import uuidutils

from mogan.tests.functional.api import v1 as v1_test
from mogan.tests.unit.db import utils


def gen_post_body(**kw):
    return {
        "name": kw.get("name", "test_manageable_server"),
        "description": kw.get("description", "This is a manageable server"),
        "node_uuid": "aacdbd78-d670-409e-95aa-ecfcfb94fee2",
        "metadata": {"My Server Name": "Apache1"}
    }


class TestManageableServers(v1_test.APITestV1):

    DENY_MESSAGE = "Access was denied to the following resource: mogan:%s"

    def setUp(self):
        super(TestManageableServers, self).setUp()
        self.project_id = "0abcdef1-2345-6789-abcd-ef123456abc1"
        # evil_project is an wicked tenant, is used for unauthorization test.
        self.evil_project = "0abcdef1-2345-6789-abcd-ef123456abc9"
        self.server1 = utils.create_test_server(
            name="T1", project_id=self.project_id)

    def test_server_get_manageable_servers_with_invalid_rule(self):
        self.context.tenant = self.evil_project
        headers = self.gen_headers(self.context, roles="no-admin")
        resp = self.get_json('/manageable_servers', True, headers=headers)
        error = self.parser_error_body(resp)
        self.assertEqual(self.DENY_MESSAGE % 'manageable_servers:get_all',
                         error['faultstring'])

    @mock.patch('mogan.engine.api.API.get_manageable_servers')
    def test_server_get_manageable_servers(self, mock_get):
        mock_get.return_value = [{'uuid': uuidutils.generate_uuid(),
                                  'name': "test_node",
                                  'resource_class': "gold"}]
        self.context.tenant = self.project_id
        headers = self.gen_headers(self.context, roles="admin")
        resp = self.get_json('/manageable_servers', headers=headers)
        self.assertIn("uuid", resp['manageable_servers'][0])

    @mock.patch('mogan.engine.api.API.manage')
    def test_manage_server_with_invalid_rule(self, mock_engine_manage):
        self.context.tenant = self.evil_project
        headers = self.gen_headers(self.context, roles="no-admin")
        body = gen_post_body()
        resp = self.post_json('/manageable_servers', body, expect_errors=True,
                              headers=headers)
        error = self.parser_error_body(resp)
        self.assertEqual(self.DENY_MESSAGE % 'manageable_servers:create',
                         error['faultstring'])

    @mock.patch('mogan.engine.api.API.manage')
    def test_manage_server(self, mock_engine_manage):
        mock_engine_manage.side_effect = None
        mock_engine_manage.return_value = self.server1
        body = gen_post_body()
        # we can not prevent the evil tenant, quota will limite him.
        self.context.tenant = self.project_id
        headers = self.gen_headers(self.context, roles="admin")
        self.post_json('/manageable_servers', body, headers=headers,
                       status=201)
