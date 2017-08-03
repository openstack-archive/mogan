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
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from mogan.tests.tempest.api import base


class BaremetalComputeAPIServerGroupsTest(base.BaseBaremetalComputeTest):
    @classmethod
    def resource_setup(cls):
        super(BaremetalComputeAPIServerGroupsTest, cls).resource_setup()
        sg_body = {
            "name": "tempest-test-server_group",
            "policies": ["anti-affinity"]
        }
        cls.server_group = cls.baremetal_compute_client.create_server_group(
            **sg_body)

    @classmethod
    def resource_cleanup(cls):
        super(BaremetalComputeAPIServerGroupsTest, cls).resource_cleanup()
        cls.baremetal_compute_client.delete_server_group(
            cls.server_group['uuid'])

    @decorators.idempotent_id('7fd1b48d-54ad-4848-8653-02d313e99cb7')
    def test_server_group_create(self):
        sg_body = {
            "name": "test-server-group",
            "policies": ["anti-affinity"]
        }
        server_group = self.baremetal_compute_client.create_server_group(
            **sg_body)
        self.assertEqual("test-server-group", server_group['name'])
        self.assertItemsEqual(["anti-affinity"], server_group['policies'])

    @decorators.idempotent_id('e174bcb7-d7fc-467a-8343-a27dd8b2e13c')
    def test_server_group_show(self):
        server_group = self.baremetal_compute_client.show_server_group(
            self.server_group['uuid'])
        self.assertEqual("tempest-test-server_group", server_group['name'])
        self.assertItemsEqual(["anti-affinity"], server_group['policies'])

    @decorators.idempotent_id('b71d790b-92da-4625-8fea-eb79ff4a7a57')
    def test_server_groups_list(self):
        server_groups = self.baremetal_compute_client.list_server_groups()
        self.assertEqual(1, len(server_groups))
        server_group = server_groups[0]
        self.assertEqual("tempest-test-server_groups", server_group['name'])
        self.assertItemsEqual(["anti-affinity"], server_group['policies'])

    @decorators.idempotent_id('d14b8011-ce6e-4454-b94d-06b5d5c1ed83')
    def test_server_group_delete(self):
        sg_body = {
            "name": "test-server-group-delete",
            "policies": ["anti-affinity"]
        }
        server_group = self.baremetal_compute_client.create_server_group(
            **sg_body)
        self.baremetal_compute_client.delete_server_group(server_group['uuid'])
        self.assertRaises(lib_exc.NotFound,
                          self.baremetal_compute_client.show_server_group,
                          server_group['uuid'])
