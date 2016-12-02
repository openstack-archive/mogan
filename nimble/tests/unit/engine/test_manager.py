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
from oslo_service import loopingcall

from nimble.common import neutron
from nimble.engine.baremetal import ironic
from nimble.engine.baremetal import ironic_states
from nimble.engine import manager
from nimble.engine.scheduler import filter_scheduler as scheduler
from nimble import objects
from nimble.tests.unit.db import base as tests_db_base
from nimble.tests.unit.db import utils as db_utils
from nimble.tests.unit.engine import mgr_utils
from nimble.tests.unit.objects import utils as obj_utils


@mock.patch.object(manager.EngineManager, '_refresh_cache')
class ManageInstanceTestCase(mgr_utils.ServiceSetUpMixin,
                             tests_db_base.DbTestCase):

    @mock.patch.object(manager.EngineManager, '_wait_for_active')
    @mock.patch.object(ironic, 'do_node_deploy')
    def test__build_instance(self, deploy_node_mock, wait_mock,
                             refresh_cache_mock):
        instance = obj_utils.create_test_instance(self.context)
        deploy_node_mock.side_effect = None
        wait_mock.side_effect = loopingcall.LoopingCallDone()
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service._build_instance(self.context, instance)
        self._stop_service()

        deploy_node_mock.assert_called_once_with(mock.ANY, instance.node_uuid)

    @mock.patch.object(manager.EngineManager, '_build_instance')
    @mock.patch.object(manager.EngineManager, '_build_networks')
    @mock.patch.object(ironic, 'validate_node')
    @mock.patch.object(ironic, 'set_instance_info')
    @mock.patch.object(scheduler.FilterScheduler, 'schedule')
    def test_create_instance(self, schedule_mock, set_inst_mock,
                             validate_mock, build_net_mock,
                             build_inst_mock, refresh_cache_mock):
        instance = obj_utils.create_test_instance(self.context)
        fake_type = db_utils.get_test_instance_type(context=self.context)
        fake_type['extra_specs'] = {}
        inst_type = objects.InstanceType(self.context, **fake_type)
        schedule_mock.side_effect = None
        set_inst_mock.side_effect = None
        validate_mock.side_effect = None
        build_net_mock.side_effect = None
        build_inst_mock.side_effect = None
        refresh_cache_mock.side_effect = None
        requested_net = [{'uuid': 'fake-net-uuid'}]

        self._start_service()
        self.service.create_instance(self.context, instance,
                                     requested_net, inst_type)
        self._stop_service()

        set_inst_mock.assert_called_once_with(mock.ANY, instance)
        validate_mock.assert_called_once_with(mock.ANY, instance.node_uuid)
        build_net_mock.assert_called_once_with(self.context, instance,
                                               requested_net)
        build_inst_mock.assert_called_once_with(self.context, instance)

    @mock.patch.object(ironic, 'unplug_vif')
    @mock.patch.object(ironic, 'get_ports_from_node')
    @mock.patch.object(neutron, 'delete_port')
    def test__destroy_networks(self, delete_port_mock,
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

        self.service._destroy_networks(self.context, instance)
        self._stop_service()

        delete_port_mock.assert_called_once_with(
            self.context, '2ea04c3d-6dc9-4285-836f-3b355008c84e',
            instance.uuid)
        get_ports_mock.assert_called_once_with(
            mock.ANY, instance.node_uuid, detail=True)
        unplug_vif_mock.assert_called_once_with(mock.ANY, 'fake-uuid')

    @mock.patch.object(ironic, 'destroy_node')
    def test__destroy_instance(self, destroy_node_mock,
                               refresh_cache_mock):
        instance = obj_utils.create_test_instance(self.context)
        destroy_node_mock.side_effect = None
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service._destroy_instance(self.context, instance)
        self._stop_service()

        destroy_node_mock.assert_called_once_with(mock.ANY, instance.node_uuid)

    @mock.patch.object(manager.EngineManager, '_destroy_instance')
    @mock.patch.object(manager.EngineManager, '_destroy_networks')
    def test_delete_instance(self, destroy_net_mock,
                             destroy_inst_mock, refresh_cache_mock):
        instance = obj_utils.create_test_instance(self.context)
        destroy_net_mock.side_effect = None
        destroy_inst_mock.side_effect = None
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service.delete_instance(self.context, instance)
        self._stop_service()

        destroy_net_mock.assert_called_once_with(mock.ANY, instance)
        destroy_inst_mock.assert_called_once_with(mock.ANY, instance)

    @mock.patch.object(ironic, 'set_power_state')
    def test_change_instance_power_state(self, set_power_mock,
                                         refresh_cache_mock):
        instance = obj_utils.create_test_instance(self.context)
        refresh_cache_mock.side_effect = None
        self._start_service()

        self.service.set_power_state(self.context, instance,
                                     ironic_states.POWER_ON)
        self._stop_service()

        set_power_mock.assert_called_once_with(mock.ANY, instance.node_uuid,
                                               ironic_states.POWER_ON)

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
        self.service.node_cache = [node1, node2, node3]
        azs = self.service.list_availability_zones(self.context)
        self._stop_service()

        self.assertItemsEqual(['az1', 'az2'], azs['availability_zones'])
