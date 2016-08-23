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

    # Flavors
    @abc.abstractmethod
    def flavor_create(self, values):
        """Create a new instance type."""

    @abc.abstractmethod
    def flavor_get(uuid):
        """Get instance type by name."""

    def flavor_get_all():
        """Get all instance types."""

    @abc.abstractmethod
    def flavor_destroy(name):
        """Delete an instance type."""

    # Instances
    @abc.abstractmethod
    def instance_create(self, values):
        """Create a new instance."""

    @abc.abstractmethod
    def instance_get(uuid):
        """Get instance by name."""

    def instance_get_all():
        """Get all instances."""

    @abc.abstractmethod
    def instance_destroy(name):
        """Delete an instance."""
