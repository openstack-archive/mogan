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

"""Tests for manipulating Instance Type Extra Specs via the DB API"""

from nimble.common import exception
from nimble.tests.unit.db import base
from nimble.tests.unit.db import utils


class DbInstanceTypeExtraSpecsTestCase(base.DbTestCase):

    def setUp(self):
        super(DbInstanceTypeExtraSpecsTestCase, self).setUp()
        self.context = {}
        self.instance_type = utils.create_test_instance_type()
        self.specs = {'k1': 'v1', 'k2': 'v2'}

    def test_create_extra_specs(self):
        self.dbapi.extra_specs_update_or_create(
            self.context, self.instance_type['uuid'], self.specs)

    def test_get_extra_specs(self):
        self.dbapi.extra_specs_update_or_create(
            self.context, self.instance_type['uuid'], self.specs)
        extra_specs = self.dbapi.instance_type_extra_specs_get(
            self.context, self.instance_type['uuid'])

        self.assertEqual(self.specs, extra_specs)

    def test_get_extra_specs_empty(self):
        extra_specs = self.dbapi.instance_type_extra_specs_get(
            self.context, self.instance_type['uuid'])

        self.assertEqual({}, extra_specs)

    def test_destroy_extra_specs(self):
        self.dbapi.extra_specs_update_or_create(
            self.context, self.instance_type['uuid'], self.specs)

        self.dbapi.type_extra_specs_delete(
            self.context, self.instance_type['uuid'], 'k1')
        extra_specs = self.dbapi.instance_type_extra_specs_get(
            self.context, self.instance_type['uuid'])

        self.assertEqual({'k2': 'v2'}, extra_specs)

    def test_delete_extra_specs_does_not_exist(self):
        self.dbapi.extra_specs_update_or_create(
            self.context, self.instance_type['uuid'], self.specs)
        self.assertRaises(exception.InstanceTypeExtraSpecsNotFound,
                          self.dbapi.type_extra_specs_delete,
                          self.context,
                          self.instance_type['uuid'],
                          'k3')
