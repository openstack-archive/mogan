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
from oslo_db.sqlalchemy import utils as sqlalchemyutils
from oslo_log import log as logging
from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import desc

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


def _dict_with_extra_specs(inst_type_query):
    """Takes an instance type query and returns it as a dictionary."""
    inst_type_dict = dict(inst_type_query)
    extra_specs = {x['key']: x['value']
                   for x in inst_type_query['extra_specs']}
    inst_type_dict['extra_specs'] = extra_specs
    return inst_type_dict


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        self.QUOTA_SYNC_FUNCTIONS = {'_sync_instances': self._sync_instances}
        pass

    def instance_type_create(self, context, values):
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        if not values.get('description'):
            values['description'] = ""

        instance_type = models.InstanceTypes()
        instance_type.update(values)

        with _session_for_write() as session:
            try:
                session.add(instance_type)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.InstanceTypeAlreadyExists(uuid=values['uuid'])
            return _dict_with_extra_specs(instance_type)

    def instance_type_get(self, context, instance_type_uuid):
        query = model_query(context, models.InstanceTypes).filter_by(
            uuid=instance_type_uuid).options(joinedload('extra_specs'))
        try:
            return _dict_with_extra_specs(query.one())
        except NoResultFound:
            raise exception.InstanceTypeNotFound(
                type_id=instance_type_uuid)

    def instance_type_update(self, context, instance_type_id, values):
        with _session_for_write():
            query = model_query(context, models.InstanceTypes)
            query = add_identity_filter(query, instance_type_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.InstanceTypeNotFound(
                    type_id=instance_type_id)

            ref.update(values)
            return ref

    def instance_type_get_all(self, context):
        results = model_query(context, models.InstanceTypes)
        return [_dict_with_extra_specs(i) for i in results]

    def instance_type_destroy(self, context, instance_type_uuid):
        with _session_for_write():
            # First clean up all extra specs related to this type
            type_id = _type_get_id_from_type(context, instance_type_uuid)
            extra_query = model_query(
                context,
                models.InstanceTypeExtraSpecs).filter_by(
                instance_type_uuid=type_id)
            extra_query.delete()

            # Then delete the type record
            query = model_query(context, models.InstanceTypes)
            query = add_identity_filter(query, instance_type_uuid)

            count = query.delete()
            if count != 1:
                raise exception.InstanceTypeNotFound(
                    type_id=instance_type_uuid)

    def instance_create(self, context, values):
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        instance_nics = values.pop('nics', [])
        instance = models.Instance()
        instance.update(values)
        nic_refs = []
        for nic in instance_nics:
            nic_ref = models.InstanceNic()
            nic_ref.update(nic)
            nic_refs.append(nic_ref)
        with _session_for_write() as session:
            try:
                session.add(instance)
                for nic_r in nic_refs:
                    session.add(nic_r)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.InstanceAlreadyExists(name=values['name'])
            return instance

    def instance_get(self, context, instance_id):
        query = model_query(
            context,
            models.Instance,
            instance=True).filter_by(uuid=instance_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.InstanceNotFound(instance=instance_id)

    def instance_get_all(self, context, project_only):
        return model_query(context, models.Instance,
                           instance=True, project_only=project_only)

    def instance_destroy(self, context, instance_id):
        with _session_for_write():
            query = model_query(context, models.Instance)
            query = add_identity_filter(query, instance_id)

            nics_query = model_query(context, models.InstanceNic).filter_by(
                instance_uuid=instance_id)
            nics_query.delete()

            faults_query = model_query(
                context,
                models.InstanceFault).filter_by(instance_uuid=instance_id)
            faults_query.delete()
            count = query.delete()
            if count != 1:
                raise exception.InstanceNotFound(instance=instance_id)

    def instance_update(self, context, instance_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Instance.")
            raise exception.InvalidParameterValue(err=msg)

        try:
            return self._do_update_instance(context, instance_id, values)
        except db_exc.DBDuplicateEntry as e:
            if 'name' in e.columns:
                raise exception.DuplicateName(name=values['name'])

    def _do_update_instance(self, context, instance_id, values):
        with _session_for_write():
            query = model_query(context, models.Instance, instance=True)
            query = add_identity_filter(query, instance_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.InstanceNotFound(instance=instance_id)

            ref.update(values)
        return ref

    def compute_node_create(self, context, values):
        compute_node = models.ComputeNode()
        compute_node.update(values)
        with _session_for_write() as session:
            try:
                session.add(compute_node)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.ComputeNodeAlreadyExists(
                    node=values['node_uuid'])
            return compute_node

    def compute_node_get(self, context, node_uuid):
        query = model_query(
            context,
            models.ComputeNode).filter_by(node_uuid=node_uuid). \
            options(joinedload('ports'))
        try:
            return query.one()
        except NoResultFound:
            raise exception.ComputeNodeNotFound(node=node_uuid)

    def compute_node_get_all(self, context):
        return model_query(
            context,
            models.ComputeNode).options(joinedload('ports'))

    def compute_node_get_all_available(self, context):
        return model_query(
            context,
            models.ComputeNode).filter_by(used=False). \
            options(joinedload('ports'))

    def compute_node_destroy(self, context, node_uuid):
        with _session_for_write():
            query = model_query(
                context,
                models.ComputeNode).filter_by(node_uuid=node_uuid)

            port_query = model_query(context, models.ComputePort).filter_by(
                node_uuid=node_uuid)
            port_query.delete()

            disk_query = model_query(context, models.ComputeDisk).filter_by(
                node_uuid=node_uuid)
            disk_query.delete()

            count = query.delete()
            if count != 1:
                raise exception.ComputeNodeNotFound(node=node_uuid)

    def compute_node_update(self, context, node_uuid, values):
        with _session_for_write():
            query = model_query(
                context,
                models.ComputeNode).filter_by(node_uuid=node_uuid)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ComputeNodeNotFound(node=node_uuid)

            ref.update(values)
        return ref

    def compute_port_create(self, context, values):
        compute_port = models.ComputePort()
        compute_port.update(values)
        with _session_for_write() as session:
            try:
                session.add(compute_port)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.ComputePortAlreadyExists(
                    port=values['port_uuid'])
            return compute_port

    def compute_port_get(self, context, port_uuid):
        query = model_query(
            context,
            models.ComputePort).filter_by(port_uuid=port_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ComputePortNotFound(port=port_uuid)

    def compute_port_get_all(self, context):
        return model_query(context, models.ComputePort)

    def compute_port_get_by_node_uuid(self, context, node_uuid):
        return model_query(context, models.ComputePort).filter_by(
            node_uuid=node_uuid).all()

    def compute_port_destroy(self, context, port_uuid):
        with _session_for_write():
            query = model_query(
                context,
                models.ComputePort).filter_by(port_uuid=port_uuid)

            count = query.delete()
            if count != 1:
                raise exception.ComputePortNotFound(port=port_uuid)

    def compute_port_update(self, context, port_uuid, values):
        with _session_for_write():
            query = model_query(
                context,
                models.ComputePort).filter_by(port_uuid=port_uuid)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ComputePortNotFound(port=port_uuid)

            ref.update(values)
        return ref

    def compute_disk_create(self, context, values):
        compute_disk = models.ComputeDisk()
        compute_disk.update(values)
        with _session_for_write() as session:
            try:
                session.add(compute_disk)
                session.flush()
            except db_exc.DBDuplicateEntry:
                raise exception.ComputeDiskAlreadyExists(
                    disk=values['disk_uuid'])
            return compute_disk

    def compute_disk_get(self, context, disk_uuid):
        query = model_query(
            context,
            models.ComputeDisk).filter_by(disk_uuid=disk_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ComputeDiskNotFound(disk=disk_uuid)

    def compute_disk_get_all(self, context):
        return model_query(context, models.ComputeDisk)

    def compute_disk_get_by_node_uuid(self, context, node_uuid):
        return model_query(context, models.ComputeDisk).filter_by(
            node_uuid=node_uuid).all()

    def compute_disk_destroy(self, context, disk_uuid):
        with _session_for_write():
            query = model_query(
                context,
                models.ComputeDisk).filter_by(disk_uuid=disk_uuid)

            count = query.delete()
            if count != 1:
                raise exception.ComputeDiskNotFound(disk=disk_uuid)

    def compute_disk_update(self, context, disk_uuid, values):
        with _session_for_write():
            query = model_query(
                context,
                models.ComputeDisk).filter_by(disk_uuid=disk_uuid)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ComputeDiskNotFound(disk=disk_uuid)

            ref.update(values)
        return ref

    def extra_specs_update_or_create(self, context,
                                     instance_type_uuid, specs,
                                     max_retries=10):
        """Create or update instance type extra specs.

        This adds or modifies the key/value pairs specified in the
        extra specs dict argument
        """
        for attempt in range(max_retries):
            with _session_for_write() as session:
                try:
                    spec_refs = model_query(
                        context, models.InstanceTypeExtraSpecs). \
                        filter_by(instance_type_uuid=instance_type_uuid). \
                        filter(models.InstanceTypeExtraSpecs.key.in_(
                            specs.keys())).with_lockmode('update').all()

                    existing_keys = set()
                    for spec_ref in spec_refs:
                        key = spec_ref["key"]
                        existing_keys.add(key)
                        spec_ref.update({"value": specs[key]})

                    for key, value in specs.items():
                        if key in existing_keys:
                            continue
                        spec_ref = models.InstanceTypeExtraSpecs()
                        spec_ref.update(
                            {"key": key, "value": value,
                             "instance_type_uuid": instance_type_uuid})

                        session.add(spec_ref)
                        session.flush()

                    return specs
                except db_exc.DBDuplicateEntry:
                    # a concurrent transaction has been committed,
                    # try again unless this was the last attempt
                    if attempt == max_retries - 1:
                        raise exception.TypeExtraSpecUpdateCreateFailed(
                            id=instance_type_uuid, retries=max_retries)

    def instance_type_extra_specs_get(self, context, type_id):
        rows = _type_extra_specs_get_query(context, type_id).all()
        return {row['key']: row['value'] for row in rows}

    def type_extra_specs_delete(self, context, type_id, key):
        result = _type_extra_specs_get_query(context, type_id). \
            filter(models.InstanceTypeExtraSpecs.key == key). \
            delete(synchronize_session=False)
        # did not find the extra spec
        if result == 0:
            raise exception.InstanceTypeExtraSpecsNotFound(
                extra_specs_key=key, type_id=type_id)

    def instance_nic_update_or_create(self, context, port_id, values):
        with _session_for_write() as session:
            query = model_query(context, models.InstanceNic).filter_by(
                port_id=port_id)
            nic = query.first()
            if not nic:
                nic = models.InstanceNic()
            values.update(port_id=port_id)
            nic.update(values)
            session.add(nic)
            session.flush()
        return nic

    def instance_nics_get_by_instance_uuid(self, context, instance_uuid):
        return model_query(context, models.InstanceNic).filter_by(
            instance_uuid=instance_uuid).all()

    def instance_fault_create(self, context, values):
        """Create a new InstanceFault."""

        fault = models.InstanceFault()
        fault.update(values)

        with _session_for_write() as session:
            session.add(fault)
            session.flush()
            return fault

    def instance_fault_get_by_instance_uuids(self, context, instance_uuids):
        """Get all instance faults for the provided instance_uuids."""
        if not instance_uuids:
            return {}

        rows = model_query(context, models.InstanceFault).\
            filter(models.InstanceFault.instance_uuid.in_(instance_uuids)).\
            order_by(desc("created_at"), desc("id")).all()

        output = {}
        for instance_uuid in instance_uuids:
            output[instance_uuid] = []

        for row in rows:
            data = dict(row)
            output[row['instance_uuid']].append(data)

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

    def quota_destroy(self, context, project_id, resource_name):
        with _session_for_write():
            query = model_query(context, models.Quota)
            query = query.filter_by(project_id=project_id,
                                    resource_name=resource_name)

            count = query.delete()
            if count != 1:
                raise exception.QuotaNotFound(quota_name=resource_name)

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

    def _sync_instances(self, context, project_id):
        query = model_query(context, models.Instance, instance=True).\
            filter_by(project_id=project_id).all()
        return {'instances': len(query) or 0}

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


def _type_get_id_from_type_query(context, type_id):
    return model_query(context, models.InstanceTypes). \
        filter_by(uuid=type_id)


def _type_get_id_from_type(context, type_id):
    result = _type_get_id_from_type_query(context, type_id).first()
    if not result:
        raise exception.InstanceTypeNotFound(type_id=type_id)
    return result.uuid


def _type_extra_specs_get_query(context, type_id):
    return model_query(context, models.InstanceTypeExtraSpecs). \
        filter_by(instance_type_uuid=type_id)
