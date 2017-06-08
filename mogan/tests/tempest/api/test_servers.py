#
# Copyright 2016 Huawei Technologies Co., Ltd.
#
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
from tempest.lib import decorators

from mogan.tests.tempest.api import base


class BaremetalComputeAPIServersTest(base.BaseBaremetalComputeTest):
    @classmethod
    def resource_setup(cls):
        super(BaremetalComputeAPIServersTest, cls).resource_setup()
        # NOTE(liusheng) Since the moga server deployment is a
        # time-consuming operation and the ironic resource cleanup
        # will be performed after a server deleted, we'd better to
        # put all test cases in a test. Additionally, since the the tests
        # can be run parallelly, this pre-created server should only be used
        # in the test cases which don't change this server.
        cls.creation_resp = cls.create_server()

    def test_server_create(self):
        resp = self.creation_resp
        self.assertEqual(self.server_ids[0], resp['uuid'])
        self.assertEqual('building', resp['status'])
        self.assertEqual(self.small_flavor, resp['flavor_uuid'])
        self.assertEqual('mogan tempest server', resp['description'])
        self.assertEqual(self.image_id, resp['image_uuid'])
        self.assertIn('launched_at', resp)
        self.assertIn('updated_at', resp)
        self.assertIn('extra', resp)
        self.assertIn('links', resp)
        self.assertIn('project_id', resp)
        self.assertIn('user_id', resp)
        self.assertIn('availability_zone', resp)
        self.assertIn('nics', resp)
        self.assertIn('name', resp)

    def test_server_show(self):
        resp = self.baremetal_compute_client.show_server(
            self.server_ids[0])
        self.assertEqual('active', resp['status'])
        self.assertEqual(self.small_flavor, resp['flavor_uuid'])
        self.assertEqual('mogan tempest server', resp['description'])
        self.assertEqual(self.image_id, resp['image_uuid'])
        self.assertEqual('power on', resp['power_state'])
        self.assertIn('launched_at', resp)
        self.assertIn('updated_at', resp)
        self.assertIn('extra', resp)
        self.assertIn('links', resp)
        self.assertIn('project_id', resp)
        self.assertIn('user_id', resp)
        self.assertIn('availability_zone', resp)
        self.assertIn('nics', resp)
        self.assertIn('name', resp)

    def test_server_list(self):
        resp = self.baremetal_compute_client.list_servers()
        self.assertEqual(1, len(resp))
        self.assertEqual(self.server_ids[0], resp[0]['uuid'])
        self.assertEqual('active', resp[0]['status'])
        self.assertIn('name', resp[0])
        self.assertEqual('mogan tempest server', resp[0]['description'])
        self.assertIn('links', resp[0])

    def test_server_delete(self):
        """server deletion will be tested by cleanUp method"""
        pass

    def _ensure_states_before_test(self):
        resp = self.baremetal_compute_client.server_get_state(
            self.server_ids[0])
        self.assertEqual('active', resp['status'])
        self.assertEqual(False, resp['locked'])
        self.assertEqual('power on', resp['power_state'])

    def test_get_server_power_status(self):
        self._ensure_states_before_test()

    def test_server_stop_start(self):
        self._ensure_states_before_test()
        self.baremetal_compute_client.server_set_power_state(
            self.server_ids[0], 'off')
        self._wait_for_servers_status(self.server_ids[0], 15, 900, 'stopped',
                                      'power off')
        self.baremetal_compute_client.server_set_power_state(
            self.server_ids[0], 'on')
        self._wait_for_servers_status(self.server_ids[0], 15, 900, 'active',
                                      'power on')

    def test_server_reboot(self):
        self._ensure_states_before_test()
        self.baremetal_compute_client.server_set_power_state(
            self.server_ids[0], 'reboot')
        self._wait_for_servers_status(self.server_ids[0], 15, 900, 'active',
                                      'power on')

    def test_server_lock_unlock(self):
        self._ensure_states_before_test()
        self.baremetal_compute_client.server_set_lock_state(
            self.server_ids[0], True)
        self._wait_for_servers_status(self.server_ids[0], 15, 900, 'active',
                                      'power on', True)
        self.baremetal_compute_client.server_set_lock_state(
            self.server_ids[0], False)

        self._wait_for_servers_status(self.server_ids[0], 15, 900, 'active',
                                      'power on', False)

    @decorators.skip_because(bug='1697886')
    def test_server_rebuild(self):
        self._ensure_states_before_test()
        self.baremetal_compute_client.server_set_provision_state(
            self.server_ids[0], 'rebuild')
        self._wait_for_servers_status(self.server_ids[0], 15, 900, 'active',
                                      'power on')
