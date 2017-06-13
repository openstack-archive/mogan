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
from tempest import config
from tempest.lib.common.utils import data_utils
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
        flavors = cls.baremetal_compute_client.list_flavors()
        for f in flavors:
            if f['name'] == 'small':
                return f['uuid']
        else:
            # TODO(liusheng) we shouldn't depend on the default
            # type created by devstack
            raise exception.FlavorNotFound("'small' flavor not found.")

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
        cls.flavor_ids = []
        cls.server_ids = []
        cls.small_flavor = cls._get_small_flavor()
        cls.image_id = CONF.compute.image_ref
        cls.net_id = cls._get_net_id()

    @classmethod
    def create_server(cls, wait_until_active=True):
        body = {'name': data_utils.rand_name('mogan_server'),
                'description': "mogan tempest server",
                'flavor_uuid': cls.small_flavor,
                'image_uuid': cls.image_id,
                "networks": [{"net_id": cls.net_id}]
                }
        resp = cls.baremetal_compute_client.create_server(**body)
        cls.server_ids.append(resp['uuid'])
        if wait_until_active:
            cls._wait_for_servers_status(resp['uuid'], 'active', 15, 900)
        return resp

    @classmethod
    def _wait_for_servers_status(cls, server_id, status,
                                 wait_interval, wait_timeout):
        """Waits for a Server to reach a given status."""
        server_status = None
        start = int(time.time())

        while server_status != status:
            time.sleep(wait_interval)
            try:
                body = cls.baremetal_compute_client.show_server(server_id)
                server_status = body['status']
            except lib_exc.NotFound:
                if status == 'deleted':
                    break
                else:
                    raise
            if server_status == 'error' and status != 'error':
                msg = ('Failed to provision server %s' % server_id)
                raise exception.ServerDeployFailure(msg)

            if int(time.time()) - start >= wait_timeout:
                message = ('Server %s failed to reach %s status '
                           '(current %s) within the required time (%s s).' %
                           (server_id, status, server_status,
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
            cls.baremetal_compute_client.delete_flavor, cls.flavor_ids)
        cls.cleanup_resources(cls.baremetal_compute_client.delete_server,
                              cls.server_ids)
        # NOTE(liusheng): need to ensure servers have been completely
        # deleted in Mogan's db
        for server_id in cls.server_ids:
            cls._wait_for_servers_status(server_id, 'deleted', 1, 60)
        super(BaseBaremetalComputeTest, cls).resource_cleanup()
