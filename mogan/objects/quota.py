# Copyright 2017 Fiberhome Integration Technologies Co.,LTD
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

"""Quotas for instances."""

import datetime

from oslo_config import cfg
from oslo_utils import importutils
from oslo_utils import timeutils
from oslo_versionedobjects import base as object_base
import six

from mogan.common import exception
from mogan.db import api as dbapi
from mogan.objects import base
from mogan.objects import fields as object_fields


CONF = cfg.CONF


@base.MoganObjectRegistry.register
class Quota(base.MoganObject, object_base.VersionedObjectDictCompat):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': object_fields.IntegerField(),
        'project_id': object_fields.UUIDField(nullable=True),
        'resource_name': object_fields.StringField(nullable=True),
        'hard_limit': object_fields.IntegerField(nullable=True),
        'allocated': object_fields.IntegerField(default=0),
    }

    def __init__(self, *args, **kwargs):
        super(Quota, self).__init__(*args, **kwargs)
        self.quota_driver = importutils.import_object(CONF.quota.quota_driver)
        self._resources = {}

    @property
    def resources(self):
        return self._resources

    @staticmethod
    def _from_db_object_list(db_objects, cls, context):
        """Converts a list of database entities to a list of formal objects."""
        return [Quota._from_db_object(cls(context), obj)
                for obj in db_objects]

    @classmethod
    def list(cls, context, project_only=False):
        """Return a list of Quota objects."""
        db_quotas = cls.dbapi.quota_get_all(context,
                                            project_only=project_only)
        return Quota._from_db_object_list(db_quotas, cls, context)

    @classmethod
    def get(cls, context, project_id, resource_name):
        """Find a quota of resource and return a Quota object."""
        db_quota = cls.dbapi.quota_get(context, project_id, resource_name)
        quota = Quota._from_db_object(cls(context), db_quota)
        return quota

    def create(self, context):
        """Create a Quota record in the DB."""
        values = self.obj_get_changes()
        # Since we need to avoid passing False down to the DB layer
        # (which uses an integer), we can always default it to zero here.
        values['deleted'] = 0

        db_quota = self.dbapi.quota_create(context, values)
        self._from_db_object(self, db_quota)

    def destroy(self, context, project_id, resource_name):
        """Delete the Quota from the DB."""
        self.dbapi.quota_destroy(context, project_id, resource_name)
        self.obj_reset_changes()

    def save(self, context, project_id, resource_name):
        """Save updates to this Quota."""
        updates = self.obj_get_changes()
        self.dbapi.quota_update(context, project_id, resource_name, updates)
        self.obj_reset_changes()

    def refresh(self, context, project_id, resource_name):
        """Refresh the object by re-fetching from the DB."""
        current = self.__class__.get(context, project_id, resource_name)
        self.obj_refresh(current)
        self.obj_reset_changes()

    def reserve(self, context, expire=None, project_id=None, **deltas):
        """reserve the Quota."""
        return self.quota_driver.reserve(context, self.resources, deltas,
                                         expire=expire, project_id=project_id)

    def commit(self, context, reservations, project_id=None):
        self.quota_driver.commit(context, reservations, project_id=project_id)

    def rollback(self, context, reservations, project_id=None):
        self.quota_driver.rollback(context, reservations,
                                   project_id=project_id)

    def expire(self, context):
        return self.quota_driver.expire(context)

    def count(self, context, resource, *args, **kwargs):
        """Count a resource.

        For countable resources, invokes the count() function and
        returns its result.  Arguments following the context and
        resource are passed directly to the count function declared by
        the resource.

        :param context: The request context, for access checks.
        :param resource: The name of the resource, as a string.
        """

        # Get the resource
        res = self.resources.get(resource)
        if not res or not hasattr(res, 'count'):
            raise exception.QuotaResourceUnknown(unknown=[resource])

        return res.count(context, *args, **kwargs)

    def register_resource(self, resource):
        """Register a resource."""

        self._resources[resource.name] = resource

    def register_resources(self, resources):
        """Register a list of resources."""

        for resource in resources:
            self.register_resource(resource)

    def get_quota_limit_and_usage(self, context, resources, project_id):
        return self.quota_driver.get_project_quotas(context, resources,
                                                    project_id, usages=True)


class DbQuotaDriver(object):

    """Driver to perform check to enforcement of quotas.

    Also allows to obtain quota information.
    The default driver utilizes the local database.
    """

    dbapi = dbapi.get_instance()

    def get_project_quotas(self, context, resources, project_id, usages=True):
        """Retrieve quotas for a project.

        Given a list of resources, retrieve the quotas for the given
        project.

        :param context: The request context, for access checks.
        :param resources: A dictionary of the registered resources.
        :param project_id: The ID of the project to return quotas for.
        :param usages: If True, the current in_use, reserved and allocated
                       counts will also be returned.
        """

        quotas = {}
        project_quotas = {}
        res = self.dbapi.quota_get_all_by_project(context, project_id)
        for p_quota in res:
            project_quotas[p_quota.resource_name] = p_quota.hard_limit
        if project_quotas == {}:
            self.dbapi.quota_create(context, {'resource_name': 'instances',
                                              'project_id': project_id,
                                              'hard_limit': 10,
                                              'allocated': 0})
            project_quotas['instances'] = 10
        allocated_quotas = None
        if usages:
            project_usages = self.dbapi.quota_usage_get_all_by_project(
                context, project_id)
            allocated_quotas = self.dbapi.quota_allocated_get_all_by_project(
                context, project_id)
            allocated_quotas.pop('project_id')

        for resource in resources.values():
            if resource.name not in project_quotas:
                continue

            quota_val = project_quotas.get(resource.name)
            if quota_val is None:
                raise exception.QuotaNotFound(quota_name=resource.name)
            quotas[resource.name] = {'limit': quota_val}

            # Include usages if desired.  This is optional because one
            # internal consumer of this interface wants to access the
            # usages directly from inside a transaction.
            if usages:
                usage = project_usages.get(resource.name, {})
                quotas[resource.name].update(
                    in_use=usage.get('in_use', 0),
                    reserved=usage.get('reserved', 0), )
            if allocated_quotas:
                quotas[resource.name].update(
                    allocated=allocated_quotas.get(resource.name, 0), )
        return quotas

    def _get_quotas(self, context, resources, keys, has_sync, project_id=None):
        """A helper method which retrieves the quotas for specific resources.

        This specific resource is identified by keys, and which apply to the
        current context.

        :param context: The request context, for access checks.
        :param resources: A dictionary of the registered resources.
        :param keys: A list of the desired quotas to retrieve.
        :param has_sync: If True, indicates that the resource must
                         have a sync attribute; if False, indicates
                         that the resource must NOT have a sync
                         attribute.
        :param project_id: Specify the project_id if current context
                           is admin and admin wants to impact on
                           common user's tenant.
        """

        # Filter resources
        if has_sync:
            sync_filt = lambda x: hasattr(x, 'sync')
        else:
            sync_filt = lambda x: not hasattr(x, 'sync')
        desired = set(keys)
        sub_resources = {k: v for k, v in resources.items()
                         if k in desired and sync_filt(v)}

        # Make sure we accounted for all of them...
        if len(keys) != len(sub_resources):
            unknown = desired - set(sub_resources.keys())
            raise exception.QuotaResourceUnknown(unknown=sorted(unknown))

        # Grab and return the quotas (without usages)
        quotas = self.get_project_quotas(context, sub_resources,
                                         project_id, usages=False)

        return {k: v['limit'] for k, v in quotas.items()}

    def reserve(self, context, resources, deltas, expire=None,
                project_id=None):
        """Check quotas and reserve resources.

        For counting quotas--those quotas for which there is a usage
        synchronization function--this method checks quotas against
        current usage and the desired deltas.

        This method will raise a QuotaResourceUnknown exception if a
        given resource is unknown or if it does not have a usage
        synchronization function.

        If any of the proposed values is over the defined quota, an
        OverQuota exception will be raised with the sorted list of the
        resources which are too high.  Otherwise, the method returns a
        list of reservation UUIDs which were created.

        :param context: The request context, for access checks.
        :param resources: A dictionary of the registered resources.
        :param deltas: A dictionary of the proposed delta changes.
        :param expire: An optional parameter specifying an expiration
                       time for the reservations.  If it is a simple
                       number, it is interpreted as a number of
                       seconds and added to the current time; if it is
                       a datetime.timedelta object, it will also be
                       added to the current time.  A datetime.datetime
                       object will be interpreted as the absolute
                       expiration time.  If None is specified, the
                       default expiration time set by
                       --default-reservation-expire will be used (this
                       value will be treated as a number of seconds).
        :param project_id: Specify the project_id if current context
                           is admin and admin wants to impact on
                           common user's tenant.
        """

        # Set up the reservation expiration
        if expire is None:
            expire = CONF.quota.reservation_expire
        if isinstance(expire, six.integer_types):
            expire = datetime.timedelta(seconds=expire)
        if isinstance(expire, datetime.timedelta):
            expire = timeutils.utcnow() + expire
        if not isinstance(expire, datetime.datetime):
            raise exception.InvalidReservationExpiration(expire=expire)

        # If project_id is None, then we use the project_id in context
        if project_id is None:
            project_id = context.tenant

        # Get the applicable quotas.
        quotas = self._get_quotas(context, resources, deltas.keys(),
                                  has_sync=True, project_id=project_id)

        return self._reserve(context, resources, quotas, deltas, expire,
                             project_id)

    def _reserve(self, context, resources, quotas, deltas, expire, project_id):
        return self.dbapi.quota_reserve(context, resources, quotas, deltas,
                                        expire,
                                        CONF.quota.until_refresh,
                                        CONF.quota.max_age,
                                        project_id)

    def commit(self, context, reservations, project_id=None):
        """Commit reservations.

        :param context: The request context, for access checks.
        :param reservations: A list of the reservation UUIDs, as
                             returned by the reserve() method.
        :param project_id: Specify the project_id if current context
                           is admin and admin wants to impact on
                           common user's tenant.
        """
        # If project_id is None, then we use the project_id in context
        if project_id is None:
            project_id = context.tenant

        self.dbapi.reservation_commit(context, reservations,
                                      project_id=project_id)

    def rollback(self, context, reservations, project_id=None):
        """Roll back reservations.

        :param context: The request context, for access checks.
        :param reservations: A list of the reservation UUIDs, as
                             returned by the reserve() method.
        :param project_id: Specify the project_id if current context
                           is admin and admin wants to impact on
                           common user's tenant.
        """
        # If project_id is None, then we use the project_id in context
        if project_id is None:
            project_id = context.tenant

        self.dbapi.reservation_rollback(context, reservations,
                                        project_id=project_id)

    def expire(self, context):
        """Expire reservations.

        Explores all currently existing reservations and rolls back
        any that have expired.

        :param context: The request context, for access checks.
        """

        self.dbapi.reservation_expire(context)


class BaseResource(object):
    """Describe a single resource for quota checking."""

    def __init__(self, name, sync, count=None):
        """Initializes a Resource.

        :param name: The name of the resource, i.e., "instances".
        :param sync: A dbapi methods name which returns a dictionary
                     to resynchronize the in_use count for one or more
                     resources, as described above.
        """
        self.name = name
        self.sync = sync
        self.count = count

    def quota(self, driver, context, **kwargs):
        """Given a driver and context, obtain the quota for this resource.

        :param driver: A quota driver.
        :param context: The request context.
        :param project_id: The project to obtain the quota value for.
                           If not provided, it is taken from the
                           context.  If it is given as None, no
                           project-specific quota will be searched
                           for.
        """

        # Get the project ID
        project_id = kwargs.get('project_id', context.tenant)

        # Look up the quota for the project
        if project_id:
            try:
                return driver.get_by_project(context, project_id, self.name)
            except exception.ProjectQuotaNotFound:
                pass
        return -1


class InstanceResource(BaseResource):
    """ReservableResource for a specific instance."""

    def __init__(self, name='instances'):
        """Initializes a InstanceResource.

        :param name: The kind of resource, i.e., "instances".
        """
        super(InstanceResource, self).__init__(name, "_sync_%s" % name)
