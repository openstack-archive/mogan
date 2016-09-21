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

"""SQLAlchemy storage backend."""

import threading

from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import enginefacade
from oslo_utils import strutils
from oslo_utils import uuidutils
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload

from nimble.common import exception
from nimble.db import api
from nimble.db.sqlalchemy import models


_CONTEXT = threading.local()


def get_backend():
    """The backend is this module itself."""
    return Connection()


def _session_for_read():
    return enginefacade.reader.using(_CONTEXT)


def _session_for_write():
    return enginefacade.writer.using(_CONTEXT)


def model_query(model, *args, **kwargs):
    """Query helper for simpler session usage.

    :param session: if present, the session to use
    """

    with _session_for_read() as session:
        query = session.query(model, *args)
        return query


def add_identity_filter(query, value):
    """Adds an identity filter to a query.

    Filters results by ID, if supplied value is a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if strutils.is_int_like(value):
        return query.filter_by(id=value)
    elif uuidutils.is_uuid_like(value):
        return query.filter_by(uuid=value)
    else:
        raise exception.InvalidIdentity(identity=value)


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def instance_type_create(self, values):
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        instance_type = models.InstanceTypes()
        instance_type.update(values)

        with _session_for_write() as session:
            try:
                session.add(instance_type)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.InstanceTypeAlreadyExists(name=values['name'])
            return instance_type

    def instance_type_get(self, instance_type_uuid):
        query = model_query(models.InstanceTypes).filter_by(
            uuid=instance_type_uuid).options(joinedload('extra_specs'))
        try:
            return query.one()
        except NoResultFound:
            raise exception.InstanceTypeNotFound(
                instance_type=instance_type_uuid)

    def instance_type_get_all(self):
        return model_query(models.InstanceTypes)

    def instance_type_destroy(self, instance_type_uuid):
        with _session_for_write():
            query = model_query(models.InstanceTypes)
            query = add_identity_filter(query, instance_type_uuid)

            count = query.delete()
            if count != 1:
                raise exception.InstanceTypeNotFound(
                    instance_type=instance_type_uuid)

    def instance_create(self, values):
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        instance = models.Instance()
        instance.update(values)

        with _session_for_write() as session:
            try:
                session.add(instance)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.InstanceAlreadyExists(name=values['name'])
            return instance

    def instance_get(self, instance_id):
        query = model_query(models.Instance).filter_by(uuid=instance_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.InstanceNotFound(instance=instance_id)

    def instance_get_all(self):
        return model_query(models.Instance)

    def instance_destroy(self, instance_id):
        with _session_for_write():
            query = model_query(models.Instance)
            query = add_identity_filter(query, instance_id)

            count = query.delete()
            if count != 1:
                raise exception.InstanceNotFound(instance=instance_id)

    def update_instance(self, instance_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Instance.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_instance(instance_id, values)
        except db_exc.DBDuplicateEntry as e:
            if 'name' in e.columns:
                raise exception.DuplicateName(name=values['name'])

    def _do_update_instance(self, instance_id, values):
        with _session_for_write():
            query = model_query(models.Instance)
            query = add_identity_filter(query, instance_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.InstanceNotFound(instance=instance_id)

            ref.update(values)
        return ref

    def extra_specs_update_or_create(self, instance_type_id, specs,
                                     max_retries=10):
        """Create or update instance type extra specs.

        This adds or modifies the key/value pairs specified in the
        extra specs dict argument
        """
        for attempt in range(max_retries):

            try:
                type_id = _type_get_id_from_type(instance_type_id)

                spec_refs = model_query(models.InstanceTypeExtraSpecs,
                                        read_deleted="no"). \
                    filter_by(instance_type_id=type_id). \
                    filter(models.InstanceTypeExtraSpecs.key.in_(specs.keys())). \
                    all()

                existing_keys = set()
                for spec_ref in spec_refs:
                    key = spec_ref["key"]
                    existing_keys.add(key)
                    spec_ref.update({"value": specs[key]})

                for key, value in specs.items():
                    if key in existing_keys:
                        continue

                return specs
            except db_exc.DBDuplicateEntry:
                # a concurrent transaction has been committed,
                # try again unless this was the last attempt
                if attempt == max_retries - 1:
                    raise exception.InstanceTypeExtraSpecUpdateCreateFailed(
                        id=instance_type_id, retries=max_retries)

    def instance_type_extra_specs_get(self, type_id):
        rows = _type_extra_specs_get_query(type_id).all()
        return {row['key']: row['value'] for row in rows}

    def type_extra_specs_delete(self, type_id, key):
        result = _type_extra_specs_get_query(type_id). \
            filter(models.InstanceTypeExtraSpecs.key == key). \
            soft_delete(synchronize_session=False)
        # did not find the extra spec
        if result == 0:
            raise exception.InstanceTypeExtraSpecsNotFound(
                extra_specs_key=key, type_id=type_id)


def _type_get_id_from_type_query(flavor_id):
    return model_query(models.InstanceTypes,
                       (models.InstanceTypes.id,),
                       read_deleted="no"). \
        filter_by(flavorid=flavor_id)


def _type_get_id_from_type(flavor_id):
    result = _type_get_id_from_type_query(flavor_id).first()
    if not result:
        raise exception.InstanceTypeNotFound(flavor_id=flavor_id)
    return result[0]


def _type_extra_specs_get_query(type_id):
    instance_type_id_subq = _type_get_id_from_type_query(type_id)

    return model_query(models.InstanceTypeExtraSpecs,
                       read_deleted="no"). \
        filter_by(instance_type_id=instance_type_id_subq)
