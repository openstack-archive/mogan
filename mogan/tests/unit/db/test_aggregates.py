# Copyright 2017 Huawei Technologies Co.,LTD.
# All Rights Reserved.
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

"""Tests for manipulating Aggregates via the DB API"""

from oslo_utils import uuidutils
import six

from mogan.common import exception
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class DbAggregateTestCase(base.DbTestCase):

    def setUp(self):
        super(DbAggregateTestCase, self).setUp()
        self.aggregate = utils.create_test_aggregate()

    def test_create_aggregate(self):
        utils.create_test_aggregate(name='testing')

    def test_create_aggregate_already_exists(self):
        self.assertRaises(exception.AggregateNameExists,
                          utils.create_test_aggregate,
                          name=self.aggregate['name'])

    def test_get_aggregate_list(self):
        uuids = [self.aggregate['uuid']]
        for i in range(1, 6):
            aggregate = utils.create_test_aggregate(
                uuid=uuidutils.generate_uuid(),
                name=six.text_type(i))
            uuids.append(six.text_type(aggregate['uuid']))
        res = self.dbapi.aggregate_get_all(self.context)
        res_uuids = [r['uuid'] for r in res]
        six.assertCountEqual(self, uuids, res_uuids)

    def test_get_aggregate(self):
        aggregate = self.dbapi.aggregate_get(
            self.context, self.aggregate['uuid'])

        self.assertEqual(self.aggregate['uuid'], aggregate['uuid'])

    def test_get_aggregate_that_does_not_exist(self):
        self.assertRaises(exception.AggregateNotFound,
                          self.dbapi.aggregate_get,
                          self.context,
                          uuidutils.generate_uuid())

    def test_destroy_aggregate(self):
        self.dbapi.aggregate_destroy(self.context, self.aggregate['id'])

        self.assertRaises(exception.AggregateNotFound,
                          self.dbapi.aggregate_destroy,
                          self.context,
                          self.aggregate['id'])

    def test_destroy_aggregate_that_does_not_exist(self):
        self.assertRaises(exception.AggregateNotFound,
                          self.dbapi.aggregate_destroy,
                          self.context,
                          uuidutils.generate_uuid())
