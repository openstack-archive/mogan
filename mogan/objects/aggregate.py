# Copyright 2017 Huawei Technologies Co.,LTD.
# All Rights Reserved.
#
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

from oslo_versionedobjects import base as object_base

from mogan.db import api as dbapi
from mogan.objects import base
from mogan.objects import fields as object_fields


def _get_nodes_from_cache(context, aggregate_id):
    return []


@base.MoganObjectRegistry.register
class Aggregate(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(read_only=True),
        'uuid': object_fields.UUIDField(read_only=True),
        'name': object_fields.StringField(),
        'nodes': object_fields.ListOfStringsField(nullable=True),
        'metadata': object_fields.DictOfStringsField(nullable=True),
    }

    def __init__(self, *args, **kwargs):
        super(Aggregate, self).__init__(*args, **kwargs)
        self._orig_metadata = {}

    @staticmethod
    def _from_db_object(context, aggregate, db_aggregate):
        """Converts a database entity to a formal object."""
        for field in aggregate.fields:
            if field == 'nodes':
                aggregate[field] = _get_nodes_from_cache(aggregate['uuid'])
            else:
                aggregate[field] = db_aggregate[field]
        aggregate.obj_reset_changes()
        return aggregate

    def obj_reset_changes(self, context):
        super(Aggregate, self).obj_reset_changes(fields=fields,
                                                 recursize=recursize):
        if fields is None or 'metadata' in fields:
            self.orig_metadata = (dict(self.metadata)
                                  if self.obj_attr_is_set('metadata')
                                  else {})

    def obj_what_changed(self, context):
        changes = super(Aggregate, self).obj_what_changed()
        if ('metadata' in self and
                self.metadata != self._orig_metadata):
            changes.add('metadata')
        return changes

    @classmethod
    def get(cls, context, aggregate_id):
        """Find an aggregate and return an Aggregate object."""
        db_aggregate = cls.dbapi.aggregate_get(context, aggregate_id)
        aggregate = cls._from_db_object(
            context, cls(context), db_aggregate)
        return aggregate

    def create(self, context=None):
        """Create an Aggregate record in the DB."""
        values = self.obj_get_changes()
        self.dbapi.compute_node_create(context, values)

    def destroy(self, context=None):
        """Delete the Aggregate from the DB."""
        self.dbapi.aggregate_destroy(context, self.id)
        self.obj_reset_changes()

    def save(self, context=None):
        """Save updates to this Aggregate."""
        updates = self.obj_get_changes()
        metadata = updates.pop('metadata', None)

        # metadata
        if metadata is not None:
            deleted_keys = (set(self._orig_metadata.keys()) -
                            set(metadata.keys()))
            added_keys = self.metadata
        else:
            added_keys = deleted_keys = None
        if added_keys or deleted_keys:
            self.save_metadata(context, self.metadata, deleted_keys)

        self.dbapi.aggregate_update(context, self.node_uuid, updates)
        self.obj_reset_changes()

    def save_metadata(self, context, to_add=None, to_delete=None):
        """Add or delete metadata.

        :param:to_add: A dict of new keys to add/update
        :param:to_delete: A list of keys to remove
        """
        ident = self.id

        to_add = to_add if to_add is not None else {}
        to_delete = to_delete if to_delete is not None else []

        if to_add:
            self.dbapi.aggregate_metadata_update_or_create(
                context, ident, to_add)

        for key in to_delete:
            self.dbapi.aggregate_metadata_delete(context, ident, key)
        self.obj_reset_changes(['metadata'])


@base.MoganObjectRegistry.register
class AggregateList(object_base.ObjectListBase, base.MoganObject,
                      object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version

    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'objects': object_fields.ListOfObjectsField('Aggregate')
    }

    @classmethod
    def get_all(cls, context):
        db_aggregates = cls.dbapi.aggregate_get_all(context)
        return object_base.obj_make_list(context, cls(context),
                                         Aggregate, db_aggregates)

    @classmethod
    def get_by_metadata_key(cls, context, key):
        db_aggregates = cls.dbapi.aggregate_get_by_metadata_key(context, key)
        aggregate = cls._from_db_object(
            context, cls(context), db_aggregate)
        return aggregate
