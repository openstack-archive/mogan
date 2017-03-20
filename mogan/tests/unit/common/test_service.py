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

import mock
from oslo_concurrency import processutils
from oslo_config import cfg
import oslo_messaging
from oslo_service import service as base_service

from mogan.common import constants
from mogan.common import exception
from mogan.common import rpc
from mogan.common import service
from mogan.engine import manager
from mogan.objects import base as objects_base
from mogan.tests import base

CONF = cfg.CONF


@mock.patch.object(base_service.Service, '__init__', lambda *_, **__: None)
class TestRPCService(base.TestCase):

    def setUp(self):
        super(TestRPCService, self).setUp()
        host = "fake_host"
        mgr_module = "mogan.engine.manager"
        mgr_class = "EngineManager"
        self.rpc_svc = service.RPCService(host, mgr_module, mgr_class,
                                          constants.ENGINE_TOPIC)

    @mock.patch.object(oslo_messaging, 'Target', autospec=True)
    @mock.patch.object(objects_base, 'MoganObjectSerializer', autospec=True)
    @mock.patch.object(rpc, 'get_server', autospec=True)
    @mock.patch.object(manager.EngineManager, 'init_host', autospec=True)
    def test_start(self, mock_init_method, mock_rpc, mock_ios, mock_target):
        mock_rpc.return_value.start = mock.MagicMock()
        self.rpc_svc.handle_signal = mock.MagicMock()
        self.rpc_svc.start()
        mock_target.assert_called_once_with(topic=self.rpc_svc.topic,
                                            server="fake_host")
        mock_ios.assert_called_once_with()
        mock_init_method.assert_called_once_with(self.rpc_svc.manager)


class TestWSGIService(base.TestCase):
    @mock.patch.object(service.wsgi, 'Server')
    def test_workers_set_default(self, wsgi_server):
        service_name = "mogan_api"
        test_service = service.WSGIService(service_name)
        self.assertEqual(processutils.get_worker_count(),
                         test_service.workers)
        wsgi_server.assert_called_once_with(CONF, service_name,
                                            test_service.app,
                                            host='0.0.0.0',
                                            port=6688,
                                            use_ssl=False)

    @mock.patch.object(service.wsgi, 'Server')
    def test_workers_set_correct_setting(self, wsgi_server):
        self.config(api_workers=8, group='api')
        test_service = service.WSGIService("mogan_api")
        self.assertEqual(8, test_service.workers)

    @mock.patch.object(service.wsgi, 'Server')
    def test_workers_set_zero_setting(self, wsgi_server):
        self.config(api_workers=0, group='api')
        test_service = service.WSGIService("mogan_api")
        self.assertEqual(processutils.get_worker_count(), test_service.workers)

    @mock.patch.object(service.wsgi, 'Server')
    def test_workers_set_negative_setting(self, wsgi_server):
        self.config(api_workers=-2, group='api')
        self.assertRaises(exception.ConfigInvalid,
                          service.WSGIService,
                          'mogan_api')
        self.assertFalse(wsgi_server.called)

    @mock.patch.object(service.wsgi, 'Server')
    def test_wsgi_service_with_ssl_enabled(self, wsgi_server):
        self.config(enable_ssl_api=True, group='api')
        service_name = 'mogan_api'
        srv = service.WSGIService('mogan_api', CONF.api.enable_ssl_api)
        wsgi_server.assert_called_once_with(CONF, service_name,
                                            srv.app,
                                            host='0.0.0.0',
                                            port=6688,
                                            use_ssl=True)
