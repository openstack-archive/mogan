# -*- encoding: utf-8 -*-
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

"""Tests for the Pecan API hooks."""


import mock
from oslo_config import cfg

from nimble.api import hooks
from nimble.common import context
from nimble.tests.unit.api import base


class FakeRequest(object):
    def __init__(self, headers, context, environ):
        self.headers = headers
        self.context = context
        self.environ = environ or {}
        self.version = (1, 0)
        self.host_url = 'http://127.0.0.1:6688'


class FakeRequestState(object):
    def __init__(self, headers=None, context=None, environ=None):
        self.request = FakeRequest(headers, context, environ)
        self.response = FakeRequest(headers, context, environ)

    def set_context(self):
        headers = self.request.headers
        creds = {
            'user': headers.get('X-User') or headers.get('X-User-Id'),
            'tenant': headers.get('X-Tenant') or headers.get('X-Tenant-Id'),
            'domain_id': headers.get('X-User-Domain-Id'),
            'domain_name': headers.get('X-User-Domain-Name'),
            'auth_token': headers.get('X-Auth-Token'),
            'roles': headers.get('X-Roles', '').split(','),
        }
        is_public_api = self.request.environ.get('is_public_api', False)

        self.request.context = context.RequestContext(
            is_public_api=is_public_api, **creds)


def fake_headers(admin=False):
    headers = {
        'X-Auth-Token': '8d9f235ca7464dd7ba46f81515797ea0',
        'X-Domain-Id': 'None',
        'X-Domain-Name': 'None',
        'X-Project-Domain-Id': 'default',
        'X-Project-Domain-Name': 'Default',
        'X-Project-Id': 'b4efa69d4ffa4973863f2eefc094f7f8',
        'X-Project-Name': 'admin',
        'X-Role': '_member_,admin',
        'X-Roles': '_member_,admin',
        'X-Tenant': 'foo',
        'X-Tenant-Id': 'b4efa69d4ffa4973863f2eefc094f7f8',
        'X-Tenant-Name': 'foo',
        'X-User': 'foo',
        'X-User-Domain-Id': 'default',
        'X-User-Domain-Name': 'Default',
        'X-User-Id': '604ab2a197c442c2a84aba66708a9e1e',
        'X-User-Name': 'foo',
        'X-OpenStack-Nimble-API-Version': '1.0'
    }
    if admin:
        headers.update({
            'X-Project-Name': 'admin',
            'X-Role': '_member_,admin',
            'X-Roles': '_member_,admin',
            'X-Tenant': 'admin',
            'X-Tenant-Name': 'admin',
        })
    else:
        headers.update({
            'X-Project-Name': 'foo',
            'X-Role': '_member_',
            'X-Roles': '_member_',
        })
    return headers


class TestContextHook(base.BaseApiTest):
    @mock.patch.object(context, 'RequestContext')
    def test_context_hook(self, mock_ctx):
        headers = fake_headers(admin=True)
        reqstate = FakeRequestState(headers=headers)
        context_hook = hooks.ContextHook(None)
        context_hook.before(reqstate)
        mock_ctx.assert_called_with(
            auth_token=headers['X-Auth-Token'],
            user=headers['X-User'],
            tenant=headers['X-Tenant'],
            domain_id=headers['X-User-Domain-Id'],
            domain_name=headers['X-User-Domain-Name'],
            is_public_api=False,
            roles=headers['X-Roles'].split(','))

    @mock.patch.object(context, 'RequestContext')
    def test_context_hook_public_api(self, mock_ctx):
        headers = fake_headers(admin=True)
        env = {'is_public_api': True}
        reqstate = FakeRequestState(headers=headers, environ=env)
        context_hook = hooks.ContextHook(None)
        context_hook.before(reqstate)
        mock_ctx.assert_called_with(
            auth_token=headers['X-Auth-Token'],
            user=headers['X-User'],
            tenant=headers['X-Tenant'],
            domain_id=headers['X-User-Domain-Id'],
            domain_name=headers['X-User-Domain-Name'],
            is_public_api=True,
            roles=headers['X-Roles'].split(','))

    @mock.patch.object(context, 'RequestContext')
    def test_context_hook_after_add_request_id(self, mock_ctx):
        headers = fake_headers(admin=True)
        reqstate = FakeRequestState(headers=headers)
        reqstate.set_context()
        reqstate.request.context.request_id = 'fake-id'
        context_hook = hooks.ContextHook(None)
        context_hook.after(reqstate)
        self.assertIn('Openstack-Request-Id',
                      reqstate.response.headers)
        self.assertEqual(
            'fake-id',
            reqstate.response.headers['Openstack-Request-Id'])

    def test_context_hook_after_miss_context(self):
        response = self.get_json('/bad/path',
                                 expect_errors=True)
        self.assertNotIn('Openstack-Request-Id',
                         response.headers)


class TestPublicUrlHook(base.BaseApiTest):

    def test_before_host_url(self):
        headers = fake_headers()
        reqstate = FakeRequestState(headers=headers)
        trusted_call_hook = hooks.PublicUrlHook()
        trusted_call_hook.before(reqstate)
        self.assertEqual(reqstate.request.host_url,
                         reqstate.request.public_url)

    def test_before_public_endpoint(self):
        cfg.CONF.set_override('public_endpoint', 'http://foo', 'api')
        headers = fake_headers()
        reqstate = FakeRequestState(headers=headers)
        trusted_call_hook = hooks.PublicUrlHook()
        trusted_call_hook.before(reqstate)
        self.assertEqual('http://foo', reqstate.request.public_url)
