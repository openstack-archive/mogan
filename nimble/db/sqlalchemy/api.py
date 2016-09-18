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
                raise exception.FlavorAlreadyExists(name=values['name'])
            return instance_type

    def instance_type_get(self, flavor_uuid):
        query = model_query(models.InstanceTypes).filter_by(uuid=flavor_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.FlavorNotFound(flavor=flavor_uuid)

    def instance_type_get_all(self):
        return model_query(models.InstanceTypes)

    def instance_type_destroy(self, flavor_uuid):
        with _session_for_write():
            query = model_query(models.InstanceTypes)
            query = add_identity_filter(query, flavor_uuid)

            count = query.delete()
            if count != 1:
                raise exception.FlavorNotFound(flavor=flavor_uuid)

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
