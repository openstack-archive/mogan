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

from mogan.common.i18n import _LE
from mogan.common.i18n import _LI
from mogan.common import utils

LOG = logging.getLogger(__name__)


class BaseEngineDriver(object):

    """Base class for mogan baremetal drivers.
    """
    def __init__(self):
        """Add init staff here.
        """

    def init_host(self, host):
        """Initialize anything that is necessary for the engine driver to
           function.
        """

    def get_node_list(self, associated=True, maintenance=False):
        """Return all available nodes.

        :param associated: whether to get nodes associated to instances,
            None to get both nodes.
        :param maintenance: whether to get nodes in maintenance mode,
            None to get both nodes.
        :param provision_state: whether to get nodes in maintenance mode,
            None to get both nodes.
        """
        raise NotImplementedError()

    def get_available_node_list(self):
        """Return all available nodes.

        """
        raise NotImplementedError()

    def get_port_list(self):
        """Return all ports.
        """
        raise NotImplementedError()

    def get_portgroup_list(self):
        """Return all portgroups.
        """
        raise NotImplementedError()

    def get_node_by_instance(self, instance_uuid):
        """Return node info associated with certain instance.

        :param instance_uuid: uuid of mogan instance to get node.
        """
        raise NotImplementedError()

    def get_power_state(self, instance_uuid):
        """Return a node's power state by passing instance uuid.

        :param instance_uuid: mogan instance uuid to get power state.
        """
        raise NotImplementedError()

    def set_power_state(self, node_uuid, state):
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

    def unplug_vif(self, node_interface):
        """Unplug a neutron port from a baremetal port.

        :param node_interface: bare metal interface id to unplug port.
        """
        raise NotImplementedError()

    def set_instance_info(self, instance, node):
        """Associate the node with an instance.

        :param instance: mogan instance object.
        :param node: node object.
        """
        raise NotImplementedError()

    def unset_instance_info(self, instance):
        """Disassociate the node with an instance.

        :param instance: mogan instance object.
        """
        raise NotImplementedError()

    def do_node_deploy(self, instance):
        """Trigger node deploy process.

        :param instance: instance to deploy.
        """
        raise NotImplementedError()

    def get_node(self, node_uuid):
        """Get node info by node id.

        :param node_uuid: node id to get info.
        """
        raise NotImplementedError()

    def destroy(self, instance):
        """Trigger node destroy process.

        :param instance: the instance to destory.
        """
        raise NotImplementedError()

    def validate_node(self, node_uuid):
        """Validate whether the node's driver has enough information to
            manage the Node.

        :param node_uuid: node id to validate.
        """
        raise NotImplementedError()

    def is_node_unprovision(self, node):
        """Validate whether the node is in unprovision state.

        :param node: node object to get state.
        """
        raise NotImplementedError()

    def do_node_rebuild(self, instance):
        """Trigger node deploy process.

        :param instance: instance to rebuild.
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
        LOG.error(_LE("Engine driver option required, but not specified"))
        sys.exit(1)

    LOG.info(_LI("Loading engine driver '%s'"), engine_driver)
    try:
        driver = importutils.import_object(
            'mogan.engine.baremetal.%s' % engine_driver)
        return utils.check_isinstance(driver, BaseEngineDriver)
    except ImportError:
        LOG.exception(_LE("Unable to load the baremetal driver"))
        sys.exit(1)
