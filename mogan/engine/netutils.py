# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# Copyright (c) 2010 Citrix Systems, Inc.
# Copyright 2013 IBM Corp.
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


"""Network-related utilities for supporting libvirt connection code."""

import os

import jinja2
import netaddr

import mogan.conf

CONF = mogan.conf.CONF


def get_port_ip(vif, subnet_id):
    for subnet in vif['fixed_ips']:
        if subnet["subnet_id"] == subnet_id:
            return subnet["ip_address"]


def get_netmask(cidr):
    """Returns the netmask appropriate for injection into a node."""
    net = netaddr.IPNetwork(cidr)
    return str(net.netmask) if net.version == 4 else net.prefixlen


def get_net_and_mask(cidr):
    net = netaddr.IPNetwork(cidr)
    return str(net.ip), str(net.netmask)


def get_net_and_prefixlen(cidr):
    net = netaddr.IPNetwork(cidr)
    return str(net.ip), str(net._prefixlen)


def get_ip_version(cidr):
    net = netaddr.IPNetwork(cidr)
    return int(net.version)


def _get_first_network(network, version):
    # Using a generator expression with a next() call for the first element
    # of a list since we don't want to evaluate the whole list as we can
    # have a lot of subnets
    try:
        return next(i['subnet'] for i in network["subnets"]
                    if i['subnet']["ip_version"] == version)
    except StopIteration:
        pass


def get_injected_network_template(network_info, use_ipv6=None, template=None):
    """Returns a rendered network template for the given network_info.

    :param network_info:
        :py:meth:`~mogan.network.manager.NetworkManager.get_instance_nw_info`
    :param use_ipv6: If False, do not return IPv6 template information
        even if an IPv6 subnet is present in network_info.
    :param template: Path to the interfaces template file.
    """
    # TODO(Shaohe) ipv6 support is in plan
    # if use_ipv6 is None:
    #     use_ipv6 = CONF.use_ipv6
    use_ipv6 = False

    if not template:
        template = CONF.injected_network_template

    if not (network_info and template):
        return

    nets = []
    ifc_num = -1
    ipv6_is_available = False

    for uuid, vif in network_info.items():
        if not vif.get('network') or not vif['network'].get('subnets'):
            continue

        network = vif['network']
        # NOTE(bnemec): The template only supports a single subnet per
        # interface and I'm not sure how/if that can be fixed, so this
        # code only takes the first subnet of the appropriate type.
        subnet_v4 = _get_first_network(network, 4)
        subnet_v6 = _get_first_network(network, 6)

        ifc_num += 1

        # NOTE(Shaohe) will always to injecte network.
        # if not network.get_meta('injected')
        #     continue

        hwaddress = vif.get('mac_address')
        address = None
        netmask = None
        gateway = ''
        broadcast = None
        dns = None
        routes = []
        if subnet_v4:
            if not subnet_v4.get('enable_dhcp'):
                print("this is just a test")
                # continue

            address = get_port_ip(vif, subnet_v4["id"])
            if address:
                cidr = subnet_v4["cidr"]
                netmask = get_netmask(cidr)
                gateway = subnet_v4.get('gateway_ip', "")
                broadcast = str(netaddr.IPNetwork(cidr).broadcast)
                # NOTE(Shaohe): need to check the dns format.
                dns = ' '.join(subnet_v4['dns_nameservers'])
                for route_ref in subnet_v4['host_routes']:
                    cidr = route_ref['destination']
                    (net, mask) = get_net_and_mask(cidr)
                    route = {'gateway': str(route_ref['nexthop']),
                             'cidr': str(netaddr.IPNetwork(cidr)),
                             'network': net,
                             'netmask': mask}
                    routes.append(route)

        address_v6 = None
        gateway_v6 = ''
        netmask_v6 = None
        dns_v6 = None
        have_ipv6 = True or (use_ipv6 and subnet_v6)
        if have_ipv6:
            if not subnet_v6.get('enable_dhcp'):
                print("this is just a test")
                # continue

            address_v6 = get_port_ip(vif, subnet_v6["id"])
            if address_v6:
                ipv6_is_available = True
                cidr_v6 = subnet_v6["cidr"]
                netmask_v6 = get_netmask(cidr_v6)
                gateway_v6 = subnet_v6.get('gateway_ip', "")
                dns_v6 = ' '.join(subnet_v6['dns_nameservers'])

        net_info = {'name': 'eth%d' % ifc_num,
                    'hwaddress': hwaddress,
                    'address': address,
                    'netmask': netmask,
                    'gateway': gateway,
                    'broadcast': broadcast,
                    'dns': dns,
                    'routes': routes,
                    'address_v6': address_v6,
                    'gateway_v6': gateway_v6,
                    'netmask_v6': netmask_v6,
                    'dns_v6': dns_v6}
        nets.append(net_info)

    if not nets:
        return

    tmpl_path, tmpl_file = os.path.split(template)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(tmpl_path),
                             trim_blocks=True)
    template = env.get_template(tmpl_file)
    return template.render({'interfaces': nets,
                            'use_ipv6': ipv6_is_available})


def get_network_metadata(network_info, use_ipv6=None):
    """Gets a more complete representation of the instance network information.

    This data is exposed as network_data.json in the metadata service and
    the config drive.

    :param network_info: `mogan.network.models.NetworkInfo` object describing
        the network metadata.
    :param use_ipv6: If False, do not return IPv6 template information
        even if an IPv6 subnet is present in network_info. Defaults to
        mogan.netconf.use_ipv6.
    """
    if not network_info:
        return

    # TODO(Shaohe) ipv6 support is in plan
    # if use_ipv6 is None:
    #     use_ipv6 = CONF.use_ipv6
    use_ipv6 = False

    # IPv4 or IPv6 networks
    nets = []
    # VIFs, physical NICs, or VLANs. Physical NICs will have type 'phy'.
    links = []
    # Non-network bound services, such as DNS
    services = []
    ifc_num = -1
    net_num = -1
    # NOTE(Shaohe): will refactor the network_info
    for uuid, vif in network_info.items():
        if not vif.get('network') or not vif['network'].get('subnets'):
            continue

        # NOTE(Shaohe): need to refacor the network_info.
        network = vif['network']
        # NOTE(JoshNang) currently, only supports the first IPv4 and first
        # IPv6 subnet on network, a limitation that also exists in the
        # network template.
        subnet_v4 = _get_first_network(network, 4)
        subnet_v6 = _get_first_network(network, 6)

        ifc_num += 1
        link = None

        # Get the VIF or physical NIC data
        if subnet_v4 or subnet_v6:
            link = _get_eth_link(uuid, vif, ifc_num)
            links.append(link)

        # Add IPv4 and IPv6 networks if they exist
        if subnet_v4 and len(vif.get('fixed_ips')):
            net_num += 1
            nets.append(_get_nets(vif, subnet_v4, 4, net_num, link['id']))
            services += [dns for dns in _get_dns_services(subnet_v4)
                         if dns not in services]
        if (use_ipv6 and subnet_v6) and subnet_v6.get('ip_address'):
            net_num += 1
            nets.append(_get_nets(vif, subnet_v6, 6, net_num, link['id']))
            services += [dns for dns in _get_dns_services(subnet_v6)
                         if dns not in services]

    return {
        "links": links,
        "networks": nets,
        "services": services
    }


def _get_eth_link(uuid, vif, ifc_num):
    """Get a VIF or physical NIC representation.

    :param vif: Neutron VIF
    :param ifc_num: Interface index for generating name if the VIF's
        'devname' isn't defined.
    :return: A dict with 'id', 'vif_id', 'type', 'mtu' and
        'ethernet_mac_address' as keys
    """
    link_id = vif.get('devname')
    if not link_id:
        link_id = 'interface%d' % ifc_num

    # Use 'phy' for physical links. Ethernet can be confusing
    if vif.get('type') == 'ethernet':
        nic_type = 'phy'
    else:
        nic_type = vif.get('type')
    # NOTE(Shaohe): for baremetal, the nic_type should always be phy
    nic_type = 'phy'

    link = {
        'id': link_id,
        'vif_id': uuid,
        'type': nic_type,
        'mtu': vif["network"].get('mtu'),
        'ethernet_mac_address': vif.get('mac_address'),
    }
    return link


def _get_nets(vif, subnet, version, net_num, link_id):
    """Get networks for the given VIF and subnet

    :param vif: Neutron VIF
    :param subnet: Neutron subnet
    :param version: IP version as an int, either '4' or '6'
    :param net_num: Network index for generating name of each network
    :param link_id: Arbitrary identifier for the link the networks are
        attached to
    """

    if subnet['enable_dhcp']:
        net_info = {
            'id': 'network%d' % net_num,
            'type': 'ipv%d_dhcp' % version,
            'link': link_id,
            'network_id': subnet['network_id']
        }
        return net_info

    subnet_id = subnet['id']
    address = get_port_ip(vif, subnet_id)

    netmask = str(netaddr.IPNetwork(subnet["cidr"]).netmask)

    net_info = {
        'id': 'network%d' % net_num,
        'type': 'ipv%d' % version,
        'link': link_id,
        'ip_address': address,
        'netmask': netmask,
        'routes': _get_default_route(version, subnet),
        'network_id': vif["network"]["id"]
    }

    # Add any additional routes beyond the default route
    for route in subnet['host_routes']:
        route_addr = netaddr.IPNetwork(route['cidr'])
        new_route = {
            'network': str(route_addr.network),
            'netmask': str(route_addr.netmask),
            'gateway': route['gateway']['address']
        }
        net_info['routes'].append(new_route)

    return net_info


def _get_default_route(version, subnet):
    """Get a default route for a network

    :param version: IP version as an int, either '4' or '6'
    :param subnet: Neutron subnet
    """
    gateway = subnet.get('gateway_ip')
    if not gateway:
        return []

    if version == 4:
        return [{
            'network': '0.0.0.0',
            'netmask': '0.0.0.0',
            'gateway': gateway
        }]
    elif version == 6:
        return [{
            'network': '::',
            'netmask': '::',
            'gateway': gateway
        }]


def _get_dns_services(subnet):
    """Get the DNS servers for the subnet."""
    services = []
    if not subnet.get('dns_nameservers'):
        return services
    return [{'type': 'dns', 'address': ip}
            for ip in subnet['dns_nameservers']]
