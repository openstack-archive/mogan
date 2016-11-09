# Copyright 2016 Huawei Technologies Co.,LTD.
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
"""
Tests for the API /types/ methods.
"""

import datetime

import mock
from oslo_utils import timeutils
from six.moves import http_client
from six.moves.urllib import parse as urlparse

from nimble.tests.unit.api import base as test_api_base
from nimble.tests.unit.api import utils as test_api_utils


class TestPost(test_api_base.BaseApiTest):

    @mock.patch.object(timeutils, 'utcnow')
    def test_create_instance_type(self, mock_utcnow):
        type_dict = test_api_utils.type_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        response = self.post_json(
            '/types', type_dict,
            headers={'X-Auth-Token': test_api_utils.ADMIN_TOKEN})
        self.assertEqual(http_client.CREATED, response.status_int)
        result = self.get_json(
            '/types/%s' % type_dict['uuid'],
            headers={'X-Auth-Token': test_api_utils.ADMIN_TOKEN})
        self.assertEqual(type_dict['uuid'], result['uuid'])
        self.assertFalse(result['updated_at'])
        return_created_at = timeutils.parse_isotime(
            result['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/types/%s' % type_dict['uuid']
        self.assertEqual(urlparse.urlparse(response.location).path,
                         expected_location)
