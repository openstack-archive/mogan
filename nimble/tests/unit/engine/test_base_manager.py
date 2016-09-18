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

"""Test class for Nimble BaseEngineManager."""

import eventlet
import mock
from oslo_config import cfg

from nimble.engine.baremetal import ironic
from nimble.tests.unit.db import base as tests_db_base
from nimble.tests.unit.engine import mgr_utils


CONF = cfg.CONF


@mock.patch.object(ironic, 'get_node_list')
class StartStopTestCase(mgr_utils.ServiceSetUpMixin, tests_db_base.DbTestCase):
    def test_prevent_double_start(self, mock_node_list):
        self._start_service()
        self.assertRaisesRegex(RuntimeError, 'already running',
                               self.service.init_host)

    @mock.patch.object(eventlet.greenpool.GreenPool, 'waitall')
    def test_del_host_waits_on_workerpool(self, wait_mock, mock_node_list):
        self._start_service()
        self.service.del_host()
        self.assertTrue(wait_mock.called)
