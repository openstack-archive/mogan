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

"""Tests for manipulating Flavor Extra Specs via the DB API"""

from mogan.common import exception
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class DbFlavorExtraSpecsTestCase(base.DbTestCase):

    def setUp(self):
        super(DbFlavorExtraSpecsTestCase, self).setUp()
        self.context = {}
        self.flavor = utils.create_test_flavor()
        self.specs = {'k1': 'v1', 'k2': 'v2'}

    def test_create_extra_specs(self):
        self.dbapi.extra_specs_update_or_create(
            self.context, self.flavor['uuid'], self.specs)

    def test_get_extra_specs(self):
        self.dbapi.extra_specs_update_or_create(
            self.context, self.flavor['uuid'], self.specs)
        extra_specs = self.dbapi.flavor_extra_specs_get(
            self.context, self.flavor['uuid'])

        self.assertEqual(self.specs, extra_specs)

    def test_get_extra_specs_empty(self):
        extra_specs = self.dbapi.flavor_extra_specs_get(
            self.context, self.flavor['uuid'])

        self.assertEqual({}, extra_specs)

    def test_destroy_extra_specs(self):
        self.dbapi.extra_specs_update_or_create(
            self.context, self.flavor['uuid'], self.specs)

        self.dbapi.type_extra_specs_delete(
            self.context, self.flavor['uuid'], 'k1')
        extra_specs = self.dbapi.flavor_extra_specs_get(
            self.context, self.flavor['uuid'])

        self.assertEqual({'k2': 'v2'}, extra_specs)

    def test_delete_extra_specs_does_not_exist(self):
        self.dbapi.extra_specs_update_or_create(
            self.context, self.flavor['uuid'], self.specs)
        self.assertRaises(exception.FlavorExtraSpecsNotFound,
                          self.dbapi.type_extra_specs_delete,
                          self.context,
                          self.flavor['uuid'],
                          'k3')
