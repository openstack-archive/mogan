# coding=utf-8
#
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

from nimble.common import context
from nimble import objects
from nimble.tests.unit.db import base
from nimble.tests.unit.db import utils
from nimble.tests.unit.objects import utils as obj_utils


class TestInstanceObject(base.DbTestCase):

    def setUp(self):
        super(TestInstanceObject, self).setUp()
        self.ctxt = context.get_admin_context()
        self.fake_instance = utils.get_test_instance(context=self.ctxt)
        self.instance = obj_utils.get_test_instance(
            self.ctxt, **self.fake_instance)
        self.instance.create()
        # These three fields are update by sqlalchemy automatically.
        # So we ignore these fields check.
        self.ignore_fields = ["created_at", "launched_at", "updated_at"]

    def test_get(self):
        uuid = self.fake_instance['uuid']
        instance = objects.Instance.get(self.context, uuid)
        self.assertEqual(self.context, instance._context)
        ignore = dict([(k, getattr(instance, k)) for k in self.ignore_fields])
        fake_instance = self.fake_instance.copy()
        fake_instance.update(ignore)
        self.assertDictEqual(instance.as_dict(), fake_instance)
