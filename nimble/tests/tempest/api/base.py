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


from tempest.common.utils import data_utils
from tempest import config
from tempest.lib import exceptions as lib_exc
import tempest.test

from nimble.tests.tempest.service import client

CONF = config.CONF


class BaseBaremetalComputeTest(tempest.test.BaseTestCase):
    """Base test case class for all Baremetal Compute API tests."""

    credentials = ['primary']
    client_manager = client.Manager

    @classmethod
    def skip_checks(cls):
        super(BaseBaremetalComputeTest, cls).skip_checks()
        if not CONF.service_available.nimble_plugin:
            raise cls.skipException("Nimble support is required")

    @classmethod
    def setup_clients(cls):
        super(BaseBaremetalComputeTest, cls).setup_clients()
        cls.baremetal_compute_client = cls.os.baremetal_compute_client

    @classmethod
    def resource_setup(cls):
        super(BaseBaremetalComputeTest, cls).resource_setup()
        cls.type_ids = []
        cls.instance_ids = []

    @staticmethod
    def cleanup_resources(method, list_of_ids):
        for resource_id in list_of_ids:
            try:
                method(resource_id)
            except lib_exc.NotFound:
                pass

    @classmethod
    def resource_cleanup(cls):
        cls.cleanup_resources(
            cls.baremetal_compute_client.delete_instance_type, cls.type_ids)
        # TODO(liusheng)
        # cls.cleanup_resources(cls.baremetal_compute_client.delete_instance,
        #  cls.instance_ids)
        super(BaseBaremetalComputeTest, cls).resource_cleanup()

