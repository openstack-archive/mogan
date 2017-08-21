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

from oslo_db import exception as db_exc
from oslo_log import log as logging
from oslo_versionedobjects import base as object_base

from mogan.db import api as dbapi
from mogan import objects
from mogan.objects import base
from mogan.objects import fields as object_fields

OPTIONAL_ATTRS = ['nics', 'fault']


LOG = logging.getLogger(__name__)


@base.MoganObjectRegistry.register
class Server(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'uuid': object_fields.UUIDField(nullable=True),
        'name': object_fields.StringField(nullable=True),
        'description': object_fields.StringField(nullable=True),
        'project_id': object_fields.UUIDField(nullable=True),
        'user_id': object_fields.UUIDField(nullable=True),
        'status': object_fields.StringField(nullable=True),
        'power_state': object_fields.StringField(nullable=True),
        'flavor_uuid': object_fields.UUIDField(nullable=True),
        'availability_zone': object_fields.StringField(nullable=True),
        'image_uuid': object_fields.UUIDField(nullable=True),
        'nics': object_fields.ObjectField('ServerNics', nullable=True),
        'fault': object_fields.ObjectField('ServerFault', nullable=True),
        'node_uuid': object_fields.UUIDField(nullable=True),
        'launched_at': object_fields.DateTimeField(nullable=True),
        'metadata': object_fields.FlexibleDictField(nullable=True),
        'locked': object_fields.BooleanField(default=False),
        'locked_by': object_fields.StringField(nullable=True),
        'affinity_zone': object_fields.StringField(nullable=True),
    }

    def __init__(self, context=None, **kwargs):
        server_nics = kwargs.pop('nics', None)
        if server_nics and isinstance(server_nics, list):
            nics_obj = objects.ServerNics(context)
            for nic in server_nics:
                nic_obj = objects.ServerNic(
                    context, server_uuid=kwargs['uuid'], **nic)
                nics_obj.objects.append(nic_obj)
            kwargs['nics'] = nics_obj
        super(Server, self).__init__(context=context, **kwargs)

    @staticmethod
    def _from_db_object(server, db_server, expected_attrs=None):
        """Method to help with migration to objects.

        Converts a database entity to a formal object.

        :param server: An object of the Server class.
        :param db_server: A DB Server model of the object
        :return: The object of the class with the database entity added
        """
        for field in set(server.fields) - set(OPTIONAL_ATTRS):
            if field == 'metadata':
                server[field] = db_server['extra']
            else:
                server[field] = db_server[field]

        if expected_attrs is None:
            expected_attrs = []
        if 'nics' in expected_attrs:
            server._load_server_nics(server._context, server.uuid)
        else:
            server.nics = None
        if 'fault' in expected_attrs:
            server._load_fault(server._context, server.uuid)

        server.obj_reset_changes()
        return server

    def _load_server_nics(self, context, server_uuid):
        self.nics = objects.ServerNics.get_by_server_uuid(
            context=context, server_uuid=server_uuid)

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        servers = []
        for obj in db_objects:
            expected_attrs = ['nics', 'fault']
            servers.append(Server._from_db_object(cls(context), obj,
                                                  expected_attrs))
        return servers

    def _load_fault(self, context, server_uuid):
        self.fault = objects.ServerFault.get_latest_for_server(
            context=context, server_uuid=server_uuid)

    def _save_nics(self, context):
        for nic_obj in self.nics or []:
            nic_obj.save(context)

    def as_dict(self):
        data = dict(self.items())
        if 'nics' in data:
            data.update(nics=data['nics'].as_list_of_dict())
        if 'fault' in data:
            if data['fault'] is not None:
                data.update(fault=data['fault'].as_fault_dict())
            else:
                data.update(fault={})
        return data

    @classmethod
    def list(cls, context, project_only=False, filters=None):
        """Return a list of Server objects."""
        db_servers = cls.dbapi.server_get_all(context,
                                              project_only=project_only,
                                              filters=filters)
        return Server._from_db_object_list(db_servers, cls, context)

    @classmethod
    def get(cls, context, uuid):
        """Find a server and return a Server object."""
        expected_attrs = ['nics', 'fault']
        db_server = cls.dbapi.server_get(context, uuid)
        server = Server._from_db_object(cls(context), db_server,
                                        expected_attrs)
        return server

    def create(self, context=None):
        """Create a Server record in the DB."""
        values = self.obj_get_changes()
        metadata = values.pop('metadata', None)
        if metadata is not None:
            values['extra'] = metadata
        server_nics = values.pop('nics', None)
        if server_nics:
            values['nics'] = server_nics.as_list_of_dict()
        db_server = self.dbapi.server_create(context, values)
        expected_attrs = None
        if server_nics:
            expected_attrs = ['nics']
        self._from_db_object(self, db_server, expected_attrs)

    def destroy(self, context=None):
        """Delete the Server from the DB."""
        self.dbapi.server_destroy(context, self.uuid)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this Server."""
        updates = self.obj_get_changes()
        for field in list(updates):
            if (self.obj_attr_is_set(field) and
                    isinstance(self.fields[field], object_fields.ObjectField)
                    and getattr(self, field, None) is not None):
                try:
                    getattr(self, '_save_%s' % field)(context)
                except AttributeError:
                    LOG.exception('No save handler for %s', field,
                                  server=self)
                except db_exc.DBReferenceError as exp:
                    if exp.key != 'server_uuid':
                        raise
                updates.pop(field)

        metadata = updates.pop('metadata', None)
        if metadata is not None:
            updates['extra'] = metadata
        self.dbapi.server_update(context, self.uuid, updates)
        self.obj_reset_changes()

    def refresh(self, context=None):
        """Refresh the object by re-fetching from the DB."""
        current = self.__class__.get(context, self.uuid)
        self.obj_refresh(current)
        self.obj_reset_changes()
