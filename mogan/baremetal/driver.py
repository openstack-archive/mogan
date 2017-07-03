# Copyright 2017 Hengfeng Bank Co.,Ltd.
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

"""Base engine driver functionality."""

import sys

from oslo_log import log as logging
from oslo_utils import importutils

from mogan.common import utils

LOG = logging.getLogger(__name__)


class BaseEngineDriver(object):

    """Base class for mogan baremetal drivers.
    """
    def __init__(self):
        """Add init staff here.
        """

    def get_maintenance_node_list(self):
        """Return maintenance nodes.

        """
        raise NotImplementedError()

    def get_nodes_power_state(self):
        """Return nodes power state.

        """
        raise NotImplementedError()

    def get_power_state(self, context, server_uuid):
        """Return a node's power state by passing server uuid.

        :param server_uuid: moga server uuid to get power state.
        """
        raise NotImplementedError()

    def set_power_state(self, context, node_uuid, state):
        """Set a node's power state.

        :param node_uuid: node id to change power state.
        :param state: mogan states to change to.
        """
        raise NotImplementedError()

    def get_ports_from_node(self, node_uuid, detail=True):
        """Get a node's ports info.

        :param node_uuid: node id to get ports info.
        :param detail: whether to get detailed info of all the ports,
            default to False.
        """
        raise NotImplementedError()

    def plug_vif(self, node_interface, neutron_port_id):
        """Plug a neutron port to a baremetal port.

        :param node_interface: bare metal interface to plug neutron port.
        :param neutron_port_id: neutron port id to plug.
        """
        raise NotImplementedError()

    def unplug_vif(self, context, server, port_id):
        """Unplug network interface.

        :param server: the server object.
        """
        raise NotImplementedError()

    def spawn(self, context, server, configdrive_value):
        """Create a new server on the provision platform.

        :param context: security context
        :param server: moga server object.
        :param configdrive_value: The configdrive value to be injected.
        """
        raise NotImplementedError()

    def destroy(self, context, server):
        """Trigger node destroy process.

        :param server: the server to destroy.
        """
        raise NotImplementedError()

    def rebuild(self, context, server):
        """Trigger node deploy process.

        :param server: server to rebuild.
        """
        raise NotImplementedError()

    def get_serial_console_by_server(self, context, server):
        """Get console info by server.

        :param server: server to get its console info.
        """
        raise NotImplementedError()

    def get_available_nodes(self):
        """Retrieve all nodes information.

        :returns: Dictionary describing nodes
        """
        raise NotImplementedError()

    @staticmethod
    def get_node_inventory(node):
        """Get the inventory of a node.

        :param node: node to get its inventory data.
        """
        raise NotImplementedError()

    def get_manageable_nodes(self):
        """Retrieve all manageable nodes information.

        :returns: Dictionary describing nodes
        """
        raise NotImplementedError()


def load_engine_driver(engine_driver):
    """Load a engine driver module.

    Load the engine driver module specified by the engine_driver
    configuration option or, if supplied, the driver name supplied as an
    argument.

    :param engine_driver: a engine driver name to override the config opt
    :returns: a EngineDriver server
    """

    if not engine_driver:
        LOG.error("Engine driver option required, but not specified")
        sys.exit(1)

    LOG.info("Loading engine driver '%s'", engine_driver)
    try:
        driver = importutils.import_object(
            'mogan.baremetal.%s' % engine_driver)
        return utils.check_isinstance(driver, BaseEngineDriver)
    except ImportError:
        LOG.exception("Unable to load the baremetal driver")
        sys.exit(1)
