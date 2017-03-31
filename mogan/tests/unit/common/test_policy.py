# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
from oslo_context import context

from mogan.common import policy
from mogan.tests import base
from mogan.tests.unit.objects import utils


class TestAuthorizeWsgi(base.TestCase):
    def setUp(self):
        super(TestAuthorizeWsgi, self).setUp()
        self.fake_controller = mock.MagicMock()
        self.ctxt = context.RequestContext(
            tenant='c18e8a1a870d4c08a0b51ced6e0b6459',
            user='cdbf77d47f1d4d04ad9b7ff62b672467')
        self.test_inst = utils.get_test_instance(self.ctxt)
        self.fake_controller._get_resource.return_value = self.test_inst

        def power(self, instance_uuid, target):
            pass

        def lock(self, instance_uuid, target):
            pass

        self.fake_power = power
        self.fake_lock = lock

    @mock.patch('pecan.request')
    def test_authorize_power_action_owner(self, mocked_pecan_request):
        mocked_pecan_request.context = self.ctxt

        policy.authorize_wsgi("mogan:instance", "set_power_state")(
            self.fake_power)(self.fake_controller, 'fake_instance_id', 'off')

    @mock.patch('pecan.request')
    def test_authorize_power_action_admin(self, mocked_pecan_request):
        mocked_pecan_request.context = context.get_admin_context()

        policy.authorize_wsgi("mogan:instance", "set_power_state")(
            self.fake_power)(self.fake_controller, 'fake_instance_id', 'off')

    @mock.patch('pecan.response')
    @mock.patch('pecan.request')
    def test_authorize_power_action_failed(self, mocked_pecan_request,
                                           mocked_pecan_response):
        mocked_pecan_request.context = context.RequestContext(
            tenant='non-exist-tenant',
            user='non-exist-user')

        data = policy.authorize_wsgi("mogan:instance", "set_power_state")(
            self.fake_power)(self.fake_controller, 'fake_instance_id',
                             'reboot')
        self.assertEqual(403, mocked_pecan_response.status)
        self.assertEqual('Access was denied to the following resource: '
                         'mogan:instance:set_power_state',
                         data['faultstring'])

    @mock.patch('pecan.request')
    def test_authorize_lock_action_owner(self, mocked_pecan_request):
        mocked_pecan_request.context = self.ctxt

        policy.authorize_wsgi("mogan:instance", "set_lock_state")(
            self.fake_lock)(self.fake_controller, 'fake_instance_id', True)

    @mock.patch('pecan.request')
    def test_authorize_lock_action_admin(self, mocked_pecan_request):
        mocked_pecan_request.context = context.get_admin_context()

        policy.authorize_wsgi("mogan:instance", "set_lock_state")(
            self.fake_lock)(self.fake_controller, 'fake_instance_id', True)

    @mock.patch('pecan.response')
    @mock.patch('pecan.request')
    def test_authorize_lock_action_failed(self, mocked_pecan_request,
                                          mocked_pecan_response):
        mocked_pecan_request.context = context.RequestContext(
            tenant='non-exist-tenant',
            user='non-exist-user')

        data = policy.authorize_wsgi("mogan:instance", "set_lock_state")(
            self.fake_lock)(self.fake_controller, 'fake_instance_id',
                            True)
        self.assertEqual(403, mocked_pecan_response.status)
        self.assertEqual('Access was denied to the following resource: '
                         'mogan:instance:set_lock_state',
                         data['faultstring'])
