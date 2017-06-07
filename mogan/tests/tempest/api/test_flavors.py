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

from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from mogan.tests.tempest.api import base


class BaremetalComputeAPITest(base.BaseBaremetalComputeTest):

    @classmethod
    def resource_setup(cls):
        super(BaremetalComputeAPITest, cls).resource_setup()
        for i in six.moves.xrange(2):
            body = {"name": "mogan_flavor_" + {0: 'public', 1: 'private'}[i],
                    "description": "mogan flavor description",
                    'is_public': not bool(i)}
            resp = cls.baremetal_compute_client.create_flavor(**body)
            cls.flavor_ids.append(resp['uuid'])

    @decorators.idempotent_id('4b256d35-47a9-4195-8f7e-56ceb4ce4737')
    def test_flavor_list(self):
        # List server types
        flavor_list = self.baremetal_compute_client.list_flavors()

        # Verify created server type in the list
        fetched_ids = [f['uuid'] for f in flavor_list]
        missing_flavors = [a for a in self.flavor_ids if a not in fetched_ids]
        self.assertEqual(0, len(missing_flavors),
                         "Failed to find the following created"
                         " flavor(s) in a fetched list: %s" %
                         ', '.join(str(t) for t in missing_flavors))

    @decorators.idempotent_id('f6ad64af-abc9-456c-9109-bc27cd9af635')
    def test_flavor_create(self):
        # Create a flavor
        body = {"name": 'mogan_flavor_create',
                "description": "mogan flavor description",
                'is_public': True}
        resp = self.baremetal_compute_client.create_flavor(**body)
        self.assertEqual('mogan_flavor_create', resp['name'])
        self.assertEqual('mogan flavor description',
                         resp['description'])
        self.assertEqual(True, resp['is_public'])
        self.assertIn('uuid', resp)
        self.assertIn('extra_specs', resp)
        self.assertIn('links', resp)
        self.flavor_ids.append(resp['uuid'])

    @decorators.idempotent_id('ab1a5147-0e3e-4a29-8c28-505d29fac8dd')
    def test_flavor_show(self):
        resp = self.baremetal_compute_client.show_flavor(self.flavor_ids[0])
        self.assertIn('mogan_flavor_public', resp['name'])
        self.assertEqual('mogan flavor description',
                         resp['description'])
        self.assertEqual(True, resp['is_public'])
        self.assertIn('uuid', resp)
        self.assertIn('extra_specs', resp)
        self.assertIn('links', resp)

    @decorators.idempotent_id('f787f8e4-aa20-4c19-a9ec-44bff85d8634')
    def test_flavor_delete(self):
        flavor_id = self.flavor_ids.pop(-1)
        self.baremetal_compute_client.delete_flavor(flavor_id)
        self.assertRaises(lib_exc.NotFound,
                          self.baremetal_compute_client.show_flavor,
                          flavor_id)
