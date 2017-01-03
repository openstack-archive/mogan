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

import six

from tempest.common.utils import data_utils
from tempest.lib import exceptions as lib_exc
from tempest import test

from mogan.tests.tempest.api import base


class BaremetalComputeAPITest(base.BaseBaremetalComputeTest):

    @classmethod
    def resource_setup(cls):
        super(BaremetalComputeAPITest, cls).resource_setup()
        for i in six.moves.xrange(3):
            body = {"name": data_utils.rand_name('nimble_instance_type'),
                    "description": "mogan instance type description",
                    'is_public': bool(data_utils.rand_int_id(0, 1))}
            resp = cls.baremetal_compute_client.create_instance_type(**body)
            cls.type_ids.append(resp['uuid'])

    @test.idempotent_id('4b256d35-47a9-4195-8f7e-56ceb4ce4737')
    def test_type_list(self):
        # List instance types
        type_list = self.baremetal_compute_client.list_instance_types()

        # Verify created instance type in the list
        fetched_ids = [t['uuid'] for t in type_list]
        missing_types = [a for a in self.type_ids if a not in fetched_ids]
        self.assertEqual(0, len(missing_types),
                         "Failed to find the following created"
                         " instance_type(s) in a fetched list: %s" %
                         ', '.join(str(t) for t in missing_types))

    @test.idempotent_id('f6ad64af-abc9-456c-9109-bc27cd9af635')
    def test_type_create_show_delete(self):
        # Create an instance type
        body = {"name": 'nimble_type_create',
                "description": "mogan instance type description",
                'is_public': True}
        resp = self.baremetal_compute_client.create_instance_type(**body)
        self.assertEqual('nimble_type_create', resp['name'])
        self.assertEqual('mogan instance type description',
                         resp['description'])
        self.assertEqual(True, resp['is_public'])
        self.assertIn('uuid', resp)
        self.assertIn('extra_specs', resp)
        self.assertIn('links', resp)
        resp = self.baremetal_compute_client.show_instance_type(resp['uuid'])
        self.assertEqual('nimble_type_create', resp['name'])
        self.assertEqual('mogan instance type description',
                         resp['description'])
        self.assertEqual(True, resp['is_public'])
        self.assertIn('uuid', resp)
        self.assertIn('extra_specs', resp)
        self.assertIn('links', resp)
        self.baremetal_compute_client.delete_instance_type(resp['uuid'])
        self.assertRaises(lib_exc.NotFound,
                          self.baremetal_compute_client.show_instance_type,
                          resp['uuid'])
