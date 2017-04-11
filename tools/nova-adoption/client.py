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

from ironicclient import client as ironic_client
from keystoneauth1 import loading
from keystoneauth1 import session
from neutronclient.v2_0 import client as neutron_clientv20
from novaclient import api_versions
from novaclient import client as nova_client


class Client(object):
    def __init__(self, args):
        self.args = args
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(
            auth_url=args.os_auth_url,
            username=args.os_username,
            password=args.os_password,
            project_id=args.os_project_id,
            project_name=args.os_project_name,
            project_domain_id=args.os_project_domain_id,
            user_domain_id=args.os_user_domain_id)
        sess = session.Session(auth=auth)
        self.nova = nova_client.Client(
            api_versions.APIVersion('2.1'), session=sess)
        self.ironic = ironic_client.Client('1', session=sess,
                                           os_ironic_api_version='1.29')
        self.neutron = neutron_clientv20.Client(session=sess)

    def get_bms_nodes(self):
        bm_nodes = self.ironic.node.list(detail=True)
        bms = []
        nodes = []
        # NOTE: we only adopt the servers in active or stopped state.
        for node in bm_nodes:
            bm = self.nova.servers.list(
                search_opts={'node': node.uuid, 'vm_state': 'active'})
            if not bm:
                bm = self.nova.servers.list(
                    search_opts={'node': node.uuid, 'vm_state': 'stopped'})
            if bm:
                bms.extend(bm)
                nodes.append(node)
        return bms, nodes

    def get_port_by_macs(self, macs):
        ports = []
        for mac in macs:
            port = self.neutron.list_ports(mac_address=mac)
            ports.extend(port['ports'])
        return ports
