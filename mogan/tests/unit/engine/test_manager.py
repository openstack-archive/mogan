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

"""Test class for Mogan ManagerService."""

import mock
from oslo_config import cfg
from oslo_utils import uuidutils

from mogan.common import ironic
from mogan.common import states
from mogan.engine.baremetal.ironic.driver import ironic_states
from mogan.engine.baremetal.ironic import IronicDriver
from mogan.engine import manager
from mogan.network import api as network_api
from mogan.tests.unit.db import base as tests_db_base
from mogan.tests.unit.engine import mgr_utils
from mogan.tests.unit.objects import utils as obj_utils

CONF = cfg.CONF


@mock.patch.object(manager.EngineManager, '_refresh_cache')
class ManageInstanceTestCase(mgr_utils.ServiceSetUpMixin,
                             tests_db_base.DbTestCase):

    @mock.patch.object(network_api.API, 'delete_port')
    def test_destroy_networks(self, delete_port_mock,
                              refresh_cache_mock):
        instance = obj_utils.create_test_instance(self.context)
        inst_port_id = instance.nics[0].port_id
        delete_port_mock.side_effect = None
        port = mock.MagicMock()
        port.extra = {'vif_port_id': 'fake-vif'}
        port.uuid = 'fake-uuid'
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service.destroy_networks(self.context, instance)
        self._stop_service()

        delete_port_mock.assert_called_once_with(
            self.context, inst_port_id, instance.uuid)

    @mock.patch.object(IronicDriver, 'destroy')
    def _test__delete_instance(self, destroy_node_mock,
                               refresh_cache_mock, state=None):
        fake_node = mock.MagicMock()
        fake_node.provision_state = state
        instance = obj_utils.create_test_instance(self.context)
        destroy_node_mock.side_effect = None
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service._delete_instance(self.context, instance)
        self._stop_service()

        destroy_node_mock.assert_called_once_with(self.context, instance)

    def test__delete_instance_cleaning(self, refresh_cache_mock):
        self._test__delete_instance(state=ironic_states.CLEANING,
                                    refresh_cache_mock=refresh_cache_mock)

    def test__delete_instance_cleanwait(self, refresh_cache_mock):
        self._test__delete_instance(state=ironic_states.CLEANWAIT,
                                    refresh_cache_mock=refresh_cache_mock)

    @mock.patch.object(manager.EngineManager, '_delete_instance')
    @mock.patch.object(manager.EngineManager, '_unplug_vifs')
    def test_delete_instance(self, unplug_mock,
                             delete_inst_mock, refresh_cache_mock):
        fake_node = mock.MagicMock()
        fake_node.provision_state = ironic_states.ACTIVE
        instance = obj_utils.create_test_instance(
            self.context, status=states.DELETING)
        unplug_mock.side_effect = None
        delete_inst_mock.side_effect = None
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service.delete_instance(self.context, instance)
        self._stop_service()

        unplug_mock.assert_called_once_with(mock.ANY, instance)
        delete_inst_mock.assert_called_once_with(mock.ANY, instance)

    @mock.patch.object(IronicDriver, 'get_power_state')
    @mock.patch.object(IronicDriver, 'set_power_state')
    def test_change_instance_power_state(
            self, set_power_mock, get_power_mock,
            refresh_cache_mock):
        instance = obj_utils.create_test_instance(
            self.context, status=states.POWERING_ON)
        fake_node = mock.MagicMock()
        fake_node.target_power_state = ironic_states.NOSTATE
        get_power_mock.return_value = states.POWER_ON
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service.set_power_state(self.context, instance,
                                     ironic_states.POWER_ON)
        self._stop_service()

        set_power_mock.assert_called_once_with(self.context,
                                               instance,
                                               ironic_states.POWER_ON)
        get_power_mock.assert_called_once_with(self.context, instance.uuid)

    def test_list_availability_zone(self, refresh_cache_mock):
        refresh_cache_mock.side_effect = None
        node1 = mock.MagicMock()
        node2 = mock.MagicMock()
        node3 = mock.MagicMock()
        node1.properties = {'availability_zone': 'az1'}
        node2.properties = {'availability_zone': 'az2'}
        node3.properties = {'availability_zone': 'az1'}

        self._start_service()
        self.service.node_cache = {'node1_id': node1,
                                   'node2_id': node2,
                                   'node3_id': node3}
        azs = self.service.list_availability_zones(self.context)
        self._stop_service()

        self.assertItemsEqual(['az1', 'az2'], azs['availability_zones'])

    @mock.patch.object(ironic.IronicClientWrapper, 'call')
    def test_get_console(self, mock_ironic_call, refresh_cache_mock):
        fake_node = mock.MagicMock()
        fake_node.uuid = uuidutils.generate_uuid()
        fake_console_url = {
            "url": "http://localhost:4321", "type": "shellinabox"}
        mock_ironic_call.side_effect = [
            fake_node,
            {"console_enabled": True, "console_info": fake_console_url},
            mock.MagicMock(),
            {"console_enabled": False, "console_info": fake_console_url},
            mock.MagicMock(),
            {"console_enabled": True, "console_info": fake_console_url}]
        refresh_cache_mock.side_effect = None
        self._start_service()
        console = self.service.get_console(self.context, 'fake-instance-uuid')
        self._stop_service()
        self.assertEqual(4321, console['port'])
        self.assertTrue(
            console['access_url'].startswith('http://127.0.0.1:8866/?token='))
        self.assertEqual('localhost', console['host'])
        self.assertIn('token', console)
