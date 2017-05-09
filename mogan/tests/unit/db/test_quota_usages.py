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

"""Tests for manipulating QuotaUsages via the DB API"""

import datetime

from oslo_config import cfg
from oslo_context import context

from mogan.db import api as db_api
from mogan.objects import quota
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils


CONF = cfg.CONF


class DbQuotaUsageTestCase(base.DbTestCase):

    def setUp(self):
        super(DbQuotaUsageTestCase, self).setUp()
        self.context = context.get_admin_context()
        self.server = quota.ServerResource()
        self.resources = {self.server.name: self.server}
        self.project_id = "c18e8a1a870d4c08a0b51ced6e0b6459"

    def test_quota_usage_reserve(self):
        utils.create_test_quota()
        dbapi = db_api.get_instance()
        r = dbapi.quota_reserve(self.context, self.resources,
                                {'servers': 10},
                                {'servers': 1},
                                datetime.datetime(2099, 1, 1, 0, 0),
                                CONF.quota.until_refresh, CONF.quota.max_age,
                                project_id=self.project_id)
        self.assertEqual('servers', r[0].resource_name)

    def test_reserve_commit(self):
        utils.create_test_quota()
        dbapi = db_api.get_instance()
        rs = dbapi.quota_reserve(self.context, self.resources,
                                 {'servers': 10},
                                 {'servers': 1},
                                 datetime.datetime(2099, 1, 1, 0, 0),
                                 CONF.quota.until_refresh, CONF.quota.max_age,
                                 project_id=self.project_id)
        r = dbapi.quota_usage_get_all_by_project(self.context, self.project_id)
        before_in_use = r['servers']['in_use']
        dbapi.reservation_commit(self.context, rs, self.project_id)
        r = dbapi.quota_usage_get_all_by_project(self.context, self.project_id)
        after_in_use = r['servers']['in_use']
        self.assertEqual(before_in_use + 1, after_in_use)

    def test_reserve_rollback(self):
        utils.create_test_quota()
        dbapi = db_api.get_instance()
        rs = dbapi.quota_reserve(self.context, self.resources,
                                 {'servers': 10},
                                 {'servers': 1},
                                 datetime.datetime(2099, 1, 1, 0, 0),
                                 CONF.quota.until_refresh, CONF.quota.max_age,
                                 project_id=self.project_id)
        r = dbapi.quota_usage_get_all_by_project(self.context, self.project_id)
        before_in_use = r['servers']['in_use']
        dbapi.reservation_rollback(self.context, rs, self.project_id)
        r = dbapi.quota_usage_get_all_by_project(self.context, self.project_id)
        after_in_use = r['servers']['in_use']
        self.assertEqual(before_in_use, after_in_use)
