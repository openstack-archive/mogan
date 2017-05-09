# Copyright 2016 Huawei Technologies Co.,LTD.
# All Rights Reserved.
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
"""
Base classes for storage engines
"""

import abc

from oslo_config import cfg
from oslo_db import api as db_api
import six


_BACKEND_MAPPING = {'sqlalchemy': 'mogan.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF, backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


@six.add_metaclass(abc.ABCMeta)
class Connection(object):
    """Base class for storage system connections."""

    @abc.abstractmethod
    def __init__(self):
        """Constructor."""

    # Flavors
    @abc.abstractmethod
    def flavor_create(self, context, values):
        """Create a new server type."""

    @abc.abstractmethod
    def flavor_get(self, context, flavor_uuid):
        """Get server type by uuid."""

    def flavor_update(self, context, flavor_id, values):
        """Update a server type."""

    @abc.abstractmethod
    def flavor_get_all(self, context):
        """Get all server types."""

    @abc.abstractmethod
    def flavor_destroy(self, context, flavor_uuid):
        """Delete a server type."""

    # Servers
    @abc.abstractmethod
    def server_create(self, context, values):
        """Create a new server."""

    @abc.abstractmethod
    def server_get(self, context, server_id):
        """Get server by name."""

    @abc.abstractmethod
    def server_get_all(self, context, project_only):
        """Get all servers."""

    @abc.abstractmethod
    def server_destroy(self, context, server_id):
        """Delete a server."""

    @abc.abstractmethod
    def server_update(self, context, server_id, values):
        """Update a server."""

    # Compute nodes
    @abc.abstractmethod
    def compute_node_create(self, context, values):
        """Create a new compute node."""

    @abc.abstractmethod
    def compute_node_get(self, context, node_uuid):
        """Get compute node by node uuid."""

    @abc.abstractmethod
    def compute_node_get_all(self, context):
        """Get all compute nodes."""

    @abc.abstractmethod
    def compute_node_get_all_available(self, context):
        """Get all available compute nodes."""

    @abc.abstractmethod
    def compute_node_destroy(self, context, node_uuid):
        """Delete a compute node."""

    @abc.abstractmethod
    def compute_node_update(self, context, node_uuid, values):
        """Update a compute node."""

    # Compute ports
    @abc.abstractmethod
    def compute_port_create(self, context, values):
        """Create a new compute port."""

    @abc.abstractmethod
    def compute_port_get(self, context, port_uuid):
        """Get compute port by port uuid."""

    @abc.abstractmethod
    def compute_port_get_all(self, context):
        """Get all compute ports."""

    @abc.abstractmethod
    def compute_port_get_by_node_uuid(self, context, node_uuid):
        """Get compute ports by node_uuid."""

    @abc.abstractmethod
    def compute_port_destroy(self, context, port_uuid):
        """Delete a compute port."""

    @abc.abstractmethod
    def compute_port_update(self, context, port_uuid, values):
        """Update a compute port."""

    # Compute disks
    @abc.abstractmethod
    def compute_disk_create(self, context, values):
        """Create a new compute disk."""

    @abc.abstractmethod
    def compute_disk_get(self, context, disk_uuid):
        """Get compute disk by disk uuid."""

    @abc.abstractmethod
    def compute_disk_get_all(self, context):
        """Get all compute disks."""

    @abc.abstractmethod
    def compute_disk_get_by_node_uuid(self, context, node_uuid):
        """Get compute disks by node_uuid."""

    @abc.abstractmethod
    def compute_disk_destroy(self, context, disk_uuid):
        """Delete a compute disk."""

    @abc.abstractmethod
    def compute_disk_update(self, context, disk_uuid, values):
        """Update a compute disk."""

    # Flavor extra specs
    @abc.abstractmethod
    def extra_specs_update_or_create(self, context,
                                     flavor_uuid, extra_specs):
        """Create or update server type extra specs.

        This adds or modifies the key/value pairs specified in the
        extra specs dict argument
        """

    @abc.abstractmethod
    def flavor_extra_specs_get(self, context, type_id):
        """Get server type extra specs"""

    @abc.abstractmethod
    def type_extra_specs_delete(self, context, flavor_uuid, key):
        """Delete server type extra specs.

        This deletes the key/value pairs specified in the
        extra specs dict argument
        """

    # Flavor access
    @abc.abstractmethod
    def flavor_access_add(self, context, flavor_id, project_id):
        """Add flavor access for project."""

    @abc.abstractmethod
    def flavor_access_get(self, context, flavor_id):
        """Get flavor access by flavor id."""

    @abc.abstractmethod
    def flavor_access_remove(self, context, flavor_id, project_id):
        """Remove flavor access for project."""

    @abc.abstractmethod
    def server_nics_get_by_server_uuid(self, context, server_uuid):
        """Get the Nics info of a server.

        This query the Nics info of the specified server.
        """

    def server_nic_update_or_create(self, context, port_id, values):
        """Update/Create a nic db entry.

        This creates or updates a nic db entry.
        """
    # Servers Faults
    @abc.abstractmethod
    def server_fault_create(self, context, values):
        """Create a new Server Fault."""

    @abc.abstractmethod
    def server_fault_get_by_server_uuids(self, context, server_uuids):
        """Get all server faults for the provided server_uuids."""

    @abc.abstractmethod
    def quota_get(self, context, project_id, resource_name):
        """Get quota value of a resource"""

    @abc.abstractmethod
    def quota_get_all(self, context, project_only=False):
        """Get all quotas value of resources"""

    @abc.abstractmethod
    def quota_create(self, context, values):
        """Create a quota of a resource"""

    @abc.abstractmethod
    def quota_destroy(self, context, project_id, resource_name):
        """Delete a quota of a resource"""

    @abc.abstractmethod
    def quota_update(self, context, project_id, resource_name, updates):
        """Delete a quota of a resource"""

    @abc.abstractmethod
    def quota_get_all_by_project(self, context, project_id):
        """Get quota by project id"""

    @abc.abstractmethod
    def quota_usage_get_all_by_project(self, context, project_id):
        """Get quota usage by project id"""

    @abc.abstractmethod
    def quota_allocated_get_all_by_project(self, context, project_id):
        """Get quota usage by project id"""

    @abc.abstractmethod
    def quota_reserve(self, context, resources, quotas, deltas, expire,
                      until_refresh, max_age, project_id):
        """Reserve quota of resource"""

    @abc.abstractmethod
    def reservation_commit(self, context, reservations, project_id):
        """Commit reservation of quota usage"""

    @abc.abstractmethod
    def reservation_rollback(self, context, reservations, project_id):
        """Reservation rollback"""

    @abc.abstractmethod
    def reservation_expire(self, context):
        """expire all reservations which has been expired"""

    @abc.abstractmethod
    def key_pair_create(self, context, values):
        """Create a key_pair from the values dictionary."""
        return IMPL.key_pair_create(context, values)

    @abc.abstractmethod
    def key_pair_destroy(self, context, user_id, name):
        """Destroy the key_pair or raise if it does not exist."""
        return IMPL.key_pair_destroy(context, user_id, name)

    @abc.abstractmethod
    def key_pair_get(self, context, user_id, name):
        """Get a key_pair or raise if it does not exist."""
        return IMPL.key_pair_get(context, user_id, name)

    @abc.abstractmethod
    def key_pair_get_all_by_user(self, context, user_id):
        """Get all key_pairs by user."""
        return IMPL.key_pair_get_all_by_user(context, user_id)

    @abc.abstractmethod
    def key_pair_count_by_user(self, context, user_id):
        """Count number of key pairs for the given user ID."""
        return IMPL.key_pair_count_by_user(context, user_id)
