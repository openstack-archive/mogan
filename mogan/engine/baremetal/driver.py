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

    def get_available_resources(self):
        """Retrieve resource information.

        :returns: Dictionary describing resources
        """
        raise NotImplementedError()

    def get_maintenance_node_list(self):
        """Return maintenance nodes.

        """
        raise NotImplementedError()

    def get_nodes_power_state(self):
        """Return nodes power state.

        """
        raise NotImplementedError()

    def get_power_state(self, context, instance_uuid):
        """Return a node's power state by passing instance uuid.

        :param instance_uuid: mogan instance uuid to get power state.
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

    def unplug_vifs(self, context, instance):
        """Unplug network interfaces.

        :param instance: the instance object.
        """
        raise NotImplementedError()

    def spawn(self, context, instance, admin_password):
        """Create a new instance on the provision platform.

        :param context: security context
        :param instance: mogan instance object.
        :param admin_password: Administrator password to set in
            instance.
        """
        raise NotImplementedError()

    def destroy(self, context, instance):
        """Trigger node destroy process.

        :param instance: the instance to destory.
        """
        raise NotImplementedError()

    def rebuild(self, context, instance):
        """Trigger node deploy process.

        :param instance: instance to rebuild.
        """
        raise NotImplementedError()

    def get_serial_console_by_instance(self, context, instance):
        """Get console info by instance.

        :param instance: instance to get its console info.
        """
        raise NotImplementedError()


def load_engine_driver(engine_driver):
    """Load a engine driver module.

    Load the engine driver module specified by the engine_driver
    configuration option or, if supplied, the driver name supplied as an
    argument.

    :param engine_driver: a engine driver name to override the config opt
    :returns: a EngineDriver instance
    """

    if not engine_driver:
        LOG.error("Engine driver option required, but not specified")
        sys.exit(1)

    LOG.info("Loading engine driver '%s'", engine_driver)
    try:
        driver = importutils.import_object(
            'mogan.engine.baremetal.%s' % engine_driver)
        return utils.check_isinstance(driver, BaseEngineDriver)
    except ImportError:
        LOG.exception("Unable to load the baremetal driver")
        sys.exit(1)
