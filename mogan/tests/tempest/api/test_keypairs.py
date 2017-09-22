#
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


class BaremetalComputeAPIKeypairsTest(base.BaseBaremetalComputeTest):

    @classmethod
    def resource_setup(cls):
        super(BaremetalComputeAPIKeypairsTest, cls).resource_setup()
        keypair_body = {
            "type": "ssh",
            "name": "tempest-test-keypair"
        }
        cls.keypair = cls.baremetal_compute_client.create_keypair(
            **keypair_body)

    @classmethod
    def resource_cleanup(cls):
        super(BaremetalComputeAPIKeypairsTest, cls).resource_cleanup()
        cls.keypair = cls.baremetal_compute_client.delete_keypair(
            cls.keypair['name'])

    @decorators.idempotent_id('82d94aab-62f1-4d85-bcb6-5c360f84d9b4')
    def test_keypair_create(self):
        keypair_body = {
            "type": "ssh",
            "name": "test-create"
        }
        keypair = self.baremetal_compute_client.create_keypair(**keypair_body)
        self.assertEqual("ssh", keypair['type'])
        self.assertEqual('test-create', keypair['name'])
        self.assertIn('public_key', keypair)
        self.assertIn('private_key', keypair)
        self.assertIn('user_id', keypair)
        self.assertIn('fingerprint', keypair)
        self.keypair = self.baremetal_compute_client.delete_keypair(
            'test-create')

    @decorators.idempotent_id('668b2c37-710e-4430-be7c-63d7b9041938')
    def test_keypair_create_with_user_id(self):
        user_id = 'cd626e792caf46b694d24e3490813bca'
        keypair_body = {
            "type": "ssh",
            "name": "test-create-user",
            "user_id": user_id
        }
        keypair = self.baremetal_compute_client.create_keypair(**keypair_body)
        self.assertEqual("ssh", keypair['type'])
        self.assertEqual('test-create-user', keypair['name'])
        self.assertEqual(user_id, keypair['user_id'])
        self.assertIn('public_key', keypair)
        self.assertIn('private_key', keypair)
        self.assertIn('user_id', keypair)
        self.assertIn('fingerprint', keypair)
        self.keypair = self.baremetal_compute_client.delete_keypair(
            'test-create-user', user_id)

    @decorators.idempotent_id('c7062d65-09f7-4efa-8852-3ac543416c31')
    def test_keypair_show(self):
        keypair = self.baremetal_compute_client.show_keypair(
            self.keypair['name'])
        self.assertEqual("ssh", keypair['type'])
        self.assertEqual('tempest-test-keypair', keypair['name'])
        self.assertIn('user_id', keypair)
        self.assertIn('public_key', keypair)
        self.assertIn('user_id', keypair)
        self.assertIn('fingerprint', keypair)

    @decorators.idempotent_id('a0520c12-4e7d-46ac-a0bc-c4c42fe3a344')
    def test_keypairs_list(self):
        keypairs = self.baremetal_compute_client.list_keypairs()
        self.assertIsInstance(keypairs, list)
        self.assertEqual(1, len(keypairs))
        keypair = keypairs[0]
        self.assertEqual("ssh", keypair['type'])
        self.assertEqual('tempest-test-keypair', keypair['name'])
        self.assertIn('user_id', keypair)
        self.assertIn('public_key', keypair)
        self.assertIn('user_id', keypair)
        self.assertIn('fingerprint', keypair)

    @decorators.idempotent_id('65614c7e-a1d9-4d1b-aa9a-6893616c0cc1')
    def test_keypair_delete(self):
        keypair_body = {
            "type": "ssh",
            "name": "test-delete"
        }
        keypair = self.baremetal_compute_client.create_keypair(**keypair_body)
        self.assertEqual('test-delete', keypair['name'])
        self.baremetal_compute_client.delete_keypair(keypair['name'])
        self.assertRaises(lib_exc.NotFound,
                          self.baremetal_compute_client.show_keypair,
                          keypair['name'])
