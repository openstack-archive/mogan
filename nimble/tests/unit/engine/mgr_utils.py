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

"""Test utils for Nimble Managers."""

from nimble.engine import manager


class ServiceSetUpMixin(object):
    def setUp(self):
        super(ServiceSetUpMixin, self).setUp()
        self.hostname = 'test-host'
        self.service = manager.EngineManager(self.hostname, 'test-topic')

    def _stop_service(self):
        self.service.del_host()

    def _start_service(self):
        self.service.init_host()
        self.addCleanup(self._stop_service)
