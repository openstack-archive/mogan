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

"""Tests for manipulating Server groups via the DB API"""

from mogan.common import exception
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class DbServerGroupTestCase(base.DbTestCase):
    def setUp(self):
        super(DbServerGroupTestCase, self).setUp()
        self.server_group = utils.create_test_server_group(
            context={},
            name='test_server_group',
            user_id='fake_user_id',
            project_id='fake_project_id',
            policies=['policy1', 'policy2'],
            members=['server1', 'server2'])

    def test_server_group_create(self):
        sg = utils.create_test_aggregate(name='testing')
        self.assertEqual('testing', sg.name)

    def test_server_group_get(self):
        server_group = self.dbapi.server_group_get(
            context={}, group_uuid=self.server_group.uuid)
        self.assertEqual('test_server_group', server_group.name)
        self.assertEqual('fake_user_id', server_group.user_id)
        self.assertEqual('fake_project_id', server_group.project_id)
        self.assertItemsEqual(['policy1', 'policy2'], server_group.policies)
        self.assertItemsEqual(['server1', 'server2'], server_group.members)

    def test_server_group_update(self):
        update_values = {'name': 'new_test_name',
                         'policies': ['policy2', 'policy3'],
                         'members': ['server2', 'server3']
                         }
        self.dbapi.server_group_update({}, self.server_group.uuid,
                                       update_values)
        server_group = self.dbapi.server_group_get(
            context={}, group_uuid=self.server_group.uuid)
        self.assertEqual('new_test_name', server_group.name)
        self.assertEqual('fake_user_id', server_group.user_id)
        self.assertEqual('fake_project_id', server_group.project_id)
        self.assertItemsEqual(['policy2', 'policy3'], server_group.policies)
        self.assertItemsEqual(['server2', 'server3'], server_group.members)

    def test_server_group_delete(self):
        self.dbapi.server_group_delete(context={},
                                       group_uuid=self.server_group.uuid)
        self.assertRaises(exception.ServerGroupNotFound,
                          self.dbapi.server_group_get,
                          self.context,
                          self.server_group.uuid)

    def test_server_group_get_all(self):
        server_groups = self.dbapi.server_group_get_all(context={})
        self.assertIsInstance(server_groups, list)
        self.assertEqual(1, len(server_groups))
        self.assertEqual('test_server_group', server_groups[0].name)
        self.assertEqual('fake_user_id', server_groups[0].user_id)
        self.assertEqual('fake_project_id', server_groups[0].project_id)
        self.assertItemsEqual(['policy1', 'policy2'],
                              server_groups[0].policies)
        self.assertItemsEqual(['server1', 'server2'],
                              server_groups[0].members)
