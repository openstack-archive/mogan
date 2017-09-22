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

import mock
from oslo_context import context

from mogan import objects
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class TestAggregateObject(base.DbTestCase):

    def setUp(self):
        super(TestAggregateObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_aggregate = utils.get_test_aggregate(context=self.ctxt)
        self.fake_aggregate['metadetails'] = {}

    def test_get(self):
        uuid = self.fake_aggregate['uuid']
        with mock.patch.object(self.dbapi, 'aggregate_get',
                               autospec=True) as mock_aggregate_get:
            mock_aggregate_get.return_value = self.fake_aggregate
            aggregate = objects.Aggregate.get(self.context, uuid)
            mock_aggregate_get.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, aggregate._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'aggregate_create',
                               autospec=True) as mock_aggregate_create:
            mock_aggregate_create.return_value = self.fake_aggregate
            aggregate = objects.Aggregate(self.context, **self.fake_aggregate)
            values = aggregate.obj_get_changes()
            aggregate.create(self.context)
            mock_aggregate_create.assert_called_once_with(self.context, values)
            self.assertEqual(self.fake_aggregate['uuid'], aggregate['uuid'])

    def test_destroy(self):
        agg_id = self.fake_aggregate['id']
        with mock.patch.object(self.dbapi, 'aggregate_destroy',
                               autospec=True) as mock_aggregate_destroy:
            mock_aggregate_destroy.return_value = self.fake_aggregate
            aggregate = objects.Aggregate(self.context, **self.fake_aggregate)
            aggregate.destroy(self.context)
            mock_aggregate_destroy.assert_called_once_with(
                self.context, agg_id)

    def test_save(self):
        id = self.fake_aggregate['id']
        with mock.patch.object(self.dbapi, 'aggregate_update',
                               autospec=True) as mock_aggregate_update:
            aggregate = objects.Aggregate(self.context, **self.fake_aggregate)
            aggregate.name = 'changed_name'
            updates = aggregate.obj_get_changes()
            aggregate.save(self.context)
            mock_aggregate_update.return_value = self.fake_aggregate
            mock_aggregate_update.assert_called_once_with(
                self.context, id, updates)
