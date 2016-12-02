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

"""Test class for Nimble ManagerService."""

import mock

from nimble.engine.baremetal import ironic
from nimble.engine.baremetal import ironic_states
from nimble.tests.unit.db import base as tests_db_base
from nimble.tests.unit.engine import mgr_utils
from nimble.tests.unit.objects import utils as obj_utils


class ManageInstanceTestCase(mgr_utils.ServiceSetUpMixin,
                             tests_db_base.DbTestCase):

    @mock.patch.object(ironic, 'set_power_state')
    def test_change_instance_power_state(self, set_power_mock):
        instance = obj_utils.create_test_instance(self.context)
        self._start_service()

        self.service.set_power_state(self.context, instance,
                                     ironic_states.POWER_ON)
        self._stop_service()

        set_power_mock.assert_called_once_with(mock.ANY, instance.node_uuid,
                                               ironic_states.POWER_ON)

    @mock.patch.object(ironic, 'get_node_states')
    def test_get_instance__states(self, get_states_mock):
        instance = obj_utils.create_test_instance(self.context)
        get_states_mock.return_value = mock.MagicMock()
        self._start_service()

        self.service.instance_states(self.context, instance)
        self._stop_service()

        get_states_mock.assert_called_once_with(mock.ANY, instance.node_uuid)
