# Copyright 2016 Huawei Technologies Co.,LTD.
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

"""Tests for manipulating Instance Types via the DB API"""

from oslo_utils import uuidutils
import six

from nimble.common import exception
from nimble.tests.unit.db import base
from nimble.tests.unit.db import utils


class DbInstanceTypeTestCase(base.DbTestCase):

    def setUp(self):
        super(DbInstanceTypeTestCase, self).setUp()
        self.context = {}
        self.instance_type = utils.create_test_instance_type()

    def test_create_instance_type(self):
        utils.create_test_instance_type(name='testing')

    def test_create_instance_type_already_exists(self):
        self.assertRaises(exception.InstanceTypeAlreadyExists,
                          utils.create_test_instance_type,
                          uuid=self.instance_type['uuid'])

    def test_get_instance_type_list(self):
        uuids = [self.instance_type['uuid']]
        for i in range(1, 6):
            inst_type = utils.create_test_instance_type(
                uuid=uuidutils.generate_uuid(),
                name=six.text_type(i))
            uuids.append(six.text_type(inst_type['uuid']))
        res = self.dbapi.instance_type_get_all(self.context)
        res_uuids = [r['uuid'] for r in res]
        six.assertCountEqual(self, uuids, res_uuids)

    def test_get_instance_type(self):
        instance_type = self.dbapi.instance_type_get(
            self.context, self.instance_type['uuid'])

        self.assertEqual(self.instance_type['uuid'], instance_type['uuid'])

    def test_get_instance_type_that_does_not_exist(self):
        self.assertRaises(exception.InstanceTypeNotFound,
                          self.dbapi.instance_type_get,
                          self.context,
                          uuidutils.generate_uuid())

    def test_destroy_instance_type(self):
        self.dbapi.instance_type_destroy(self.context,
                                         self.instance_type['uuid'])

        self.assertRaises(exception.InstanceTypeNotFound,
                          self.dbapi.instance_type_destroy,
                          self.context,
                          self.instance_type['uuid'])

    def test_destroy_instance_type_that_does_not_exist(self):
        self.assertRaises(exception.InstanceTypeNotFound,
                          self.dbapi.instance_type_destroy,
                          self.context,
                          uuidutils.generate_uuid())
