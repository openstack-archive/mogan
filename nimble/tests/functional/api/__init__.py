# -*- encoding: utf-8 -*-
#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
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
"""Base classes for API tests."""


from oslo_config import cfg
from oslo_serialization import jsonutils
from oslo_utils import fileutils
import pecan
import pecan.testing

from nimble import objects
from nimble.tests.unit.db import base

cfg.CONF.import_group('keystone_authtoken', 'keystonemiddleware.auth_token')


class BaseApiTest(base.DbTestCase):
    """Pecan controller functional testing class.

    Used for functional tests of Pecan controllers where you need to
    test your literal application and its integration with the
    framework.
    """

    PATH_PREFIX = ''

    def setUp(self):
        super(BaseApiTest, self).setUp()
        cfg.CONF.set_override("auth_version", "v3",
                              group='keystone_authtoken')
        cfg.CONF.set_override("admin_user", "admin",
                              group='keystone_authtoken')

        objects.register_all()
        self.app = self._make_app()

        def reset_pecan():
            pecan.set_config({}, overwrite=True)

        self.addCleanup(reset_pecan)

    def _make_app(self):
        # Determine where we are so we can set up paths in the config
        root_dir = self.get_path()
        paste_cfg = cfg.CONF.api.paste_config
        with open(paste_cfg, 'r') as f:
            paste_cfg_content = f.read()
        paste_cfg_content = paste_cfg_content.replace(
            'public_api_routes = /,/v1\n', 'public_api_routes = /,/v1.*\n')
        self.tmp_paste_cfg = fileutils.write_to_tempfile(
            content=paste_cfg_content, prefix='nimble_api_paste',
            suffix='.ini')
        self.app_config = {
            'app': {
                'root': 'nimble.api.controllers.root.RootController',
                'modules': ['nimble.api'],
                'static_root': '%s/public' % root_dir,
                'template_path': '%s/api/templates' % root_dir,
            },
        }
        return pecan.testing.load_test_app(self.app_config,
                                           paste_cfg_file=self.tmp_paste_cfg)

    def _request_json(self, path, params, expect_errors=False, headers=None,
                      method="post", extra_environ=None, status=None):
        """Sends simulated HTTP request to Pecan test app.

        :param path: url path of target service
        :param params: content for wsgi.input of request
        :param expect_errors: Boolean value; whether an error is expected based
                              on request
        :param headers: a dictionary of headers to send along with the request
        :param method: Request method type. Appropriate method function call
                       should be used rather than passing attribute in.
        :param extra_environ: a dictionary of environ variables to send along
                              with the request
        :param status: expected status code of response
        :param path_prefix: prefix of the url path
        """
        response = getattr(self.app, "%s_json" % method)(
            str(path),
            params=params,
            headers=headers,
            status=status,
            extra_environ=extra_environ,
            expect_errors=expect_errors
        )
        return response

    def put_json(self, path, params, expect_errors=False, headers=None,
                 extra_environ=None, status=None):
        """Sends simulated HTTP PUT request to Pecan test app.

        :param path: url path of target service
        :param params: content for wsgi.input of request
        :param expect_errors: Boolean value; whether an error is expected based
                              on request
        :param headers: a dictionary of headers to send along with the request
        :param extra_environ: a dictionary of environ variables to send along
                              with the request
        :param status: expected status code of response
        """
        full_path = self.PATH_PREFIX + path
        return self._request_json(path=full_path, params=params,
                                  expect_errors=expect_errors,
                                  headers=headers, extra_environ=extra_environ,
                                  status=status, method="put")

    def post_json(self, path, params, expect_errors=False, headers=None,
                  extra_environ=None, status=None):
        """Sends simulated HTTP POST request to Pecan test app.

        :param path: url path of target service
        :param params: content for wsgi.input of request
        :param expect_errors: Boolean value; whether an error is expected based
                              on request
        :param headers: a dictionary of headers to send along with the request
        :param extra_environ: a dictionary of environ variables to send along
                              with the request
        :param status: expected status code of response
        """
        full_path = self.PATH_PREFIX + path
        return self._request_json(path=full_path, params=params,
                                  expect_errors=expect_errors,
                                  headers=headers, extra_environ=extra_environ,
                                  status=status, method="post")

    def patch_json(self, path, params, expect_errors=False, headers=None,
                   extra_environ=None, status=None):
        """Sends simulated HTTP PATCH request to Pecan test app.

        :param path: url path of target service
        :param params: content for wsgi.input of request
        :param expect_errors: Boolean value; whether an error is expected based
                              on request
        :param headers: a dictionary of headers to send along with the request
        :param extra_environ: a dictionary of environ variables to send along
                              with the request
        :param status: expected status code of response
        """
        full_path = self.PATH_PREFIX + path
        return self._request_json(path=full_path, params=params,
                                  expect_errors=expect_errors,
                                  headers=headers, extra_environ=extra_environ,
                                  status=status, method="patch")

    def delete(self, path, expect_errors=False, headers=None,
               extra_environ=None, status=None):
        """Sends simulated HTTP DELETE request to Pecan test app.

        :param path: url path of target service
        :param expect_errors: Boolean value; whether an error is expected based
                              on request
        :param headers: a dictionary of headers to send along with the request
        :param extra_environ: a dictionary of environ variables to send along
                              with the request
        :param status: expected status code of response
        :param path_prefix: prefix of the url path
        """
        full_path = self.PATH_PREFIX + path
        response = self.app.delete(str(full_path),
                                   headers=headers,
                                   status=status,
                                   extra_environ=extra_environ,
                                   expect_errors=expect_errors)
        return response

    def get_json(self, path, expect_errors=False, headers=None,
                 extra_environ=None, q=[], **params):
        """Sends simulated HTTP GET request to Pecan test app.

        :param path: url path of target service
        :param expect_errors: Boolean value;whether an error is expected based
                              on request
        :param headers: a dictionary of headers to send along with the request
        :param extra_environ: a dictionary of environ variables to send along
                              with the request
        :param q: list of queries consisting of: field, value, op, and type
                  keys
        :param path_prefix: prefix of the url path
        :param params: content for wsgi.input of request
        """
        full_path = self.PATH_PREFIX + path
        query_params = {'q.field': [],
                        'q.value': [],
                        'q.op': [],
                        }
        for query in q:
            for name in ['field', 'op', 'value']:
                query_params['q.%s' % name].append(query.get(name, ''))
        all_params = {}
        all_params.update(params)
        if q:
            all_params.update(query_params)
        response = self.app.get(full_path,
                                params=all_params,
                                headers=headers,
                                extra_environ=extra_environ,
                                expect_errors=expect_errors)
        if not expect_errors:
            response = response.json
        return response

    def gen_headers(self, context, **kw):
        """Generate a header for a simulated HTTP request to Pecan test app.

        :param context: context that store the client user information.
        :param kw: key word aguments, used to overwrite the context attribute.

        note: "is_public_api" is not in headers, it should be in environ
        variables to send along with the requeste. We can pass it by
        extra_environ when we call delete, get_json or other method request.
        """
        ct = context.to_dict()
        ct.update(kw)
        headers = {
            'X-User-Name': ct.get("user_name") or "user",
            'X-User-Id':
                ct.get("user") or "8abcdef1-2345-6789-abcd-ef123456abc0",
            'X-Project-Name': ct.get("project_name") or "project",
            'X-Project-Id':
                ct.get("tenant") or "1abcdef1-2345-6789-abcd-ef123456abe0",
            'X-User-Domain-Id':
                ct.get("domain_id") or "9abcdef1-2345-6789-abcd-ef123456abc0",
            'X-User-Domain-Name': ct.get("domain_name") or "no_domain",
            'X-Auth-Token':
                ct.get("auth_token") or "6aff71c33a274bc3ab7f0b29ca1be162",
            'X-Roles': ct.get("roles") or "nimble"
        }

        return headers

    def parser_error_body(self, resp):
        """paser a string response error body to json for a bad HTTP request.

        :param body: and response body need to be parsered.

        :return: an python dict will be return. such as:
                {u'debuginfo': None,
                 u'faultcode': u'Client',
                 u'faultstring': u': error reason'}

        Note: the error body just one nested json string, so we do not need
        a recursive function.
        """
        body = jsonutils.loads(resp.body)
        return jsonutils.loads(body["error_message"])
