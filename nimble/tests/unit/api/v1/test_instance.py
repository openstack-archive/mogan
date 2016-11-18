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

import mock

from nimble.tests.functional.api import v1 as v1_test
from nimble.tests.unit.db import utils


def gen_post_body(**kw):
    fake_networks = [
        {
            "uuid": "c1940655-8b8e-4370-b8f9-03ba1daeca31"
        },
        {
            "uuid": "8e8ceb07-4641-4188-9b22-840755e92ee2",
            "port_type": "10GE"
        }
    ]
    return {
        "name": kw.get("name", "test_instance"),
        "description": kw.get("description", "this is a test instance"),
        "instance_type_uuid": kw.get(
            "instance_type_uuid", "0607b5f3-6111-424d-ba46-f5de39a6fa69"),
        "image_uuid": kw.get(
            "image_uuid", "efe0a06f-ca95-4808-b41e-9f55b9c5eb98"),
        "networks": kw.get("networks", fake_networks)
    }


class TestInstanceAuthorization(v1_test.APITestV1):

    DENY_MESSAGE = "Access was denied to the following resource: nimble:%s"

    def setUp(self):
        super(TestInstanceAuthorization, self).setUp()
        project_id = "0abcdef1-2345-6789-abcd-ef123456abc1"
        # evil_project is an wicked tenant, is used for unauthorization test.
        self.evil_project = "0abcdef1-2345-6789-abcd-ef123456abc9"
        self.instance1 = utils.create_test_instance(
            name="T1", project_id=project_id)

    @mock.patch('nimble.engine.rpcapi.EngineAPI.create_instance')
    @mock.patch('nimble.objects.InstanceType.get')
    def test_instance_post(self, mock_get, mock_rpi_create):
        mock_get.side_effect = None
        mock_rpi_create.side_effect = None
        body = gen_post_body()
        self.context.roles = "no-admin"
        # we can not prevent the evil tenant, quota will limite him.
        # Note(Shaohe): quota is in plan
        self.context.project_id = self.evil_project
        headers = self.gen_headers(self.context)
        self.post_json('/instances', body, headers=headers, status=201)

    def test_instance_get_one_by_owner(self):
        # not admin but the owner
        self.context.project_id = self.instance1.project_id
        headers = self.gen_headers(self.context, roles="no-admin")
        self.get_json('/instances/%s' % self.instance1.uuid, headers=headers)

    def test_instance_get_one_by_admin(self):
        # admin but the owner
        self.context.project_id = self.instance1.project_id
        # when the evil tenant is admin, he can do everything.
        self.context.project_id = self.evil_project
        headers = self.gen_headers(self.context, roles="admin")
        self.get_json('/instances/%s' % self.instance1.uuid, headers=headers)

    def test_instance_get_one_unauthorized(self):
        # not admin and not the owner
        self.context.project_id = self.evil_project
        headers = self.gen_headers(self.context, roles="no-admin")
        resp = self.get_json('/instances/%s' % self.instance1.uuid,
                             True, headers=headers)
        error = self.parser_error_body(resp)
        self.assertEqual(error['faultstring'],
                         self.DENY_MESSAGE % 'instance:get')
