# Copyright 2018 FiberHome Telecommunication Technologies CO.,LTD
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

"""Tests for manipulating Quotas via the DB API"""

import six

from mogan.common import exception
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


class DbQuotaTestCase(base.DbTestCase):

    def test_quota_create(self):
        utils.create_test_quota()

    def test_quota_get_by_project_id_and_resource_name(self):
        quota = utils.create_test_quota()
        res = self.dbapi.quota_get(self.context, quota.project_id,
                                   quota.resource_name)
        self.assertEqual(quota.id, res.id)

    def test_quota_get_not_exist(self):
        self.assertRaises(exception.QuotaNotFound,
                          self.dbapi.quota_get,
                          self.context,
                          '123', 'fake')

    def test_quota_get_all(self):
        ids_project_1 = []
        ids_project_2 = []
        ids_project_all = []
        resource_names = ['instances', 'instances_type', 'test_resource']
        for i in range(0, 3):
            quota = utils.create_test_quota(
                project_id='project_1',
                resource_name=resource_names[i])
            ids_project_1.append(quota['id'])
        for i in range(3, 5):
            quota = utils.create_test_quota(
                project_id='project_2',
                resource_name=resource_names[i-3])
            ids_project_2.append(quota['id'])
        ids_project_all.extend(ids_project_1)
        ids_project_all.extend(ids_project_2)

        # Set project_only to False
        # get all quotas from all projects
        res = self.dbapi.quota_get_all(self.context, project_only=False)
        res_ids = [r.id for r in res]
        six.assertCountEqual(self, ids_project_all, res_ids)

        # Set project_only to True
        # get quotas from current project (project_1)
        self.context.tenant = 'project_1'
        res = self.dbapi.quota_get_all(self.context, project_only=True)
        res_ids = [r.id for r in res]
        six.assertCountEqual(self, ids_project_1, res_ids)

        # Set project_only to True
        # get quotas from current project (project_2)
        self.context.tenant = 'project_2'
        res = self.dbapi.quota_get_all(self.context, project_only=True)
        res_ids = [r.id for r in res]
        six.assertCountEqual(self, ids_project_2, res_ids)

    def test_quota_destroy(self):
        quota = utils.create_test_quota()
        self.dbapi.quota_destroy(self.context, quota.project_id,
                                 quota.resource_name)
        self.assertRaises(exception.QuotaNotFound,
                          self.dbapi.quota_get,
                          self.context,
                          quota.project_id,
                          quota.resource_name)

    def test_quota_destroy_not_exist(self):
        self.assertRaises(exception.QuotaNotFound,
                          self.dbapi.quota_destroy,
                          self.context,
                          '123', 'fake')

    def test_quota_update(self):
        quota = utils.create_test_quota()
        old_limit = quota.hard_limit
        new_limit = 100
        self.assertNotEqual(old_limit, new_limit)

        res = self.dbapi.quota_update(self.context,
                                      quota.project_id,
                                      quota.resource_name,
                                      {'hard_limit': new_limit})
        self.assertEqual(new_limit, res.hard_limit)

    def test_quota_update_with_invalid_parameter_value(self):
        quota = utils.create_test_quota()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.quota_update,
                          self.context,
                          quota.project_id,
                          quota.resource_name,
                          {'resource_name': 'instance_test'})
