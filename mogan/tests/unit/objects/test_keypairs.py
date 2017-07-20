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
import copy

import mock
from oslo_context import context

from mogan.common import exception
from mogan import objects
from mogan.tests.unit.db import base


class TestKeyPairObject(base.DbTestCase):
    def setUp(self):
        super(TestKeyPairObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_keypair = {
            "id": 1,
            "public_key": "fake-publick-key",
            "user_id": "e78b60069fc9467e97fb4b74de9cadc1",
            "project_id": "c18e8a1a870d4c08a0b51ced6e0b6459",
            "name": "test_key",
            "fingerprint": "f1:83:34:02:f9:63:79:d4:bd:2a:1d:50:16:61:1b:cc",
            "type": "ssh",
            "created_at": "2017-04-18T09:16:18.182631+00:00",
            "updated_at": None
        }

    def test_get(self):
        with mock.patch.object(self.dbapi, 'key_pair_get',
                               autospec=True) as mock_keypair_get:
            mock_keypair_get.return_value = self.fake_keypair

            keypair = objects.KeyPair.get_by_name(
                self.context, self.fake_keypair['user_id'],
                self.fake_keypair['name'])

            mock_keypair_get.assert_called_once_with(
                self.context, self.fake_keypair['user_id'],
                self.fake_keypair['name'])
            self.assertEqual(self.context, keypair._context)
            self.assertEqual(self.fake_keypair['name'], keypair.name)
            self.assertEqual(self.fake_keypair['user_id'], keypair.user_id)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'key_pair_get',
                               autospec=True) as mock_keypair_get:
            with mock.patch.object(self.dbapi, 'key_pair_create',
                                   autospec=True) as mock_keypair_create:
                mock_keypair_get.side_effect = exception.KeypairNotFound(
                    user_id=self.fake_keypair['user_id'],
                    name=self.fake_keypair['name'])
                mock_keypair_create.return_value = self.fake_keypair
                create_params = copy.copy(self.fake_keypair)
                create_params.pop('id')
                keypair = objects.KeyPair(self.context,
                                          **create_params)
                values = keypair.obj_get_changes()
                keypair.create()
                mock_keypair_create.assert_called_once_with(
                    self.context, values)
                self.assertEqual(self.fake_keypair['name'], keypair.name)
                self.assertEqual(self.fake_keypair['user_id'], keypair.user_id)

    def test_destroy(self):
        with mock.patch.object(self.dbapi, 'key_pair_destroy',
                               autospec=True) as mock_keypair_destroy:
            mock_keypair_destroy.return_value = self.fake_keypair
            keypair = objects.KeyPair(self.context,
                                      **self.fake_keypair)
            keypair.destroy()
            mock_keypair_destroy.assert_called_once_with(
                self.context, self.fake_keypair['user_id'],
                self.fake_keypair['name'])
