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

"""Tests for the Pecan API app."""


import mock
from pecan import hooks

from mogan.api import app
from mogan.api.controllers.root import RootController
from mogan.engine import api as engineapi
from mogan.tests import base


class TestHook(hooks.PecanHook):
    pass


class TestApplication(base.TestCase):
    @mock.patch.object(engineapi, 'API')
    def test_setup_app(self, mock_api):
        moganapp = app.setup_app()
        self.assertIsInstance(moganapp._mogan_app.application.app.root,
                              RootController)

    @mock.patch.object(engineapi, 'API')
    def test_setup_app_with_extra_hooks(self, mock_api):
        testhook = TestHook()
        moganapp = app.setup_app(extra_hooks=[testhook])
        self.assertIn(testhook, moganapp._mogan_app.application.app.hooks)
