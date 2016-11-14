# Copyright 2016 Intel
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

"""Tests for manipulating Instances via the DB API"""

from oslo_utils import uuidutils
import six

from nimble.common import exception
from nimble.tests.unit.db import base
from nimble.tests.unit.db import utils


class DbInstanceTestCase(base.DbTestCase):

    def test_instance_create(self):
        utils.create_test_instance()

    def test_instance_create_already_exist(self):
        utils.create_test_instance()
        self.assertRaises(exception.InstanceAlreadyExists,
                          utils.create_test_instance)

    def test_instance_get_by_uuid(self):
        instance = utils.create_test_instance()
        res = self.dbapi.instance_get(self.context, instance.uuid)
        self.assertEqual(instance.id, res.id)
        self.assertEqual(instance.uuid, res.uuid)

    def test_instance_get_not_exist(self):
        self.assertRaises(exception.InstanceNotFound,
                          self.dbapi.instance_get,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_instance_get_all(self):
        uuids = []
        for i in range(1, 6):
            instance = utils.create_test_instance(
                uuid=uuidutils.generate_uuid())
            uuids.append(six.text_type(instance['uuid']))
        res = self.dbapi.instance_get_all(self.context, project_only=False)
        res_uuids = [r.uuid for r in res]
        six.assertCountEqual(self, uuids, res_uuids)

    def test_instance_destroy(self):
        instance = utils.create_test_instance()
        self.dbapi.instance_destroy(self.context, instance.uuid)
        self.assertRaises(exception.InstanceNotFound,
                          self.dbapi.instance_get,
                          self.context,
                          instance.uuid)

    def test_instance_destroy_not_exist(self):
        self.assertRaises(exception.InstanceNotFound,
                          self.dbapi.instance_destroy,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_instance_update(self):
        instance = utils.create_test_instance()
        old_extra = instance.extra
        new_extra = {'foo': 'bar'}
        self.assertNotEqual(old_extra, new_extra)

        res = self.dbapi.instance_update(self.context,
                                         instance.id,
                                         {'extra': new_extra})
        self.assertEqual(new_extra, res.extra)

    def test_instance_update_with_invalid_parameter_value(self):
        instance = utils.create_test_instance()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.instance_update,
                          self.context,
                          instance.id,
                          {'uuid': '12345678-9999-0000-aaaa-123456789012'})

    def test_instance_update_with_duplicate_name(self):
        instance1 = utils.create_test_instance(uuid=uuidutils.generate_uuid(),
                                               name='spam')
        instance2 = utils.create_test_instance(uuid=uuidutils.generate_uuid())
        self.assertRaises(exception.DuplicateName,
                          self.dbapi.instance_update,
                          self.context,
                          instance2.id,
                          {'name': 'spam'})
