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

from mogan.common import states
from mogan.engine.baremetal.ironic.driver import ironic_states
from mogan.engine.baremetal.ironic import IronicDriver
from mogan.engine import manager
from mogan.network import api as network_api
from mogan.tests.unit.db import base as tests_db_base
from mogan.tests.unit.engine import mgr_utils
from mogan.tests.unit.objects import utils as obj_utils

CONF = cfg.CONF


class ManageInstanceTestCase(mgr_utils.ServiceSetUpMixin,
                             tests_db_base.DbTestCase):

    @mock.patch.object(network_api.API, 'delete_port')
    def test_destroy_networks(self, delete_port_mock):
        instance = obj_utils.create_test_instance(self.context)
        inst_port_id = instance.nics[0].port_id
        delete_port_mock.side_effect = None
        port = mock.MagicMock()
        port.extra = {'vif_port_id': 'fake-vif'}
        port.uuid = 'fake-uuid'
        self._start_service()

        self.service.destroy_networks(self.context, instance)
        self._stop_service()

        delete_port_mock.assert_called_once_with(
            self.context, inst_port_id, instance.uuid)

    @mock.patch.object(IronicDriver, 'destroy')
    @mock.patch.object(IronicDriver, 'unplug_vifs')
    @mock.patch.object(manager.EngineManager, 'destroy_networks')
    def _test__delete_instance(self, destroy_networks_mock, unplug_mock,
                               destroy_node_mock, state=None):
        fake_node = mock.MagicMock()
        fake_node.provision_state = state
        instance = obj_utils.create_test_instance(self.context)
        destroy_networks_mock.side_effect = None
        unplug_mock.side_effect = None
        destroy_node_mock.side_effect = None
        self._start_service()

        self.service._delete_instance(self.context, instance)
        self._stop_service()

        destroy_networks_mock.assert_called_once_with(self.context, instance)
        unplug_mock.assert_called_once_with(self.context, instance)
        destroy_node_mock.assert_called_once_with(self.context, instance)

    def test__delete_instance_cleaning(self):
        self._test__delete_instance(state=ironic_states.CLEANING)

    def test__delete_instance_cleanwait(self):
        self._test__delete_instance(state=ironic_states.CLEANWAIT)

    @mock.patch.object(manager.EngineManager, '_delete_instance')
    def test_delete_instance(self, delete_inst_mock):
        fake_node = mock.MagicMock()
        fake_node.provision_state = ironic_states.ACTIVE
        instance = obj_utils.create_test_instance(
            self.context, status=states.DELETING)
        delete_inst_mock.side_effect = None
        self._start_service()

        self.service.delete_instance(self.context, instance)
        self._stop_service()

        delete_inst_mock.assert_called_once_with(mock.ANY, instance)

    @mock.patch.object(manager.EngineManager, '_delete_instance')
    def test_delete_instance_unassociated(self, delete_inst_mock):
        fake_node = mock.MagicMock()
        fake_node.provision_state = ironic_states.ACTIVE
        instance = obj_utils.create_test_instance(
            self.context, status=states.DELETING, node_uuid=None)
        self._start_service()

        self.service.delete_instance(self.context, instance)
        self._stop_service()

        delete_inst_mock.assert_not_called()

    @mock.patch.object(IronicDriver, 'get_power_state')
    @mock.patch.object(IronicDriver, 'set_power_state')
    def test_change_instance_power_state(
            self, set_power_mock, get_power_mock):
        instance = obj_utils.create_test_instance(
            self.context, status=states.POWERING_ON)
        fake_node = mock.MagicMock()
        fake_node.target_power_state = ironic_states.NOSTATE
        get_power_mock.return_value = states.POWER_ON
        self._start_service()

        self.service.set_power_state(self.context, instance,
                                     ironic_states.POWER_ON)
        self._stop_service()

        set_power_mock.assert_called_once_with(self.context,
                                               instance,
                                               ironic_states.POWER_ON)
        get_power_mock.assert_called_once_with(self.context, instance.uuid)

    def test_list_availability_zone(self):
        uuid1 = uuidutils.generate_uuid()
        uuid2 = uuidutils.generate_uuid()
        obj_utils.create_test_compute_node(
            self.context, availability_zone='az1')
        obj_utils.create_test_compute_node(
            self.context, node_uuid=uuid1, availability_zone='az2')
        obj_utils.create_test_compute_node(
            self.context, node_uuid=uuid2, availability_zone='az1')

        self._start_service()
        azs = self.service.list_availability_zones(self.context)
        self._stop_service()

        self.assertItemsEqual(['az1', 'az2'], azs['availability_zones'])
