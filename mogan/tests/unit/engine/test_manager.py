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

from mogan.baremetal.ironic.driver import ironic_states
from mogan.baremetal.ironic import IronicDriver
from mogan.common import exception
from mogan.common import ironic
from mogan.common import states
from mogan.common import utils
from mogan.engine import manager
from mogan.network import api as network_api
from mogan.notifications import base as notifications
from mogan.objects import fields
from mogan.tests.unit.db import base as tests_db_base
from mogan.tests.unit.engine import mgr_utils
from mogan.tests.unit.objects import utils as obj_utils

CONF = cfg.CONF


class ManageServerTestCase(mgr_utils.ServiceSetUpMixin,
                           tests_db_base.DbTestCase):

    @mock.patch.object(network_api.API, 'delete_port')
    def test_destroy_networks(self, delete_port_mock):
        server = obj_utils.create_test_server(self.context)
        server_port_id = server.nics[0].port_id
        delete_port_mock.side_effect = None
        port = mock.MagicMock()
        port.extra = {'vif_port_id': 'fake-vif'}
        port.uuid = 'fake-uuid'
        self._start_service()

        self.service.destroy_networks(self.context, server)
        self._stop_service()

        delete_port_mock.assert_called_once_with(
            self.context, server_port_id, server.uuid)

    @mock.patch.object(IronicDriver, 'destroy')
    @mock.patch.object(IronicDriver, 'unplug_vif')
    @mock.patch.object(manager.EngineManager, 'destroy_networks')
    def _test__delete_server(self, destroy_networks_mock, unplug_mock,
                             destroy_node_mock, state=None):
        fake_node = mock.MagicMock()
        fake_node.provision_state = state
        server = obj_utils.create_test_server(self.context)
        destroy_networks_mock.side_effect = None
        unplug_mock.side_effect = None
        destroy_node_mock.side_effect = None
        self._start_service()

        self.service._delete_server(self.context, server)
        self._stop_service()

        destroy_networks_mock.assert_called_once_with(self.context, server)
        self.assertEqual(unplug_mock.call_count, len(server.nics))
        destroy_node_mock.assert_called_once_with(self.context, server)

    def test__delete_server_cleaning(self):
        self._test__delete_server(state=ironic_states.CLEANING)

    def test__delete_server_cleanwait(self):
        self._test__delete_server(state=ironic_states.CLEANWAIT)

    @mock.patch.object(manager.EngineManager, '_delete_server')
    def test_delete_server(self, delete_server_mock):
        fake_node = mock.MagicMock()
        fake_node.provision_state = ironic_states.ACTIVE
        server = obj_utils.create_test_server(
            self.context, status=states.DELETING)
        delete_server_mock.side_effect = None
        self._start_service()

        self.service.delete_server(self.context, server)
        self._stop_service()

        delete_server_mock.assert_called_once_with(mock.ANY, server)

    @mock.patch.object(manager.EngineManager, '_delete_server')
    def test_delete_server_unassociated(self, delete_server_mock):
        fake_node = mock.MagicMock()
        fake_node.provision_state = ironic_states.ACTIVE
        server = obj_utils.create_test_server(
            self.context, status=states.DELETING, node_uuid=None)
        self._start_service()

        self.service.delete_server(self.context, server)
        self._stop_service()

        delete_server_mock.assert_not_called()

    @mock.patch.object(IronicDriver, 'get_power_state')
    @mock.patch.object(IronicDriver, 'set_power_state')
    def test_change_server_power_state(
            self, set_power_mock, get_power_mock):
        server = obj_utils.create_test_server(
            self.context, status=states.POWERING_ON)
        fake_node = mock.MagicMock()
        fake_node.target_power_state = ironic_states.NOSTATE
        get_power_mock.return_value = states.POWER_ON
        self._start_service()

        self.service.set_power_state(self.context, server,
                                     ironic_states.POWER_ON)
        self._stop_service()

        set_power_mock.assert_called_once_with(self.context,
                                               server,
                                               ironic_states.POWER_ON)
        get_power_mock.assert_called_once_with(self.context, server.uuid)

    @mock.patch.object(notifications, 'notify_about_server_action')
    @mock.patch.object(IronicDriver, 'get_power_state')
    @mock.patch.object(IronicDriver, 'set_power_state')
    def test_change_server_power_state_with_error_status(
            self, set_power_mock, get_power_mock, notify_mock):
        server = obj_utils.create_test_server(
            self.context, status=states.REBOOTING)
        get_power_mock.return_value = states.POWER_OFF
        exception = Exception("test-exception")
        set_power_mock.side_effect = exception

        self._start_service()
        self.assertRaises(Exception,
                          self.service.set_power_state,
                          self.context,
                          server, 'reboot')
        set_power_mock.assert_called_once_with(self.context, server, 'reboot')
        get_power_mock.assert_called_once_with(self.context, server.uuid)
        notify_mock.assert_called_once_with(
            self.context, server, 'test-host',
            action=fields.NotificationAction.REBOOT,
            phase=fields.NotificationPhase.ERROR, exception=exception)
        self.assertEqual(server.status, states.ERROR)
        self._stop_service()

    @mock.patch.object(notifications, 'notify_about_server_action')
    @mock.patch.object(IronicDriver, 'get_power_state')
    @mock.patch.object(IronicDriver, 'set_power_state')
    def test_change_server_power_state_with_rollback_status(
            self, set_power_mock, get_power_mock, notify_mock):
        server = obj_utils.create_test_server(
            self.context, status=states.POWERING_OFF)
        exception = Exception("test-exception")
        get_power_mock.return_value = states.POWER_ON
        set_power_mock.side_effect = exception

        self._start_service()
        self.assertRaises(Exception, self.service.set_power_state,
                          self.context, server, 'off')
        set_power_mock.assert_called_once_with(self.context, server, 'off')
        get_power_mock.assert_called_once_with(self.context, server.uuid)
        notify_mock.assert_called_once_with(
            self.context, server, 'test-host',
            action=fields.NotificationAction.POWER_OFF,
            phase=fields.NotificationPhase.ERROR, exception=exception)
        self.assertEqual(server.status, states.ACTIVE)
        self._stop_service()

    @mock.patch.object(ironic.IronicClientWrapper, 'call')
    def test_get_serial_console(self, mock_ironic_call):
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
        server = obj_utils.create_test_server(self.context)
        self._start_service()
        console = self.service.get_serial_console(self.context, server)
        self._stop_service()
        self.assertEqual(4321, console['port'])
        self.assertTrue(
            console['access_url'].startswith('http://127.0.0.1:8866/?token='))
        self.assertEqual('localhost', console['host'])
        self.assertIn('token', console)

    @mock.patch.object(network_api.API, 'delete_port')
    @mock.patch.object(IronicDriver, 'unplug_vif')
    def test_detach_interface(self, unplug_vif_mock, delete_port_mock):
        fake_node = mock.MagicMock()
        fake_node.provision_state = ironic_states.ACTIVE
        server = obj_utils.create_test_server(
            self.context, status=states.ACTIVE, node_uuid=None)
        port_id = server['nics'][0]['port_id']
        self._start_service()
        self.service.detach_interface(self.context, server, port_id)
        self._stop_service()
        unplug_vif_mock.assert_called_once_with(self.context, server, port_id)
        delete_port_mock.assert_called_once_with(self.context, port_id,
                                                 server.uuid)

    def test_wrap_server_fault(self):
        server = {"uuid": uuidutils.generate_uuid()}

        called = {'fault_added': False}

        def did_it_add_fault(*args):
            called['fault_added'] = True

        self.stub_out('mogan.common.utils.add_server_fault_from_exc',
                      did_it_add_fault)

        @manager.wrap_server_fault
        def failer(engine_manager, context, server):
            raise NotImplementedError()

        self.assertRaises(NotImplementedError, failer,
                          manager.EngineManager, self.context, server=server)

        self.assertTrue(called['fault_added'])

    def test_wrap_server_fault_no_server(self):
        server = {"uuid": uuidutils.generate_uuid()}

        called = {'fault_added': False}

        def did_it_add_fault(*args):
            called['fault_added'] = True

        self.stub_out('mogan.common.utils.add_server_fault_from_exc',
                      did_it_add_fault)

        @manager.wrap_server_fault
        def failer(engine_manager, context, server):
            raise exception.ServerNotFound(server=server['uuid'])

        self.assertRaises(exception.ServerNotFound, failer,
                          manager.EngineManager, self.context, server=server)

        self.assertFalse(called['fault_added'])
