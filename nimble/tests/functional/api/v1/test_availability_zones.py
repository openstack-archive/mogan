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

import mock

from nimble.tests.functional.api import v1 as v1_test


class TestAvailabilityZone(v1_test.APITestV1):

    def setUp(self):
        super(TestAvailabilityZone, self).setUp()

    @mock.patch('nimble.engine.api.API.list_availability_zones')
    def test_availability_zone_get_all(self, list_azs):
        list_azs.return_value = {'availability_zones': ['az1', 'az2']}
        resp = self.get_json('/availability_zones')
        self.assertItemsEqual(['az1', 'az2'], resp['availability_zones'])
