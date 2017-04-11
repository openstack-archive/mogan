# Copyright 2017 Huawei Technologies Co.,LTD.
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
To use this tool, you just need to run: `python adoption.py`, this depends on
the env user credentials, you also manually specify the user credentials. Use
`python adoption.py --help` to get more details.
"""

import argparse
import itertools
import os
import sys

from keystoneauth1 import loading
from oslo_config import cfg
from oslo_context import context

import client as resource_client
from mogan.common import exception
from mogan.common import service as mogan_service
from mogan import objects

CONF = cfg.CONF

STATUS_MAPPING = {}


def env(*args, **kwargs):
    """Returns the first environment variable set.

    If all are empty, defaults to '' or keyword arg `default`.
    """
    for arg in args:
        value = os.environ.get(arg)
        if value:
            return value
    return kwargs.get('default', '')


def get_parser():
    parser = argparse.ArgumentParser(prog='nova-bms-adoption')
    loading.register_session_argparse_arguments(parser)
    default_auth_plugin = 'password'
    if 'os-token' in sys.argv:
        default_auth_plugin = 'token'
    loading.register_auth_argparse_arguments(
        parser, sys.argv, default=default_auth_plugin)
    parser.set_defaults(os_auth_url=env('OS_AUTH_URL'))
    parser.set_defaults(os_username=env('OS_USERNAME'))
    parser.set_defaults(os_password=env('OS_PASSWORD'))
    parser.set_defaults(os_project_name=env(
        'OS_PROJECT_NAME', 'OS_TENANT_NAME'))
    parser.set_defaults(os_project_id=env('OS_PROJECT_ID', 'OS_TENANT_ID'))
    parser.set_defaults(os_project_domain_id=env('OS_PROJECT_DOMAIN_ID',
                                                 default='default'))
    parser.set_defaults(os_user_domain_id=env('OS_USER_DOMAIN_ID',
                                              default='default'))
    return parser


def _construct_nics(ctxt, client, bm):
    addresses = bm.addresses
    mac_addrs = [addr['OS-EXT-IPS-MAC:mac_addr'] for addr in
                 itertools.chain(*addresses.values())]
    macs = sorted(set(mac_addrs), key=mac_addrs.index)
    ports = client.get_port_by_macs(macs)
    nics_object = objects.InstanceNics(ctxt)
    for port in ports:
        nic_dict = {'port_id': port['id'],
                    'network_id': port['network_id'],
                    'mac_address': port['mac_address'],
                    'fixed_ips': port['fixed_ips'],
                    'port_type': port.get('binding: vif_type', ''),
                    'instance_uuid': bm.id}
        nics_object.objects.append(objects.InstanceNic(
            ctxt, **nic_dict))
    return nics_object


def _add_flavor(ctxt, flavor_uuid):
    try:
        objects.InstanceType.get(ctxt, flavor_uuid)
    except exception.InstanceTypeNotFound:
        inst_type_obj = objects.InstanceType(
            ctxt, uuid=flavor_uuid, name='nova_adoption_flavor',
            is_public=True, description='instance_type created for bms '
                                        'adopted from Nova')
        inst_type_obj.create(ctxt)


def handle_bms(ctxt, client, bms, nodes):
    for bm, node in zip(bms, nodes):
        task_state = getattr(bm, 'OS-EXT-STS:task_state')
        if task_state is not None:
            print("The instance %s in task state: %s, skipped to adopt." % (
                bm.id, task_state))
            continue
        nics_object = _construct_nics(ctxt, client, bm)
        mogan_bm_attrs = {
            'uuid': bm.id,
            'name': bm.name,
            'description': 'baremetal servers adopted from Nova',
            'project_id': bm.tenant_id,
            'user_id': bm.user_id,
            'status': getattr(bm, 'OS-EXT-STS:vm_state'),
            # NOTE: the mogan periodic task will sync the power state
            'power_state': None,
            # NOTE: we create a mogan flavor with same uuid of nova bm flavor
            'instance_type_uuid': bm.flavor['id'],
            'availability_zone': (node.properties.get('availability_zone') or
                                  CONF.engine.default_availability_zone),
            'image_uuid': bm.image['id'],
            'node_uuid': getattr(bm, 'OS-EXT-SRV-ATTR:hypervisor_hostname'),
            'launched_at': getattr(bm, 'OS-SRV-USG:launched_at', ''),
            'created_at': bm.created,
            'updated_at': bm.updated,
            'extra': {}}
        _add_flavor(ctxt, bm.flavor['id'])
        inst_object = objects.Instance(ctxt, **mogan_bm_attrs)
        inst_object.nics = nics_object
        inst_object.create()


def main():
    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])
    client = resource_client.Client(args)
    bms, nodes = client.get_bms_nodes()
    ctxt = context.get_admin_context()
    mogan_service.prepare_service(sys.argv)
    handle_bms(ctxt, client, bms, nodes)


if __name__ == '__main__':
    main()
