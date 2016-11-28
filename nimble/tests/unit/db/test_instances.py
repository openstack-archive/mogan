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

    def test_instance_create_with_same_uuid(self):
        utils.create_test_instance(uuid='uuid', name='instance1')
        self.assertRaises(exception.InstanceAlreadyExists,
                          utils.create_test_instance,
                          uuid='uuid',
                          name='instance2')

    def test_instance_get_by_uuid(self):
        instance = utils.create_test_instance()
        res = self.dbapi.instance_get(self.context, instance.uuid)
        self.assertEqual(instance.uuid, res.uuid)

    def test_instance_get_not_exist(self):
        self.assertRaises(exception.InstanceNotFound,
                          self.dbapi.instance_get,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_instance_get_all(self):
        uuids_project_1 = []
        uuids_project_2 = []
        uuids_project_all = []
        for i in range(0, 3):
            instance = utils.create_test_instance(
                uuid=uuidutils.generate_uuid(),
                project_id='project_1',
                name=str(i))
            uuids_project_1.append(six.text_type(instance['uuid']))
        for i in range(3, 5):
            instance = utils.create_test_instance(
                uuid=uuidutils.generate_uuid(),
                project_id='project_2',
                name=str(i))
            uuids_project_2.append(six.text_type(instance['uuid']))
        uuids_project_all.extend(uuids_project_1)
        uuids_project_all.extend(uuids_project_2)

        # Set project_only to False
        # get all instances from all projects
        res = self.dbapi.instance_get_all(self.context, project_only=False)
        res_uuids = [r.uuid for r in res]
        six.assertCountEqual(self, uuids_project_all, res_uuids)

        # Set project_only to True
        # get instances from current project (project_1)
        self.context.project_id = 'project_1'
        res = self.dbapi.instance_get_all(self.context, project_only=True)
        res_uuids = [r.uuid for r in res]
        six.assertCountEqual(self, uuids_project_1, res_uuids)

        # Set project_only to True
        # get instances from current project (project_2)
        self.context.project_id = 'project_2'
        res = self.dbapi.instance_get_all(self.context, project_only=True)
        res_uuids = [r.uuid for r in res]
        six.assertCountEqual(self, uuids_project_2, res_uuids)

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
                                         instance.uuid,
                                         {'extra': new_extra})
        self.assertEqual(new_extra, res.extra)

    def test_instance_update_with_invalid_parameter_value(self):
        instance = utils.create_test_instance()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.instance_update,
                          self.context,
                          instance.uuid,
                          {'uuid': '12345678-9999-0000-aaaa-123456789012'})
