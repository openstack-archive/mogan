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
from oslo_log import log

from nimble.common import exception
from nimble.db import api
from nimble.db.sqlalchemy import models

LOG = log.getLogger(__name__)


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


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def flavor_create(self, values):
        instance_type = models.InstanceTypes()
        instance_type.update(values)

        with _session_for_write() as session:
            try:
                session.add(instance_type)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.FlavorAlreadyExists(name=values['name'])
            return instance_type

    def flavor_get_all(self):
        return model_query(models.InstanceTypes)
