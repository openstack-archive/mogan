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
    def server_get_all(self, context, project_only, filters=None):
        """Get all servers."""

    @abc.abstractmethod
    def server_destroy(self, context, server_id):
        """Delete a server."""

    @abc.abstractmethod
    def server_update(self, context, server_id, values):
        """Update a server."""

    # Flavor access
    @abc.abstractmethod
    def flavor_access_add(self, context, flavor_uuid, project_id):
        """Add flavor access for project."""

    @abc.abstractmethod
    def flavor_access_get(self, context, flavor_uuid):
        """Get flavor access by flavor uuid."""

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

    def server_nic_delete(self, context, port_id):
        """Delete a nic db entry.

        This delete a nic db entry.
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

    @abc.abstractmethod
    def aggregate_create(self, context, values):
        """Create an aggregate from the values dictionary."""
        return IMPL.aggregate_create(context, values)

    @abc.abstractmethod
    def aggregate_update(self, context, aggregate_id, values):
        """Update an aggregate from the values dictionary."""
        return IMPL.aggregate_update(context, aggregate_id, values)

    @abc.abstractmethod
    def aggregate_get(self, context, aggregate_id):
        """Get an aggregate or raise if it does not exist."""
        return IMPL.aggregate_get(context, aggregate_id)

    @abc.abstractmethod
    def aggregate_get_all(self, context):
        """Get all aggregates."""
        return IMPL.aggregate_get_all(context)

    @abc.abstractmethod
    def aggregate_destroy(self, context, aggregate_id):
        """Destroy the aggregate or raise if it does not exist."""
        return IMPL.aggregate_destroy(context, aggregate_id)

    @abc.abstractmethod
    def aggregate_get_by_metadata_key(self, context, key):
        """Get a list of aggregates by metadata key."""
        return IMPL.aggregate_get_by_metadata_key(context, key)

    @abc.abstractmethod
    def aggregate_metadata_update_or_create(self, context, aggregate_id,
                                            metadata):
        """Update/Create aggregates metadata."""
        return IMPL.aggregate_metadata_update_or_create(context, aggregate_id,
                                                        metadata)

    @abc.abstractmethod
    def aggregate_metadata_get(self, context, aggregate_id):
        """Get aggregate metadata by aggregate id."""
        return IMPL.aggregate_metadata_get(context, aggregate_id)

    @abc.abstractmethod
    def aggregate_metadata_delete(self, context, key):
        """Delete aggregate metadata by key."""
        return IMPL.aggregate_metadata_delete(context, key)

    def server_group_create(self, context, values, policies=None,
                            members=None):
        """Create a new group."""
        return IMPL.server_group_create(context, values, policies, members)

    def server_group_get(self, context, group_uuid):
        """Get a specific group by uuid."""
        return IMPL.server_group_get(context, group_uuid)

    def server_group_update(self, context, group_uuid, values):
        """Update the attributes of a group."""
        return IMPL.server_group_update(context, group_uuid, values)

    def server_group_delete(self, context, group_uuid):
        """Delete a group."""
        return IMPL.server_group_delete(context, group_uuid)

    def server_group_get_all(self, context, project_id=None):
        """Get server groups."""
        return IMPL.server_group_get_all(context, project_id)
