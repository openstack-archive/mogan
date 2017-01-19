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
"""
Unit Tests for :py:class:`mogan.engine.rpcapi.EngineAPI`.
"""

import copy

import mock
from oslo_config import cfg
from oslo_messaging import _utils as messaging_utils

from mogan.engine import manager as engine_manager
from mogan.engine import rpcapi as engine_rpcapi
from mogan import objects
from mogan.tests import base as tests_base
from mogan.tests.unit.db import base
from mogan.tests.unit.db import utils as dbutils

CONF = cfg.CONF


class EngineRPCAPITestCase(tests_base.TestCase):

    def test_versions_in_sync(self):
        self.assertEqual(
            engine_manager.EngineManager.RPC_API_VERSION,
            engine_rpcapi.EngineAPI.RPC_API_VERSION)


class RPCAPITestCase(base.DbTestCase):

    def setUp(self):
        super(RPCAPITestCase, self).setUp()
        self.fake_instance = dbutils.get_test_instance()
        self.fake_instance_obj = objects.Instance._from_db_object(
            objects.Instance(self.context), self.fake_instance)
        self.fake_type = dbutils.get_test_instance_type()
        self.fake_type['extra_specs'] = {}
        self.fake_type_obj = objects.InstanceType._from_db_object(
            objects.InstanceType(self.context), self.fake_type)

    def test_serialized_instance_has_uuid(self):
        self.assertIn('uuid', self.fake_instance)

    def _test_rpcapi(self, method, rpc_method, **kwargs):
        rpcapi = engine_rpcapi.EngineAPI(topic='fake-topic')

        expected_retval = 'hello world' if rpc_method == 'call' else None

        expected_topic = 'fake-topic'

        target = {
            "topic": expected_topic,
            "server": CONF.host,
            "version": kwargs.pop('version', rpcapi.RPC_API_VERSION)
        }
        expected_msg = copy.deepcopy(kwargs)

        self.fake_args = None
        self.fake_kwargs = None

        def _fake_can_send_version_method(version):
            return messaging_utils.version_is_compatible(
                rpcapi.RPC_API_VERSION, version)

        def _fake_prepare_method(*args, **kwargs):
            for kwd in kwargs:
                self.assertEqual(kwargs[kwd], target[kwd])
            return rpcapi.client

        def _fake_rpc_method(*args, **kwargs):
            self.fake_args = args
            self.fake_kwargs = kwargs
            if expected_retval:
                return expected_retval

        with mock.patch.object(rpcapi.client,
                               "can_send_version") as mock_can_send_version:
            mock_can_send_version.side_effect = _fake_can_send_version_method
            with mock.patch.object(rpcapi.client, "prepare") as mock_prepared:
                mock_prepared.side_effect = _fake_prepare_method

                with mock.patch.object(rpcapi.client,
                                       rpc_method) as mock_method:
                    mock_method.side_effect = _fake_rpc_method
                    retval = getattr(rpcapi, method)(self.context, **kwargs)
                    self.assertEqual(retval, expected_retval)
                    expected_args = [self.context, method, expected_msg]
                    for arg, expected_arg in zip(self.fake_args,
                                                 expected_args):
                        self.assertEqual(arg, expected_arg)

    def test_create_instance(self):
        self._test_rpcapi('create_instance',
                          'cast',
                          version='1.0',
                          instance=self.fake_instance_obj,
                          requested_networks=[],
                          request_spec=None,
                          filter_properties=None)

    def test_delete_instance(self):
        self._test_rpcapi('delete_instance',
                          'cast',
                          version='1.0',
                          instance=self.fake_instance_obj)

    def test_set_power_state(self):
        self._test_rpcapi('set_power_state',
                          'cast',
                          version='1.0',
                          instance=self.fake_instance_obj,
                          state='power on')
