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

from oslo_db import api as oslo_db_api
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import utils as sqlalchemyutils
from oslo_log import log as logging
from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy import orm
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql import true

from mogan.common import exception
from mogan.common.i18n import _
from mogan.db import api
from mogan.db.sqlalchemy import models


_CONTEXT = threading.local()
LOG = logging.getLogger(__name__)


def get_backend():
    """The backend is this module itself."""
    return Connection()


def _session_for_read():
    return enginefacade.reader.using(_CONTEXT)


# Please add @oslo_db_api.retry_on_deadlock decorator to all methods using
# _session_for_write (as deadlocks happen on write), so that oslo_db is able
# to retry in case of deadlocks.
def _session_for_write():
    return enginefacade.writer.using(_CONTEXT)


def model_query(context, model, *args, **kwargs):
    """Query helper for simpler session usage.

    :param context: Context of the query
    :param model: Model to query. Must be a subclass of ModelBase.
    :param args: Arguments to query. If None - model is used.

    Keyword arguments:

    :keyword project_only:
      If set to True, then will do query filter with context's project_id.
      if set to False or absent, then will not do query filter with context's
      project_id.
    :type project_only: bool
    """
    if kwargs.pop("project_only", False):
        kwargs["project_id"] = context.tenant

    with _session_for_read() as session:
        query = sqlalchemyutils.model_query(
            model, session, args, **kwargs)
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
        raise exception.InvalidParameterValue(identity=value)


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        self.QUOTA_SYNC_FUNCTIONS = {'_sync_servers': self._sync_servers,
                                     '_sync_keypairs': self._sync_keypairs}
        pass

    def _add_servers_filters(self, context, query, filters):
        if filters is None:
            filters = []
        if 'name' in filters:
            name_start_with = filters['name']
            query = query.filter(models.Server.name.like(
                "%" + name_start_with + "%"))
        if 'status' in filters:
            query = query.filter_by(status=filters['status'])
        if 'flavor_uuid' in filters or 'flavor_name' in filters:
            if 'flavor_name' in filters:
                flavor_query = model_query(context, models.Flavors).filter_by(
                    name=filters['flavor_name'])
                filters['flavor_uuid'] = flavor_query.first().uuid
            query = query.filter_by(flavor_uuid=filters['flavor_uuid'])
        if 'image_uuid' in filters:
            query = query.filter_by(image_uuid=filters['image_uuid'])
        if 'node_uuid' in filters:
            query = query.filter_by(node_uuid=filters['node_uuid'])
        return query

    @oslo_db_api.retry_on_deadlock
    def flavor_create(self, context, values):
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        if not values.get('description'):
            values['description'] = ""

        flavor = models.Flavors()
        flavor.update(values)

        with _session_for_write() as session:
            try:
                session.add(flavor)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.FlavorAlreadyExists(name=values['name'])
            return flavor

    def flavor_get(self, context, flavor_uuid):
        query = model_query(context, models.Flavors).filter_by(
            uuid=flavor_uuid)

        if not context.is_admin:
            query = query.filter_by(disabled=False)
            the_filter = [models.Flavors.is_public == true()]
            the_filter.extend([
                models.Flavors.projects.has(project_id=context.project_id)
            ])
            query = query.filter(or_(*the_filter))

        try:
            return query.one()
        except NoResultFound:
            raise exception.FlavorNotFound(
                flavor_id=flavor_uuid)

    @oslo_db_api.retry_on_deadlock
    def flavor_update(self, context, flavor_id, values):
        with _session_for_write():
            query = model_query(context, models.Flavors)
            query = add_identity_filter(query, flavor_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.FlavorNotFound(
                    flavor_id=flavor_id)

            ref.update(values)
            return ref

    def flavor_get_all(self, context):
        query = model_query(context, models.Flavors)
        if not context.is_admin:
            query = query.filter_by(disabled=False)
            the_filter = [models.Flavors.is_public == true()]
            the_filter.extend([
                models.Flavors.projects.has(project_id=context.project_id)
            ])
            query = query.filter(or_(*the_filter))

        return query.all()

    @oslo_db_api.retry_on_deadlock
    def flavor_destroy(self, context, flavor_uuid):
        # check if the flavor is in use
        query = model_query(
            context, models.Server).filter_by(flavor_uuid=flavor_uuid)
        if query.first():
            raise exception.FlavorInUse(flavor_id=flavor_uuid)

        with _session_for_write():
            flavor_id = _get_id_from_flavor(context, flavor_uuid)

            # Clean up all access related to this flavor
            project_query = model_query(
                context,
                models.FlavorProjects).filter_by(
                flavor_id=flavor_id)
            project_query.delete()

            # Then delete the type record
            query = model_query(context, models.Flavors)
            query = add_identity_filter(query, flavor_uuid)

            count = query.delete()
            if count != 1:
                raise exception.FlavorNotFound(
                    flavor_id=flavor_uuid)

    @oslo_db_api.retry_on_deadlock
    def server_create(self, context, values):
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        server_nics = values.pop('nics', [])
        server = models.Server()
        server.update(values)
        nic_refs = []
        for nic in server_nics:
            nic_ref = models.ServerNic()
            nic_ref.update(nic)
            nic_refs.append(nic_ref)
        with _session_for_write() as session:
            try:
                session.add(server)
                for nic_r in nic_refs:
                    session.add(nic_r)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.ServerAlreadyExists(name=values['name'])
            return server

    def server_get(self, context, server_id):
        query = model_query(
            context,
            models.Server).filter_by(uuid=server_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ServerNotFound(server=server_id)

    def server_get_all(self, context, project_only, filters=None):
        query = model_query(context, models.Server,
                            project_only=project_only)
        query = self._add_servers_filters(context, query, filters)
        return query.all()

    @oslo_db_api.retry_on_deadlock
    def server_destroy(self, context, server_id):
        with _session_for_write():
            query = model_query(context, models.Server)
            query = add_identity_filter(query, server_id)

            nics_query = model_query(context, models.ServerNic).filter_by(
                server_uuid=server_id)
            nics_query.delete()

            faults_query = model_query(
                context,
                models.ServerFault).filter_by(server_uuid=server_id)
            faults_query.delete()
            count = query.delete()
            if count != 1:
                raise exception.ServerNotFound(server=server_id)

    def server_update(self, context, server_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Server.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_server(context, server_id, values)
        except db_exc.DBDuplicateEntry as e:
            if 'name' in e.columns:
                raise exception.DuplicateName(name=values['name'])

    @oslo_db_api.retry_on_deadlock
    def _do_update_server(self, context, server_id, values):
        with _session_for_write():
            query = model_query(context, models.Server)
            query = add_identity_filter(query, server_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ServerNotFound(server=server_id)

            ref.update(values)
        return ref

    def flavor_access_get(self, context, flavor_uuid):
        flavor_id = _get_id_from_flavor(context, flavor_uuid)
        return _flavor_access_query(context, flavor_id)

    @oslo_db_api.retry_on_deadlock
    def flavor_access_add(self, context, flavor_uuid, project_id):
        flavor_id = _get_id_from_flavor(context, flavor_uuid)
        access_ref = models.FlavorProjects()
        access_ref.update({"flavor_id": flavor_id,
                           "project_id": project_id})
        with _session_for_write() as session:
            try:
                session.add(access_ref)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.FlavorAccessExists(flavor_id=flavor_uuid,
                                                   project_id=project_id)
        return access_ref

    @oslo_db_api.retry_on_deadlock
    def flavor_access_remove(self, context, flavor_id, project_id):
        with _session_for_write():
            count = _flavor_access_query(context, flavor_id). \
                filter_by(project_id=project_id). \
                delete(synchronize_session=False)

        if count == 0:
            raise exception.FlavorAccessNotFound(flavor_id=flavor_id,
                                                 project_id=project_id)

    @oslo_db_api.retry_on_deadlock
    def server_nic_delete(self, context, port_id):
        with _session_for_write():
            query = model_query(context, models.ServerNic).filter_by(
                port_id=port_id)
            count = query.delete()
        if count != 1:
            raise exception.PortNotFound(port_id=port_id)

    @oslo_db_api.retry_on_deadlock
    def server_nic_update_or_create(self, context, port_id, values):
        with _session_for_write() as session:
            query = model_query(context, models.ServerNic).filter_by(
                port_id=port_id)
            nic = query.first()
            if not nic:
                nic = models.ServerNic()
            values.update(port_id=port_id)
            nic.update(values)
            session.add(nic)
            session.flush()
        return nic

    def server_nics_get_by_server_uuid(self, context, server_uuid):
        return model_query(context, models.ServerNic).filter_by(
            server_uuid=server_uuid).all()

    @oslo_db_api.retry_on_deadlock
    def server_fault_create(self, context, values):
        """Create a new ServerFault."""

        fault = models.ServerFault()
        fault.update(values)

        with _session_for_write() as session:
            session.add(fault)
            session.flush()
            return fault

    def server_fault_get_by_server_uuids(self, context, server_uuids):
        """Get all server faults for the provided server_uuids."""
        if not server_uuids:
            return {}

        rows = model_query(context, models.ServerFault).\
            filter(models.ServerFault.server_uuid.in_(server_uuids)).\
            order_by(desc("created_at"), desc("id")).all()

        output = {}
        for server_uuid in server_uuids:
            output[server_uuid] = []

        for row in rows:
            data = dict(row)
            output[row['server_uuid']].append(data)

        return output

    def quota_get(self, context, project_id, resource_name):
        query = model_query(
            context,
            models.Quota).filter_by(project_id=project_id,
                                    resource_name=resource_name)
        try:
            return query.one()
        except NoResultFound:
            raise exception.QuotaNotFound(quota_name=resource_name)

    @oslo_db_api.retry_on_deadlock
    def quota_create(self, context, values):
        quota = models.Quota()
        quota.update(values)

        with _session_for_write() as session:
            try:
                session.add(quota)
                session.flush()
            except db_exc.DBDuplicateEntry:
                project_id = values['project_id']
                raise exception.QuotaAlreadyExists(name=values['name'],
                                                   project_id=project_id)
            return quota

    def quota_get_all(self, context, project_only):
        return model_query(context, models.Quota, project_only=project_only)

    @oslo_db_api.retry_on_deadlock
    def quota_destroy(self, context, project_id, resource_name):
        with _session_for_write():
            query = model_query(context, models.Quota)
            query = query.filter_by(project_id=project_id,
                                    resource_name=resource_name)

            count = query.delete()
            if count != 1:
                raise exception.QuotaNotFound(quota_name=resource_name)

    @oslo_db_api.retry_on_deadlock
    def _do_update_quota(self, context, project_id, resource_name, updates):
        with _session_for_write():
            query = model_query(context, models.Quota)
            query = query.filter_by(project_id=project_id,
                                    resource_name=resource_name)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.QuotaNotFound(quota_name=resource_name)

            ref.update(updates)
        return ref

    def quota_update(self, context, project_id, resource_name, updates):
        if 'resource_name' in updates or 'project_id' in updates:
            msg = _("Cannot overwrite resource_name/project_id for "
                    "an existing Quota.")
            raise exception.InvalidParameterValue(err=msg)
        try:
            return self._do_update_quota(context, project_id, resource_name,
                                         updates)
        except db_exc.DBDuplicateEntry:
            pass

    def quota_get_all_by_project(self, context, project_id):
        return model_query(context, models.Quota, project_id=project_id)

    def quota_usage_get_all_by_project(self, context, project_id):
        rows = model_query(context, models.QuotaUsage,
                           project_id=project_id)
        result = {'project_id': project_id}
        for row in rows:
            result[row.resource_name] = dict(in_use=row.in_use,
                                             reserved=row.reserved)
        return result

    def quota_allocated_get_all_by_project(self, context, project_id):
        rows = model_query(context, models.Quota,
                           project_id=project_id)
        result = {'project_id': project_id}
        for row in rows:
            result[row.resource_name] = row.allocated
        return result

    def _get_quota_usages(self, context, project_id):
        # Broken out for testability
        rows = model_query(context, models.QuotaUsage,
                           project_id=project_id).\
            order_by(models.QuotaUsage.id.asc()).\
            with_lockmode('update').all()
        return {row.resource_name: row for row in rows}

    @oslo_db_api.retry_on_deadlock
    def quota_allocated_update(self, context, project_id, resource, allocated):
        with _session_for_write():
            quota_ref = self.quota_get(context, project_id, resource)
            quota_ref.update({'allocated': allocated})
        return quota_ref

    def _quota_usage_create(self, context, project_id, resource, in_use,
                            reserved, until_refresh, session=None):
        quota_usage_ref = models.QuotaUsage()
        quota_usage_ref.project_id = project_id
        quota_usage_ref.resource_name = resource
        quota_usage_ref.in_use = in_use
        quota_usage_ref.reserved = reserved
        quota_usage_ref.until_refresh = until_refresh
        try:
            session.add(quota_usage_ref)
            session.flush()
        except db_exc.DBDuplicateEntry:
            raise exception.QuotaAlreadyExists(name=resource,
                                               project_id=project_id)
        return quota_usage_ref

    def _reservation_create(self, context, uuid, usage, project_id, resource,
                            delta, expire, session=None, allocated_id=None):
        usage_id = usage['id'] if usage else None
        reservation_ref = models.Reservation()
        reservation_ref.uuid = uuid
        reservation_ref.usage_id = usage_id
        reservation_ref.project_id = project_id
        reservation_ref.resource_name = resource
        reservation_ref.delta = delta
        reservation_ref.expire = expire
        reservation_ref.allocated_id = allocated_id
        try:
            session.add(reservation_ref)
            session.flush()
        except db_exc.DBDuplicateEntry:
            raise exception.ReservationAlreadyExists(name=resource,
                                                     project_id=project_id)
        return reservation_ref

    def _sync_servers(self, context, project_id):
        query = model_query(context, models.Server).\
            filter_by(project_id=project_id).all()
        return {'servers': len(query) or 0}

    def _sync_keypairs(self, context, project_id):
        query = model_query(context, models.KeyPair).\
            filter_by(project_id=project_id).all()
        return {'keypairs': len(query) or 0}

    @oslo_db_api.retry_on_deadlock
    def quota_reserve(self, context, resources, quotas, deltas, expire,
                      until_refresh, max_age, project_id,
                      is_allocated_reserve=False):
        # NOTE(wanghao): Now we still doesn't support contenxt.elevated() yet.
        # We can support it later.
        elevated = context
        with _session_for_write() as session:
            if project_id is None:
                project_id = context.project_id
            # Get the current usages
            usages = self._get_quota_usages(context, project_id)
            allocated = self.quota_allocated_get_all_by_project(context,
                                                                project_id)
            allocated.pop('project_id')

            # Handle usage refresh
            work = set(deltas.keys())
            while work:
                resource = work.pop()

                # Do we need to refresh the usage?
                refresh = False
                if resource not in usages:
                    usages[resource] = self._quota_usage_create(
                        elevated, project_id, resource, 0, 0,
                        until_refresh or None, session=session)
                    refresh = True
                elif usages[resource].in_use < 0:
                    refresh = True
                elif usages[resource].until_refresh is not None:
                    usages[resource].until_refresh -= 1
                    if usages[resource].until_refresh <= 0:
                        refresh = True
                elif max_age and usages[resource].updated_at is not None and (
                    (usages[resource].updated_at -
                        timeutils.utcnow()).seconds >= max_age):
                    refresh = True

                # OK, refresh the usage
                if refresh:
                    # Grab the sync routine
                    sync = self.QUOTA_SYNC_FUNCTIONS[resources[resource].sync]
                    updates = sync(elevated, project_id)
                    for res, in_use in updates.items():
                        # Make sure we have a destination for the usage!
                        if res not in usages:
                            usages[res] = self._quota_usage_create(
                                elevated, project_id, res, 0, 0,
                                until_refresh or None, session=session)

                        # Update the usage
                        usages[res].in_use = in_use
                        usages[res].until_refresh = until_refresh or None

                        # Because more than one resource may be refreshed
                        # by the call to the sync routine, and we don't
                        # want to double-sync, we make sure all refreshed
                        # resources are dropped from the work set.
                        work.discard(res)

            # Check for deltas that would go negative
            if is_allocated_reserve:
                unders = [r for r, delta in deltas.items()
                          if delta < 0 and delta + allocated.get(r, 0) < 0]
            else:
                unders = [r for r, delta in deltas.items()
                          if delta < 0 and delta + usages[r].in_use < 0]

            # Now, let's check the quotas
            overs = [r for r, delta in deltas.items()
                     if quotas[r] >= 0 and delta >= 0 and
                     quotas[r] < delta + usages[r].total + allocated.get(r, 0)]

            # Create the reservations
            if not overs:
                reservations = []
                for resource, delta in deltas.items():
                    usage = usages[resource]
                    allocated_id = None
                    if is_allocated_reserve:
                        try:
                            quota = self.quota_get(context, project_id,
                                                   resource)
                        except exception.ProjectQuotaNotFound:
                            # If we were using the default quota, create DB
                            # entry
                            quota = self.quota_create(context,
                                                      project_id,
                                                      resource,
                                                      quotas[resource], 0)
                        # Since there's no reserved/total for allocated, update
                        # allocated immediately and subtract on rollback
                        # if needed
                        self.quota_allocated_update(context, project_id,
                                                    resource,
                                                    quota.allocated + delta)
                        allocated_id = quota.id
                        usage = None
                    reservation = self._reservation_create(
                        elevated, uuidutils.generate_uuid(), usage, project_id,
                        resource, delta, expire, session=session,
                        allocated_id=allocated_id)

                    reservations.append(reservation)

                    # Also update the reserved quantity
                    if delta > 0 and not is_allocated_reserve:
                        usages[resource].reserved += delta

        if unders:
            LOG.warning("Change will make usage less than 0 for the "
                        "following resources: %s", unders)
        if overs:
            usages = {k: dict(in_use=v.in_use, reserved=v.reserved,
                              allocated=allocated.get(k, 0))
                      for k, v in usages.items()}
            raise exception.OverQuota(overs=sorted(overs), quotas=quotas,
                                      usages=usages)
        return reservations

    def _dict_with_usage_id(self, usages):
        return {row.id: row for row in usages.values()}

    @oslo_db_api.retry_on_deadlock
    def reservation_commit(self, context, reservations, project_id):
        with _session_for_write():
            usages = self._get_quota_usages(context, project_id)
            usages = self._dict_with_usage_id(usages)

            for reservation in reservations:
                # Allocated reservations will have already been bumped
                if not reservation.allocated_id:
                    usage = usages[reservation.usage_id]
                    if reservation.delta >= 0:
                        usage.reserved -= reservation.delta
                    usage.in_use += reservation.delta

                query = model_query(context, models.Reservation)
                query = query.filter_by(uuid=reservation.uuid)
                count = query.delete()
                if count != 1:
                    raise exception.ReservationNotFound(uuid=reservation.uuid)

    @oslo_db_api.retry_on_deadlock
    def reservation_rollback(self, context, reservations, project_id):
        with _session_for_write():
            usages = self._get_quota_usages(context, project_id)
            usages = self._dict_with_usage_id(usages)
            for reservation in reservations:
                if reservation.allocated_id:
                    reservation.quota.allocated -= reservation.delta
                else:
                    usage = usages[reservation.usage_id]
                    if reservation.delta >= 0:
                        usage.reserved -= reservation.delta

                query = model_query(context, models.Reservation)
                query = query.filter_by(uuid=reservation.uuid)
                count = query.delete()
                if count != 1:
                    raise exception.ReservationNotFound(uuid=reservation.uuid)

    @oslo_db_api.retry_on_deadlock
    def reservation_expire(self, context):
        with _session_for_write() as session:
            current_time = timeutils.utcnow()
            results = model_query(context, models.Reservation).\
                filter(models.Reservation.expire < current_time).\
                all()

            if results:
                for reservation in results:
                    if reservation.delta >= 0:
                        if reservation.allocated_id:
                            reservation.quota.allocated -= reservation.delta
                            reservation.quota.save(session=session)
                        else:
                            reservation.usage.reserved -= reservation.delta
                            reservation.usage.save(session=session)

                    query = model_query(context, models.Reservation)
                    query = query.filter_by(uuid=reservation.uuid)
                    count = query.delete()
                    if count != 1:
                        uuid = reservation.uuid
                        raise exception.ReservationNotFound(uuid=uuid)

    @oslo_db_api.retry_on_deadlock
    def key_pair_create(self, context, values):
        key_pair_ref = models.KeyPair()
        key_pair_ref.update(values)
        with _session_for_write() as session:
            try:
                session.add(key_pair_ref)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.KeypairExists(key_name=values['name'])
            return key_pair_ref

    @oslo_db_api.retry_on_deadlock
    def key_pair_destroy(self, context, user_id, name):
        with _session_for_write():
            result = model_query(context, models.KeyPair).filter_by(
                user_id=user_id).filter_by(name=name).delete()
        if not result:
            raise exception.KeypairNotFound(user_id=user_id, name=name)

    def key_pair_get(self, context, user_id, name):
        result = model_query(context, models.KeyPair).filter_by(
            user_id=user_id).filter_by(name=name).first()
        if not result:
            raise exception.KeypairNotFound(user_id=user_id, name=name)
        return result

    def key_pair_get_all_by_user(self, context, user_id):
        query = model_query(context, models.KeyPair).filter_by(user_id=user_id)
        return query.all()

    def key_pair_count_by_user(self, context, user_id):
        return model_query(context, models.KeyPair).filter_by(
            user_id=user_id).count()

    @oslo_db_api.retry_on_deadlock
    def aggregate_create(self, context, values):
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()
        metadata = values.pop('metadata', None)

        with _session_for_write() as session:
            query = model_query(context, models.Aggregate).filter_by(
                name=values['name']).options(joinedload("_metadata"))
            aggregate = query.first()
            if not aggregate:
                aggregate = models.Aggregate()
                aggregate.update(values)
                aggregate.save(session=session)
                # We don't want these to be lazy loaded later.  We know there
                # is nothing here since we just created this aggregate.
                aggregate._metadata = []
            else:
                raise exception.AggregateNameExists(name=values['name'])
            if metadata:
                self.aggregate_metadata_update_or_create(
                    context, aggregate.id, metadata)
                # NOTE(pkholkin): '_metadata' attribute was updated during
                # 'aggregate_metadata_create_or_update' method, so it should
                # be expired and read from db
                session.expire(aggregate, ['_metadata'])
                aggregate._metadata
            return aggregate

    def aggregate_get(self, context, aggregate_id):
        query = model_query(context, models.Aggregate).filter_by(
            uuid=aggregate_id).options(joinedload("_metadata"))

        try:
            result = query.one()
        except NoResultFound:
            raise exception.AggregateNotFound(aggregate=aggregate_id)
        return result

    def aggregate_update(self, context, aggregate_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing aggregate.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            result = self._do_update_aggregate(context, aggregate_id, values)
        except db_exc.DBDuplicateEntry as e:
            if 'name' in e.columns:
                raise exception.DuplicateName(name=values['name'])
        return result

    @oslo_db_api.retry_on_deadlock
    def _do_update_aggregate(self, context, aggregate_id, values):
        with _session_for_write():
            query = model_query(context, models.Aggregate)
            query = add_identity_filter(query, aggregate_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.AggregateNotFound(aggregate=aggregate_id)
            ref.update(values)
        return ref

    def aggregate_get_all(self, context):
        aggregates = model_query(context, models.Aggregate). \
            options(joinedload("_metadata")).all()
        return aggregates

    @oslo_db_api.retry_on_deadlock
    def aggregate_destroy(self, context, aggregate_id):
        with _session_for_write():
            # First clean up all metadata related to this type
            meta_query = model_query(
                context,
                models.AggregateMetadata).filter_by(
                aggregate_id=aggregate_id)
            meta_query.delete()

            query = model_query(
                context,
                models.Aggregate).filter_by(id=aggregate_id)

            count = query.delete()
            if count != 1:
                raise exception.AggregateNotFound(aggregate=aggregate_id)

    def aggregate_get_by_metadata_key(self, context, key):
        query = model_query(context, models.Aggregate)
        query = query.join("_metadata")
        query = query.filter(models.AggregateMetadata.key == key)
        query = query.options(contains_eager("_metadata"))
        return query.all()

    def aggregate_get_by_metadata(self, context, key, value):
        query = model_query(context, models.Aggregate)
        query = query.join("_metadata")
        query = query.filter(and_(models.AggregateMetadata.key == key,
                                  models.AggregateMetadata.value == value))
        query = query.options(contains_eager("_metadata"))
        return query.all()

    @oslo_db_api.retry_on_deadlock
    def aggregate_metadata_update_or_create(self, context, aggregate_id,
                                            metadata, max_retries=10):
        for attempt in range(max_retries):
            with _session_for_write() as session:
                try:
                    query = model_query(
                        context, models.AggregateMetadata).\
                        filter_by(aggregate_id=aggregate_id).\
                        filter(models.AggregateMetadata.key.in_(
                            metadata.keys())).with_lockmode('update').all()

                    already_existing_keys = set()
                    for meta_ref in query:
                        key = meta_ref["key"]
                        meta_ref.update({"value": metadata[key]})
                        already_existing_keys.add(key)

                    for key, value in metadata.items():
                        if key in already_existing_keys:
                            continue
                        metadata_ref = models.AggregateMetadata()
                        metadata_ref.update({"key": key,
                                             "value": value,
                                             "aggregate_id": aggregate_id})
                        session.add(metadata_ref)
                        session.flush()

                    return metadata
                except db_exc.DBDuplicateEntry:
                    # a concurrent transaction has been committed,
                    # try again unless this was the last attempt
                    if attempt < max_retries - 1:
                        LOG.warning("Add metadata failed for aggregate %(id)s "
                                    "after %(retries)s retries",
                                    {"id": aggregate_id,
                                     "retries": max_retries})

    def aggregate_metadata_get(self, context, aggregate_id):
        rows = model_query(context, models.AggregateMetadata). \
            filter_by(aggregate_id=aggregate_id).all()
        return {row["key"]: row["value"] for row in rows}

    @oslo_db_api.retry_on_deadlock
    def aggregate_metadata_delete(self, context, aggregate_id, key):
        with _session_for_write():
            result = model_query(context, models.AggregateMetadata). \
                filter_by(aggregate_id=aggregate_id). \
                filter(models.AggregateMetadata.key == key). \
                delete(synchronize_session=False)
        # did not find the metadata
        if result == 0:
            raise exception.AggregateMetadataNotFound(
                key=key, aggregate_id=aggregate_id)

    @oslo_db_api.retry_on_deadlock
    def _server_group_policies_add(self, context, group_id, policies,
                                   delete=False):
        all_policies = set(policies)
        query = model_query(context, models.ServerGroupPolicy).filter_by(
            group_id=group_id)
        if delete:
            with _session_for_write():
                query.filter(~models.ServerGroupPolicy.policy.in_(
                    all_policies)).delete(synchronize_session=False)
        query = query.filter(models.ServerGroupPolicy.policy.in_(all_policies))
        already_existing = set()
        for policy_ref in query.all():
            already_existing.add(policy_ref.policy)
        with _session_for_write() as session:
            for policy in all_policies:
                if policy in already_existing:
                    continue
                policy_ref = models.ServerGroupPolicy()
                policy_ref.update({'policy': policy,
                                   'group_id': group_id})
                session.add(policy_ref)
        return policies

    @oslo_db_api.retry_on_deadlock
    def _server_group_members_add(self, context, group_id, members,
                                  delete=False):
        all_members = set(members)
        query = model_query(context, models.ServerGroupMember).filter_by(
            group_id=group_id)
        if delete:
            with _session_for_write():
                query.filter(~models.ServerGroupMember.server_uuid.in_(
                    all_members)).delete(synchronize_session=False)
        query = query.filter(models.ServerGroupMember.server_uuid.in_(
            all_members))
        already_existing = set()
        for member_ref in query.all():
            already_existing.add(member_ref.server_uuid)
        with _session_for_write() as session:
            for server_uuid in members:
                if server_uuid in already_existing:
                    continue
                member_ref = models.ServerGroupMember()
                member_ref.update({'server_uuid': server_uuid,
                                   'group_id': group_id})
                session.add(member_ref)
        return members

    @oslo_db_api.retry_on_deadlock
    def server_group_create(self, context, values, policies=None,
                            members=None):
        """Create a new group."""
        uuid = values.get('uuid', None)
        if uuid is None:
            uuid = uuidutils.generate_uuid()
            values['uuid'] = uuid
        with _session_for_write() as session:
            try:
                server_group_ref = models.ServerGroup()
                server_group_ref.update(values)
                server_group_ref.save(session)
            except db_exc.DBDuplicateEntry:
                raise exception.ServerGroupExists(group_uuid=values['uuid'])
        if policies:
            self._server_group_policies_add(context, server_group_ref.id,
                                            policies)
        if members:
            self._server_group_members_add(context, server_group_ref.id,
                                           members)

        return self.server_group_get(context, uuid)

    def server_group_get(self, context, group_uuid):
        """Get a specific group by uuid."""
        columns_to_join = ['_policies', '_members']
        query = model_query(context, models.ServerGroup)
        for c in columns_to_join:
            query = query.options(orm.joinedload(c))
        query = query.filter(models.ServerGroup.uuid == group_uuid)
        group = query.first()
        if not group:
            raise exception.ServerGroupNotFound(group_uuid=group_uuid)
        return group

    @oslo_db_api.retry_on_deadlock
    def server_group_update(self, context, group_uuid, values):
        """Update the attributes of a group.

        If values contains a metadata key, it updates the aggregate metadata
        too. Similarly for the policies and members.
        """
        group_query = model_query(context, models.ServerGroup).filter_by(
            uuid=group_uuid)
        group = group_query.first()
        if not group:
            raise exception.ServerGroupNotFound(group_uuid=group_uuid)

        policies = values.get('policies')
        if policies is not None:
            self._server_group_policies_add(context,
                                            group.id,
                                            values.pop('policies'),
                                            True)
        members = values.get('members')
        if members is not None:
            self._server_group_members_add(context,
                                           group.id,
                                           values.pop('members'),
                                           True)
        with _session_for_write():
            group_query.update(values)

        if policies:
            values['policies'] = policies
        if members:
            values['members'] = members

    @oslo_db_api.retry_on_deadlock
    def server_group_delete(self, context, group_uuid):
        """Delete a group."""
        query = model_query(context, models.ServerGroup).filter_by(
            uuid=group_uuid)
        group = query.first()
        if not group:
            raise exception.ServerGroupNotFound(group_uuid=group_uuid)
        group_id = group.id
        with _session_for_write():
            query.delete()
        # Delete policies and members
        instance_models = [models.ServerGroupPolicy,
                           models.ServerGroupMember]
        for model in instance_models:
            model_query(context, model).filter_by(group_id=group_id).delete()

    def server_group_get_all(self, context, project_id=None):
        """Get all groups."""
        columns_to_join = ['_policies', '_members']
        query = model_query(context, models.ServerGroup)
        for c in columns_to_join:
            query = query.options(orm.joinedload(c))
        if project_id is not None:
            query = query.filter_by(project_id=project_id)
        return query.all()


def _get_id_from_flavor_query(context, type_id):
    return model_query(context, models.Flavors). \
        filter_by(uuid=type_id)


def _get_id_from_flavor(context, type_id):
    result = _get_id_from_flavor_query(context, type_id).first()
    if not result:
        raise exception.FlavorNotFound(flavor_id=type_id)
    return result.id


def _flavor_access_query(context, flavor_id):
    return model_query(context, models.FlavorProjects). \
        filter_by(flavor_id=flavor_id)
