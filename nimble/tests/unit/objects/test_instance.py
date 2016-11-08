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

import mock

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

    def test_get(self):
        uuid = self.fake_instance['uuid']
        with mock.patch.object(self.dbapi, 'instance_get',
                               autospec=True) as mock_instance_get:
            mock_instance_get.return_value = self.fake_instance

            instance = objects.Instance.get(self.context, uuid)

            mock_instance_get.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, instance._context)
