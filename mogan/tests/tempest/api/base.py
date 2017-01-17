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

    # NOTE(liusheng) because the baremetal sever deployment need some
    # network related configurations which configured by ironic. The
    # 'private' network is choosed by default, we need to admin user
    # to use the 'private' network.
    credentials = ['admin']
    client_manager = client.Manager

    @classmethod
    def skip_checks(cls):
        super(BaseBaremetalComputeTest, cls).skip_checks()
        if not CONF.service_available.mogan_plugin:
            raise cls.skipException("Mogan support is required")

    @classmethod
    def setup_clients(cls):
        super(BaseBaremetalComputeTest, cls).setup_clients()
        cls.baremetal_compute_client = cls.os_admin.baremetal_compute_client
        cls.compute_networks_client = cls.os_admin.compute_networks_client

    @classmethod
    def _get_small_flavor(cls):
        types = cls.baremetal_compute_client.list_instance_types()
        for t in types:
            if t['name'] == 'small':
                return t['uuid']
        else:
            # TODO(liusheng) we shouldn't depend on the default
            # type created by devstack
            raise exception.InstanceTypeNotFound("'small' type not found.")

    @classmethod
    def _get_net_id(cls):
        for net in cls.compute_networks_client.list_networks()['networks']:
            if net['label'] == CONF.compute.fixed_network_name:
                return net['id']
        else:
            raise lib_exc.TempestException('Could not find fixed network!')

    @classmethod
    def resource_setup(cls):
        super(BaseBaremetalComputeTest, cls).resource_setup()
        cls.type_ids = []
        cls.instance_ids = []
        cls.small_flavor = cls._get_small_flavor()
        cls.image_id = CONF.compute.image_ref
        cls.net_id = cls._get_net_id()

    @classmethod
    def create_instance(cls, wait_until_active=True):
        body = {'name': data_utils.rand_name('mogan_instance'),
                'description': "mogan tempest instance",
                'instance_type_uuid': cls.small_flavor,
                'image_uuid': cls.image_id,
                "networks": [{"net_id": cls.net_id}]
                }
        resp_mogan = cls.baremetal_compute_client.create_instance(**body)
        resp = resp_mogan['instances'][0]
        cls.instance_ids.append(resp['uuid'])
        if wait_until_active:
            cls._wait_for_instances_status(resp['uuid'], 'active', 15, 900)
        return resp

    @classmethod
    def _wait_for_instances_status(cls, inst_id, status,
                                   wait_interval, wait_timeout):
        """Waits for a Instance to reach a given status."""
        inst_status = None
        start = int(time.time())

        while inst_status != status:
            time.sleep(wait_interval)
            try:
                body = cls.baremetal_compute_client.show_instance(inst_id)
                inst_status = body['status']
            except lib_exc.NotFound:
                if status == 'deleted':
                    break
                else:
                    raise
            if inst_status == 'error' and status != 'error':
                msg = ('Failed to provision instance %s' % inst_id)
                raise exception.InstanceDeployFailure(msg)

            if int(time.time()) - start >= wait_timeout:
                message = ('Instance %s failed to reach %s status '
                           '(current %s) within the required time (%s s).' %
                           (inst_id, status, inst_status,
                            wait_timeout))
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
