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

"""Tests for manipulating Flavors via the DB API"""

from oslo_utils import uuidutils
import six

from mogan.common import exception
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class DbFlavorTestCase(base.DbTestCase):

    def setUp(self):
        super(DbFlavorTestCase, self).setUp()
        self.context = {}
        self.flavor = utils.create_test_flavor()

    def test_create_flavor(self):
        utils.create_test_flavor(name='testing')

    def test_create_flavor_already_exists(self):
        self.assertRaises(exception.FlavorAlreadyExists,
                          utils.create_test_flavor,
                          uuid=self.flavor['uuid'])

    def test_get_flavor_list(self):
        uuids = [self.flavor['uuid']]
        for i in range(1, 6):
            inst_type = utils.create_test_flavor(
                uuid=uuidutils.generate_uuid(),
                name=six.text_type(i))
            uuids.append(six.text_type(inst_type['uuid']))
        res = self.dbapi.flavor_get_all(self.context)
        res_uuids = [r['uuid'] for r in res]
        six.assertCountEqual(self, uuids, res_uuids)

    def test_get_flavor(self):
        flavor = self.dbapi.flavor_get(
            self.context, self.flavor['uuid'])

        self.assertEqual(self.flavor['uuid'], flavor['uuid'])

    def test_get_flavor_that_does_not_exist(self):
        self.assertRaises(exception.FlavorNotFound,
                          self.dbapi.flavor_get,
                          self.context,
                          uuidutils.generate_uuid())

    def test_destroy_flavor(self):
        self.dbapi.flavor_destroy(self.context, self.flavor['uuid'])

        self.assertRaises(exception.FlavorNotFound,
                          self.dbapi.flavor_destroy,
                          self.context,
                          self.flavor['uuid'])

    def test_destroy_flavor_that_does_not_exist(self):
        self.assertRaises(exception.FlavorNotFound,
                          self.dbapi.flavor_destroy,
                          self.context,
                          uuidutils.generate_uuid())
