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

from ironicclient import exc as ironic_exc
import mock
from oslo_config import cfg
from oslo_utils import uuidutils

from mogan.baremetal.ironic.driver import ironic_states
from mogan.baremetal.ironic import IronicDriver
from mogan.common import exception
from mogan.common import ironic
from mogan.common import states
from mogan.engine import manager
from mogan.network import api as network_api
from mogan.notifications import base as notifications
from mogan.objects import fields
from mogan.objects import server
from mogan.scheduler.client.report import SchedulerReportClient as report_api
from mogan.tests.unit.db import base as tests_db_base
from mogan.tests.unit.engine import mgr_utils
from mogan.tests.unit.objects import utils as obj_utils

CONF = cfg.CONF


class ManageServerTestCase(mgr_utils.ServiceSetUpMixin,
                           tests_db_base.DbTestCase):

    @mock.patch.object(network_api.API, 'delete_port')
    @mock.patch.object(IronicDriver, 'unplug_vif')
    def test_destroy_networks(self, unplug_vif_mock, delete_port_mock):
        server = obj_utils.create_test_server(self.context)
        server_port_id = server.nics[0].port_id
        delete_port_mock.side_effect = None
        unplug_vif_mock.side_effect = None
        self._start_service()

        self.service.destroy_networks(self.context, server)
        self._stop_service()

        unplug_vif_mock.assert_called_once_with(
            self.context, server, server_port_id)
        delete_port_mock.assert_called_once_with(
            self.context, server_port_id, server.uuid)

    @mock.patch.object(IronicDriver, 'destroy')
    @mock.patch.object(manager.EngineManager, 'destroy_networks')
    def _test__delete_server(self, destroy_networks_mock,
                             destroy_node_mock, state=None):
        fake_node = mock.MagicMock()
        fake_node.provision_state = state
        server = obj_utils.create_test_server(self.context)
        destroy_networks_mock.side_effect = None
        destroy_node_mock.side_effect = None
        self._start_service()

        self.service._delete_server(self.context, server)
        self._stop_service()

        destroy_networks_mock.assert_called_once_with(self.context, server)
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
        exception = ironic_exc.NotFound("The bare metal node is not found")
        set_power_mock.side_effect = exception

        self._start_service()
        self.assertRaises(ironic_exc.NotFound,
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
        exception = ironic_exc.NotFound("The bare metal node is not found")
        get_power_mock.return_value = states.POWER_ON
        set_power_mock.side_effect = exception

        self._start_service()
        self.assertRaises(ironic_exc.NotFound, self.service.set_power_state,
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
        console = self.service.get_serial_console(
            self.context, server, 'shellinabox')
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

    @mock.patch.object(IronicDriver, 'get_manageable_nodes')
    def test_get_manageable_servers_failed(self, get_manageable_mock):
        get_manageable_mock.side_effect = exception.MoganException()
        self._start_service()
        self.assertRaises(exception.MoganException,
                          self.service.get_manageable_servers,
                          self.context)
        self._stop_service()
        get_manageable_mock.assert_called_once()

    @mock.patch.object(IronicDriver, 'get_manageable_nodes')
    def test_get_manageable_servers(self, get_manageable_mock):
        get_manageable_mock.return_value = {}
        self._start_service()
        self.service.get_manageable_servers(self.context)
        self._stop_service()
        get_manageable_mock.assert_called_once()

    @mock.patch.object(network_api.API, 'bind_port')
    @mock.patch.object(IronicDriver, 'manage')
    @mock.patch.object(network_api.API, 'show_port')
    @mock.patch.object(report_api, 'put_allocations')
    def test__manage_servers(self,
                             put_allocations_mock, show_port_mock,
                             manage_mock, bind_port_mock):
        neutron_port_id = '67ec8e86-d77b-4729-b11d-a009864d289d'
        neutron_mac_address = '52:54:00:8e:6a:03'
        node_uuid = 'aacdbd78-d670-409e-95aa-ecfcfb94fee2'
        image_uuid = 'efe0a06f-ca95-4808-b41e-9f55b9c5eb98'

        node = {
            'uuid': node_uuid,
            'name': 'test_manageable_mode',
            'resource_class': 'gold',
            'power_state': 'power on',
            'provision_state': 'active',
            "ports": [
                {
                    "address": neutron_mac_address,
                    "uuid": "1ec01153-685a-49b5-a6d3-45a4e7dddf53",
                    "neutron_port_id": neutron_port_id
                }
            ],
            "portgroups": [
                {
                    "address": "a4:dc:be:0e:82:a6",
                    "uuid": "1ec01153-685a-49b5-a6d3-45a4e7dddf54",
                    "neutron_port_id": None
                }
            ],
            'image_source': image_uuid
        }

        put_allocations_mock.side_effect = None
        show_port_mock.return_value = {
            'id': neutron_port_id,
            'network_id': '34ec8e86-d77b-4729-b11d-a009864d3456',
            'mac_address': neutron_mac_address,
            'fixed_ips': [{"subnet_id": "d2d7a7c2-17d2-4268-906d-1da8dde24fa8",
                           "ip_address": "10.80.20.12"}]
        }

        bind_port_mock.side_effect = None
        server = obj_utils.get_test_server(
            self.context, status=None, node_uuid=None,
            power_state=states.NOSTATE, availability_zone=None,
            image_uuid=None)

        manage_mock.side_effect = None
        self.service._manage_server(self.context, server, node)

        put_allocations_mock.assert_called_once()
        manage_mock.assert_called_once()
        show_port_mock.assert_called_once_with(self.context, neutron_port_id)
        bind_port_mock.assert_called_once_with(self.context, neutron_port_id,
                                               server)
        self.assertEqual(server.node_uuid, node_uuid)
        self.assertIsNone(server.availability_zone)
        self.assertEqual(server.status, 'active')
        self.assertEqual(server.power_state, 'power on')
        self.assertEqual(server.image_uuid, image_uuid)

    @mock.patch.object(network_api.API, 'bind_port')
    @mock.patch.object(IronicDriver, 'manage')
    @mock.patch.object(network_api.API, 'show_port')
    @mock.patch.object(report_api, 'put_allocations')
    def test__manage_servers_with_mac_exception(self,
                                                put_allocations_mock,
                                                show_port_mock,
                                                manage_mock, bind_port_mock):
        neutron_port_id1 = '67ec8e86-d77b-4729-b11d-a009864d289d'
        neutron_port_id2 = '67ec8e86-d77b-4729-b11d-a009864d289d'
        neutron_mac_address1 = '52:54:00:8e:6a:03'
        neutron_mac_address2 = '52:54:00:8e:6a:04'
        node_uuid = 'aacdbd78-d670-409e-95aa-ecfcfb94fee2'

        node = {
            'uuid': node_uuid,
            'name': 'test_manageable_mode',
            'resource_class': 'gold',
            'power_state': 'power on',
            'provision_state': 'active',
            "ports": [
                {
                    "address": neutron_mac_address1,
                    "uuid": "1ec01153-685a-49b5-a6d3-45a4e7dddf53",
                    "neutron_port_id": neutron_port_id1
                }
            ],
            "portgroups": [
                {
                    "address": "a4:dc:be:0e:82:a6",
                    "uuid": "1ec01153-685a-49b5-a6d3-45a4e7dddf54",
                    "neutron_port_id": neutron_port_id2
                }
            ],
            'image_source': 'efe0a06f-ca95-4808-b41e-9f55b9c5eb98'
        }

        put_allocations_mock.side_effect = None
        show_port_mock.return_value = {
            'id': neutron_port_id1,
            'network_id': '34ec8e86-d77b-4729-b11d-a009864d3456',
            'mac_address': neutron_mac_address2,
            'fixed_ips': [{"subnet_id": "d2d7a7c2-17d2-4268-906d-1da8dde24fa8",
                           "ip_address": "10.80.20.12"}]
        }

        server = obj_utils.get_test_server(
            self.context, status=None, node_uuid=None,
            power_state=states.NOSTATE, availability_zone=None,
            image_uuid=None)

        manage_mock.side_effect = None
        self.assertRaises(exception.NetworkError, self.service._manage_server,
                          self.context, server, node)

        put_allocations_mock.assert_called_once()
        show_port_mock.assert_called_with(self.context, neutron_port_id1)
        show_port_mock.assert_called_with(self.context, neutron_port_id2)
        manage_mock.assert_not_called()
        bind_port_mock.assert_not_called()
        self.assertNotEqual(server.node_uuid, node_uuid)
        self.assertIsNone(server.availability_zone)
        self.assertIsNone(server.status, None)
        self.assertEqual(server.power_state, states.NOSTATE)
        self.assertIsNone(server.image_uuid, None)

    @mock.patch.object(server.Server, 'create')
    @mock.patch.object(IronicDriver, 'unmanage')
    @mock.patch.object(manager.EngineManager, '_manage_server')
    @mock.patch.object(IronicDriver, 'get_manageable_node')
    def test_manage_servers(self, get_manageable_mock,
                            manage_mock, umanage_mock, server_create_mock):
        get_manageable_mock.side_effect = None
        manage_mock.side_effect = None
        server_create_mock.side_effect = None

        server = obj_utils.get_test_server(
            self.context, status=None, node_uuid=None,
            power_state=states.NOSTATE, availability_zone=None,
            image_uuid=None)
        node_uuid = 'aacdbd78-d670-409e-95aa-ecfcfb94fee2'

        self.service.manage_server(self.context, server, node_uuid)

        get_manageable_mock.assert_called_once_with(node_uuid)
        manage_mock.assert_called_once()
        umanage_mock.assert_not_called()
        server_create_mock.assert_called_once()

    @mock.patch.object(manager.EngineManager, '_rollback_servers_quota')
    @mock.patch.object(server.Server, 'create')
    @mock.patch.object(IronicDriver, 'unmanage')
    @mock.patch.object(manager.EngineManager, '_manage_server')
    @mock.patch.object(IronicDriver, 'get_manageable_node')
    def test_manage_servers_with_db_exception(self,
                                              get_manageable_mock,
                                              manage_mock,
                                              umanage_mock,
                                              server_create_mock,
                                              rollback_quota_mock):
        get_manageable_mock.side_effect = None
        manage_mock.side_effect = None
        server_create_mock.side_effect = exception.ServerAlreadyExists(
            "test-server")

        server = obj_utils.get_test_server(
            self.context, status=None, node_uuid=None,
            power_state=states.NOSTATE, availability_zone=None,
            image_uuid=None)
        node_uuid = 'aacdbd78-d670-409e-95aa-ecfcfb94fee2'

        self.assertRaises(exception.ServerAlreadyExists,
                          self.service.manage_server,
                          self.context, server, node_uuid)

        get_manageable_mock.assert_called_once_with(node_uuid)
        manage_mock.assert_called_once()
        umanage_mock.assert_called_once()
        server_create_mock.assert_called_once()
        rollback_quota_mock.assert_called_once_with(self.context, -1)

    @mock.patch.object(manager.EngineManager, '_rollback_servers_quota')
    @mock.patch.object(server.Server, 'create')
    @mock.patch.object(IronicDriver, 'unmanage')
    @mock.patch.object(manager.EngineManager, '_manage_server')
    @mock.patch.object(IronicDriver, 'get_manageable_node')
    def test_manage_servers_with_network_exception(self,
                                                   get_manageable_mock,
                                                   manage_mock,
                                                   umanage_mock,
                                                   server_create_mock,
                                                   rollback_quota_mock):
        get_manageable_mock.side_effect = None
        manage_mock.side_effect = exception.NetworkError()
        server_create_mock.side_effect = None

        server = obj_utils.get_test_server(
            self.context, status=None, node_uuid=None,
            power_state=states.NOSTATE, availability_zone=None,
            image_uuid=None)
        node_uuid = 'aacdbd78-d670-409e-95aa-ecfcfb94fee2'

        self.assertRaises(exception.NetworkError,
                          self.service.manage_server,
                          self.context, server, node_uuid)

        get_manageable_mock.assert_called_once_with(node_uuid)
        manage_mock.assert_called_once()
        umanage_mock.assert_not_called()
        server_create_mock.assert_not_called()
        rollback_quota_mock.assert_called_once_with(self.context, -1)
