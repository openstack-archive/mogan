# Copyright 2010-2011 OpenStack Foundation
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
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

import mock
import os

from oslo_config import cfg
from oslo_config import fixture as config_fixture
from oslo_db import options
from oslo_log import log
from oslotest import base
import pecan
import testscenarios

from nimble.common import config as nimble_config
from nimble.common import context as nimble_context


CONF = cfg.CONF
options.set_defaults(cfg.CONF)
try:
    log.register_options(CONF)
except cfg.ArgsAlreadyParsedError:
    pass


class BaseTestCase(testscenarios.WithScenarios, base.BaseTestCase):
    """Test base class."""

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.addCleanup(CONF.reset)


class TestCase(base.BaseTestCase):
    """Test case base class for all unit tests."""

    def setUp(self):
        super(TestCase, self).setUp()
        self.context = nimble_context.get_admin_context()

        self._set_config()

        def reset_pecan():
            pecan.set_config({}, overwrite=True)

        self.addCleanup(reset_pecan)

    def _set_config(self):
        self.cfg_fixture = self.useFixture(config_fixture.Config(cfg.CONF))
        self.config(use_stderr=False,
                    fatal_exception_format_errors=True)
        self.set_defaults(host='fake-mini',
                          debug=True)
        self.set_defaults(connection="sqlite://",
                          sqlite_synchronous=False,
                          group='database')
        nimble_config.parse_args([], default_config_files=[])

    def config(self, **kw):
        """Override config options for a test."""
        group = kw.pop('group', None)
        for k, v in kw.items():
            CONF.set_override(k, v, group, enforce_type=True)

    def set_defaults(self, **kw):
        """Set default values of config options."""
        group = kw.pop('group', None)
        for o, v in kw.items():
            self.cfg_fixture.set_default(o, v, group=group)

    def get_path(self, project_file=None):
        """Get the absolute path to a file. Used for testing the API.

        :param project_file: File whose path to return. Default: None.
        :returns: path to the specified file, or path to project root.
        """
        root = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            '..',
                                            '..',
                                            )
                               )
        if project_file:
            return os.path.join(root, project_file)
        else:
            return root

    def mock_object(self, obj, attr_name, *args, **kwargs):
        """Use python mock to mock an object attribute

        Mocks the specified objects attribute with the given value.
        Automatically performs 'addCleanup' for the mock.

        """
        patcher = mock.patch.object(obj, attr_name, *args, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result
