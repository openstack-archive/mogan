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

from mogan.common import exception
from mogan.engine.baremetal import ironic
from mogan.engine.baremetal import ironic_states
from mogan.engine import manager
from mogan.network import api as network_api
from mogan.tests.unit.db import base as tests_db_base
from mogan.tests.unit.engine import mgr_utils
from mogan.tests.unit.objects import utils as obj_utils

CONF = cfg.CONF


@mock.patch.object(manager.EngineManager, '_refresh_cache')
class ManageInstanceTestCase(mgr_utils.ServiceSetUpMixin,
                             tests_db_base.DbTestCase):

    @mock.patch.object(ironic, 'unplug_vif')
    @mock.patch.object(ironic, 'get_ports_from_node')
    @mock.patch.object(network_api.API, 'delete_port')
    def test_destroy_networks(self, delete_port_mock,
                              get_ports_mock, unplug_vif_mock,
                              refresh_cache_mock):
        instance = obj_utils.create_test_instance(self.context)
        delete_port_mock.side_effect = None
        port = mock.MagicMock()
        port.extra = {'vif_port_id': 'fake-vif'}
        port.uuid = 'fake-uuid'
        get_ports_mock.return_value = [port]
        unplug_vif_mock.side_effect = None
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service.destroy_networks(self.context, instance)
        self._stop_service()

        delete_port_mock.assert_called_once_with(
            self.context, '2ea04c3d-6dc9-4285-836f-3b355008c84e',
            instance.uuid)
        get_ports_mock.assert_called_once_with(
            mock.ANY, instance.node_uuid, detail=True)
        unplug_vif_mock.assert_called_once_with(mock.ANY, 'fake-uuid')

    @mock.patch.object(ironic, 'get_node_by_instance')
    @mock.patch.object(ironic, 'destroy_node')
    def _test__destroy_instance(self, destroy_node_mock,
                                get_node_mock, refresh_cache_mock,
                                state=None):
        fake_node = mock.MagicMock()
        fake_node.provision_state = state
        get_node_mock.return_value = fake_node
        instance = obj_utils.create_test_instance(self.context)
        destroy_node_mock.side_effect = None
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service._destroy_instance(self.context, instance)
        self._stop_service()

        get_node_mock.assert_called_once_with(mock.ANY, instance.uuid)
        destroy_node_mock.assert_called_once_with(mock.ANY, instance.node_uuid)

    def test__destroy_instance_cleaning(self, refresh_cache_mock):
        self._test__destroy_instance(state=ironic_states.CLEANING,
                                     refresh_cache_mock=refresh_cache_mock)

    def test__destroy_instance_cleanwait(self, refresh_cache_mock):
        self._test__destroy_instance(state=ironic_states.CLEANWAIT,
                                     refresh_cache_mock=refresh_cache_mock)

    @mock.patch.object(ironic, 'get_node_by_instance')
    @mock.patch.object(ironic, 'destroy_node')
    def test__destroy_instance_fail_max_retries(self, destroy_node_mock,
                                                get_node_mock,
                                                refresh_cache_mock):
        CONF.set_default('api_max_retries', default=2, group='ironic')
        fake_node = mock.MagicMock()
        fake_node.provision_state = ironic_states.ACTIVE
        get_node_mock.return_value = fake_node
        instance = obj_utils.create_test_instance(self.context)
        destroy_node_mock.side_effect = None
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.assertRaises(exception.MoganException,
                          self.service._destroy_instance,
                          self.context, instance)
        self._stop_service()

        self.assertTrue(get_node_mock.called)
        destroy_node_mock.assert_called_once_with(mock.ANY, instance.node_uuid)

    @mock.patch.object(ironic, 'get_node_by_instance')
    @mock.patch.object(manager.EngineManager, '_destroy_instance')
    @mock.patch.object(manager.EngineManager, 'destroy_networks')
    def test_delete_instance(self, destroy_net_mock,
                             destroy_inst_mock, get_node_mock,
                             refresh_cache_mock):
        fake_node = mock.MagicMock()
        fake_node.provision_state = ironic_states.ACTIVE
        instance = obj_utils.create_test_instance(self.context)
        destroy_net_mock.side_effect = None
        destroy_inst_mock.side_effect = None
        refresh_cache_mock.side_effect = None
        get_node_mock.return_value = fake_node
        self._start_service()

        self.service.delete_instance(self.context, instance)
        self._stop_service()

        destroy_net_mock.assert_called_once_with(mock.ANY, instance)
        destroy_inst_mock.assert_called_once_with(mock.ANY, instance)
        get_node_mock.assert_called_once_with(mock.ANY, instance.uuid)

    @mock.patch.object(ironic, 'get_node_by_instance')
    @mock.patch.object(manager.EngineManager, '_destroy_instance')
    def test_delete_instance_without_node_destroy(
            self, destroy_inst_mock, get_node_mock, refresh_cache_mock):
        fake_node = mock.MagicMock()
        fake_node.provision_state = 'foo'
        instance = obj_utils.create_test_instance(self.context)
        destroy_inst_mock.side_effect = None
        refresh_cache_mock.side_effect = None
        get_node_mock.return_value = fake_node
        self._start_service()

        self.service.delete_instance(self.context, instance)
        self._stop_service()

        self.assertFalse(destroy_inst_mock.called)

    @mock.patch.object(ironic, 'get_node_by_instance')
    @mock.patch.object(ironic, 'set_power_state')
    def test_change_instance_power_state(
            self, set_power_mock, get_node_mock, refresh_cache_mock):
        instance = obj_utils.create_test_instance(self.context)
        fake_node = mock.MagicMock()
        fake_node.target_power_state = ironic_states.NOSTATE
        get_node_mock.return_value = fake_node
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service.set_power_state(self.context, instance,
                                     ironic_states.POWER_ON)
        self._stop_service()

        set_power_mock.assert_called_once_with(mock.ANY, instance.node_uuid,
                                               ironic_states.POWER_ON)
        get_node_mock.assert_called_once_with(mock.ANY, instance.uuid)

    @mock.patch.object(ironic, 'get_node_states')
    def test_get_instance_states(self, get_states_mock, refresh_cache_mock):
        instance = obj_utils.create_test_instance(self.context)
        get_states_mock.return_value = mock.MagicMock()
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service.instance_states(self.context, instance)
        self._stop_service()

        get_states_mock.assert_called_once_with(mock.ANY, instance.node_uuid)

    @mock.patch.object(ironic, 'get_node_by_instance')
    def test_get_ironic_node(self, get_node_mock, refresh_cache_mock):
        instance = obj_utils.create_test_instance(self.context)
        get_node_mock.return_value = mock.MagicMock()
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service.get_ironic_node(self.context, instance.uuid, [])
        self._stop_service()

        get_node_mock.assert_called_once_with(mock.ANY, instance.uuid, [])

    @mock.patch.object(ironic, 'get_node_list')
    def test_get_ironic_node_list(self, get_node_list_mock,
                                  refresh_cache_mock):
        get_node_list_mock.return_value = mock.MagicMock()
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service.get_ironic_node_list(self.context, [])
        self._stop_service()

        get_node_list_mock.assert_called_once_with(mock.ANY, associated=True,
                                                   limit=0, fields=[])

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
