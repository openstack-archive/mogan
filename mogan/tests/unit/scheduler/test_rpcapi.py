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
Unit Tests for :py:class:`mogan.scheduler.rpcapi.SchedulerAPI`.
"""

import copy

import mock
from oslo_config import cfg
from oslo_messaging import _utils as messaging_utils

from mogan.scheduler import manager as scheduler_manager
from mogan.scheduler import rpcapi as scheduler_rpcapi
from mogan.tests import base as tests_base
from mogan.tests.unit.db import base

CONF = cfg.CONF


class SchedulerRPCAPITestCase(tests_base.TestCase):

    def test_versions_in_sync(self):
        self.assertEqual(
            scheduler_manager.SchedulerManager.RPC_API_VERSION,
            scheduler_rpcapi.SchedulerAPI.RPC_API_VERSION)


class RPCAPITestCase(base.DbTestCase):

    def _test_rpcapi(self, method, rpc_method, **kwargs):
        rpcapi = scheduler_rpcapi.SchedulerAPI(topic='fake-topic')

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

    def test_select_destinations(self):
        self._test_rpcapi('select_destinations',
                          'call',
                          version='1.0',
                          request_spec=None,
                          filter_properties=None)
