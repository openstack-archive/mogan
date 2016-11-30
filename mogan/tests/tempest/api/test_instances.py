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

from mogan.tests.tempest.api import base


class BaremetalComputeAPIInstancesTest(base.BaseBaremetalComputeTest):
    def test_instance_post(self):
        resp = self.create_instance()
        self.assertIn('uuid', resp)
        self.assertIn('name', resp)
        self.assertIn('description', resp)
        self.assertIn('instance_type_uuid', resp)
        self.assertIn('image_uuid', resp)
        self.assertIn('availability_zone', resp)
        self.assertIn('network_info', resp)
        self.assertIn('status', resp)
