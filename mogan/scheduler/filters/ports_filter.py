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

from oslo_log import log as logging

from mogan.scheduler import filters

LOG = logging.getLogger(__name__)


class PortsFilter(filters.BaseNodeFilter):
    """NodeFilter to work with resource server type records."""

    def _find_port_type(self, ports, port_type):
        """Check if ports has the specified port type."""

        for port in ports:
            if port_type == port.port_type:
                return True

        return False

    def _satisfies_networks(self, ports, networks):
        """Check if ports satisfy networks requirements.

        Check that the ports provided by the nodes satisfy
        the networks associated with the request spec.
        """

        if not networks:
            return True

        if len(ports) < len(networks):
            return False

        for net in networks:
            if 'port_type' in net:
                if not self._find_port_type(ports, net.get('port_type')):
                    return False

        return True

    def node_passes(self, node_state, filter_properties):
        """Return a list of nodes that can create resource_type."""
        spec = filter_properties.get('request_spec', {})
        props = spec.get('server_properties', {})
        networks = props.get('networks')
        if not self._satisfies_networks(node_state.ports, networks):
            LOG.debug("%(node_state)s fails network ports "
                      "requirements", {'node_state': node_state})
            return False
        return True
