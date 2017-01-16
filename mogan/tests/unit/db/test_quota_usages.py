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
        self.instance = quota.InstanceResource()
        self.resources = {self.instance.name: self.instance}

    def test_quota_usage_reserve(self):
        utils.create_test_quota()
        dbapi = db_api.get_instance()
        r = dbapi.quota_reserve(self.context, self.resources,
                                {'instances': 10},
                                {'instances': 1},
                                datetime.datetime(2099, 1, 1, 0, 0),
                                CONF.api.until_refresh, CONF.api.max_age,
                                project_id="c18e8a1a870d4c08a0b51ced6e0b6459")
        self.assertEqual('instances', r.resource_name)
