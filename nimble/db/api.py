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


_BACKEND_MAPPING = {'sqlalchemy': 'nimble.db.sqlalchemy.api'}
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

    # Instance Types
    @abc.abstractmethod
    def instance_type_create(self, context, values):
        """Create a new instance type."""

    @abc.abstractmethod
    def instance_type_get(self, context, instance_type_uuid):
        """Get instance type by uuid."""

    def instance_type_update(self, context, instance_type_id, values):
        """Update an instance type."""

    @abc.abstractmethod
    def instance_type_get_all(self, context):
        """Get all instance types."""

    @abc.abstractmethod
    def instance_type_destroy(self, context, instance_type_uuid):
        """Delete an instance type."""

    # Instances
    @abc.abstractmethod
    def instance_create(self, context, values):
        """Create a new instance."""

    @abc.abstractmethod
    def instance_get(self, context, instance_id):
        """Get instance by name."""

    @abc.abstractmethod
    def instance_get_all(self, context):
        """Get all instances."""

    @abc.abstractmethod
    def instance_destroy(self, context, instance_id):
        """Delete an instance."""

    @abc.abstractmethod
    def instance_update(self, context, instance_id, values):
        """Update an instance."""

    @abc.abstractmethod
    def extra_specs_update_or_create(self, context,
                                     instance_type_id, extra_specs):
        """Create or update instance type extra specs.

        This adds or modifies the key/value pairs specified in the
        extra specs dict argument
        """

    @abc.abstractmethod
    def instance_type_extra_specs_get(self, context, type_id):
        """Get instance type extra specs"""

    @abc.abstractmethod
    def type_extra_specs_delete(self, context, instance_type_id, key):
        """Delete instance type extra specs.

        This deletes the key/value pairs specified in the
        extra specs dict argument
        """
