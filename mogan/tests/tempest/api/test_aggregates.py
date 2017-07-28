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


class BaremetalComputeAPIAggregatesTest(base.BaseBaremetalComputeTest):

    @classmethod
    def resource_setup(cls):
        super(BaremetalComputeAPIAggregatesTest, cls).resource_setup()
        aggregate_body = {
            "name": "tempest-test-aggregate",
            "metadata": {"k1", "v1"}
        }
        cls.aggregate = cls.baremetal_compute_client.create_aggregate(
            **aggregate_body)

    @classmethod
    def resource_cleanup(cls):
        super(BaremetalComputeAPIAggregatesTest, cls).resource_cleanup()
        cls.aggregate = cls.baremetal_compute_client.delete_aggregate(
            cls.aggregate['uuid'])

    @decorators.idempotent_id('82d94aab-62f1-4d85-bcb6-5c360f84d9b4')
    def test_aggregate_create(self):
        aggregate_body = {
            "name": "tempest-test-aggregate",
            "metadata": {"k1", "v1"}
        }
        aggregate = self.baremetal_compute_client.create_aggregate(
            **aggregate_body)
        self.assertEqual("tempest-test-aggregate", aggregate['name'])
        self.assertItemsEqual({'k1', 'v1'}, aggregate['metadata'])
        self.aggregate = self.baremetal_compute_client.delete_aggregate(
            aggregate['uuid'])

    @decorators.idempotent_id('c7062d65-09f7-4efa-8852-3ac543416c31')
    def test_aggregate_show(self):
        aggregate = self.baremetal_compute_client.show_aggregate(
            self.aggregate['uuid'])
        self.assertEqual("tempest-test-aggregate", aggregate['name'])
        self.assertItemsEqual({'k1', 'v1'}, aggregate['metadata'])

    @decorators.idempotent_id('a0520c12-4e7d-46ac-a0bc-c4c42fe3a344')
    def test_aggregates_list(self):
        aggregates = self.baremetal_compute_client.list_aggregates()
        self.assertEqual(1, len(aggregates))
        aggregate = aggregates[0]
        self.assertEqual("tempest-test-aggregate", aggregate['name'])
        self.assertItemsEqual({'k1', 'v1'}, aggregate['metadata'])

    @decorators.idempotent_id('65614c7e-a1d9-4d1b-aa9a-6893616c0cc1')
    def test_aggregate_delete(self):
        aggregate_body = {
            "name": "tempest-test-aggregate",
            "metadata": {"k1", "v1"}
        }
        aggregate = self.baremetal_compute_client.create_aggregate(
            **aggregate_body)
        self.aggregate = self.baremetal_compute_client.delete_aggregate(
            aggregate['uuid'])
        self.assertRaises(lib_exc.NotFound,
                          self.baremetal_compute_client.show_aggregate,
                          aggregate['uuid'])
