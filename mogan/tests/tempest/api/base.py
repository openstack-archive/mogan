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

import time

from mogan.common import exception
from tempest.common.utils import data_utils
from tempest import config
from tempest.lib import exceptions as lib_exc
import tempest.test

from mogan.tests.tempest.service import client

CONF = config.CONF


class BaseBaremetalComputeTest(tempest.test.BaseTestCase):
    """Base test case class for all Baremetal Compute API tests."""

    credentials = ['primary']
    client_manager = client.Manager

    @classmethod
    def skip_checks(cls):
        super(BaseBaremetalComputeTest, cls).skip_checks()
        if not CONF.service_available.mogan_plugin:
            raise cls.skipException("Mogan support is required")

    @classmethod
    def setup_clients(cls):
        super(BaseBaremetalComputeTest, cls).setup_clients()
        cls.baremetal_compute_client = cls.os.baremetal_compute_client

    @classmethod
    def resource_setup(cls):
        super(BaseBaremetalComputeTest, cls).resource_setup()
        cls.type_ids = []
        cls.instance_ids = []

    @classmethod
    def create_instance(cls, wait_until_active=True):
        types = cls.baremetal_compute_client.list_instance_types()
        for t in types:
            if t['name'] == 'small':
                type_id = t['uuid']
                break
        else:
            # TODO(liusheng) we shouldn't depend on the default
            # type created by devstack
            raise exception.InstanceTypeNotFound("'small' type not found.")
        tenant_network = cls.get_tenant_network()
        image_id = CONF.compute.image_ref
        body = {'name': data_utils.rand_name('nimble_instance'),
                'description': "nimble tempest instance",
                'instance_type_uuid': type_id,
                'image_uuid': image_id,
                "networks": [{"net_id": tenant_network['id']}]
                }
        resp = cls.baremetal_compute_client.create_instance(**body)
        cls.instance_ids.append(resp['uuid'])
        if wait_until_active:
            cls._wait_for_instances_status(resp['uuid'], 'active', 15, 900)
        return resp

    @classmethod
    def _wait_for_instances_status(cls, inst_id, status,
                                   build_interval, build_timeout):
        """Waits for a Instance to reach a given status."""
        inst_status = None
        start = int(time.time())

        while inst_status != status:
            time.sleep(build_interval)
            body = cls.baremetal_compute_client.show_instance(inst_id)
            inst_status = body['status']
            if inst_status == 'error' and status != 'error':
                msg = ('Failed to provision instance %s' % inst_id)
                raise exception.InstanceDeployFailure(msg)

            if int(time.time()) - start >= build_timeout:
                message = ('Instance %s failed to reach %s status '
                           '(current %s) within the required time (%s s).' %
                           (inst_id, status, inst_status,
                            build_timeout))
                raise lib_exc.TimeoutException(message)

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
        cls.cleanup_resources(cls.baremetal_compute_client.delete_instance,
                              cls.instance_ids)
        super(BaseBaremetalComputeTest, cls).resource_cleanup()
