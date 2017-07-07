# Copyright (c) 2014 Red Hat, Inc.
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

import functools
import re
import time

from keystoneauth1 import exceptions as ks_exc
from keystoneauth1 import loading as keystone
from oslo_config import cfg
from oslo_log import log as logging
from six.moves.urllib import parse

from mogan.common import exception

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

_RE_INV_IN_USE = re.compile("Inventory for (.+) on resource provider "
                            "(.+) in use")
WARN_EVERY = 10


def warn_limit(self, msg):
    if self._warn_count:
        self._warn_count -= 1
    else:
        self._warn_count = WARN_EVERY
        LOG.warning(msg)


def safe_connect(f):
    @functools.wraps(f)
    def wrapper(self, *a, **k):
        try:
            return f(self, *a, **k)
        except ks_exc.EndpointNotFound:
            warn_limit(
                self,
                'The placement API endpoint not found.')
        except ks_exc.MissingAuthPlugin:
            warn_limit(
                self,
                'No authentication information found for placement API.')
        except ks_exc.Unauthorized:
            warn_limit(
                self,
                ('Placement service credentials do not work.'))
        except ks_exc.DiscoveryFailure:
            # TODO(_gryf): Looks like DiscoveryFailure is not the only missing
            # exception here. In Pike we should take care about keystoneauth1
            # failures handling globally.
            warn_limit(self,
                       'Discovering suitable URL for placement API '
                       'failed.')
        except ks_exc.ConnectFailure:
            msg = 'Placement API service is not responding.'
            LOG.warning(msg)

    return wrapper


def _extract_inventory_in_use(body):
    """Given an HTTP response body, extract the resource classes that were
    still in use when we tried to delete inventory.

    :returns: String of resource classes or None if there was no InventoryInUse
              error in the response body.
    """
    match = _RE_INV_IN_USE.search(body)
    if match:
        return match.group(1)
    return None


def get_placement_request_id(response):
    if response is not None:
        return response.headers.get(
            'openstack-request-id',
            response.headers.get('x-openstack-request-id'))


class SchedulerReportClient(object):
    """Client class for updating the scheduler."""

    def __init__(self):
        # A dict, keyed by the resource provider UUID, of ResourceProvider
        # objects that will have their inventories and allocations tracked by
        # the placement API for the node
        self._resource_providers = {}
        # A dict, keyed by resource provider UUID, of sets of aggregate UUIDs
        # the provider is associated with
        self._provider_aggregate_map = {}
        auth_plugin = keystone.load_auth_from_conf_options(
            CONF, 'placement')
        self._client = keystone.load_session_from_conf_options(
            CONF, 'placement', auth=auth_plugin)
        # NOTE(danms): Keep track of how naggy we've been
        self._warn_count = 0
        self.ks_filter = {'service_type': 'placement',
                          'region_name': CONF.placement.os_region_name,
                          'interface': CONF.placement.os_interface}

    def get(self, url, version=None):
        kwargs = {}
        if version is not None:
            # TODO(mriedem): Perform some version discovery at some point.
            kwargs = {
                'headers': {
                    'OpenStack-API-Version': 'placement %s' % version
                },
            }
        return self._client.get(
            url,
            endpoint_filter=self.ks_filter, raise_exc=False, **kwargs)

    def post(self, url, data, version=None):
        # NOTE(sdague): using json= instead of data= sets the
        # media type to application/json for us. Placement API is
        # more sensitive to this than other APIs in the OpenStack
        # ecosystem.
        kwargs = {}
        if version is not None:
            # TODO(mriedem): Perform some version discovery at some point.
            kwargs = {
                'headers': {
                    'OpenStack-API-Version': 'placement %s' % version
                },
            }
        return self._client.post(
            url, json=data,
            endpoint_filter=self.ks_filter, raise_exc=False, **kwargs)

    def put(self, url, data, version=None):
        # NOTE(sdague): using json= instead of data= sets the
        # media type to application/json for us. Placement API is
        # more sensitive to this than other APIs in the OpenStack
        # ecosystem.
        kwargs = {}
        if version is not None:
            # TODO(mriedem): Perform some version discovery at some point.
            kwargs = {
                'headers': {
                    'OpenStack-API-Version': 'placement %s' % version
                },
            }
        if data is not None:
            kwargs['json'] = data
        return self._client.put(
            url, endpoint_filter=self.ks_filter, raise_exc=False,
            **kwargs)

    def delete(self, url):
        return self._client.delete(
            url,
            endpoint_filter=self.ks_filter, raise_exc=False)

    @safe_connect
    def get_filtered_resource_providers(self, filters):
        """Returns a list of ResourceProviders matching the requirements
        expressed by the filters argument, which can include a dict named
        'resources' where amounts are keyed by resource class names.

        eg. filters = {'resources': {'CUSTOM_BAREMETAL_GOLD': 1}}
        """
        resources = filters.pop("resources", None)
        if resources:
            resource_query = ",".join(sorted("%s:%s" % (rc, amount)
                                      for (rc, amount) in resources.items()))
            filters['resources'] = resource_query

        resp = self.get("/resource_providers?%s" % parse.urlencode(filters),
                        version='1.4')
        if resp.status_code == 200:
            data = resp.json()
            return data.get('resource_providers', [])
        else:
            msg = ("Failed to retrieve filtered list of resource providers "
                   "from placement API for filters %(filters)s. "
                   "Got %(status_code)d: %(err_text)s.")
            args = {
                'filters': filters,
                'status_code': resp.status_code,
                'err_text': resp.text,
            }
            LOG.error(msg, args)
            return None

    @safe_connect
    def _get_provider_aggregates(self, rp_uuid):
        """Queries the placement API for a resource provider's aggregates.
        Returns a set() of aggregate UUIDs or None if no such resource provider
        was found or there was an error communicating with the placement API.

        :param rp_uuid: UUID of the resource provider to grab aggregates for.
        """
        resp = self.get("/resource_providers/%s/aggregates" % rp_uuid,
                        version='1.1')
        if resp.status_code == 200:
            data = resp.json()
            return set(data['aggregates'])

        placement_req_id = get_placement_request_id(resp)
        if resp.status_code == 404:
            msg = "[%(placement_req_id)s] Tried to get a provider's "
            "aggregates; however the provider %(uuid)s does not "
            "exist."
            args = {
                'uuid': rp_uuid,
                'placement_req_id': placement_req_id,
            }
            LOG.warning(msg, args)
        else:
            msg = ("[%(placement_req_id)s] Failed to retrieve aggregates "
                   "from placement API for resource provider with UUID "
                   "%(uuid)s. Got %(status_code)d: %(err_text)s.")
            args = {
                'placement_req_id': placement_req_id,
                'uuid': rp_uuid,
                'status_code': resp.status_code,
                'err_text': resp.text,
            }
            LOG.error(msg, args)

    @safe_connect
    def _put_provider_aggregates(self, rp_uuid, aggs):
        """Associate a list of aggregates with the resource provider.

        :param aggs: a list of UUID of the aggregates.
        :param rp_uuid: UUID of the resource provider.
        """
        url = "/resource_providers/%s/aggregates" % rp_uuid
        payload = list(aggs)
        resp = self.put(url, payload, version='1.1')
        if resp.status_code == 200:
            self._provider_aggregate_map[rp_uuid] = set(aggs)
            data = resp.json()
            return set(data['aggregates'])

        placement_req_id = get_placement_request_id(resp)
        if resp.status_code == 404:
            msg = "[%(placement_req_id)s] Tried to put a provider's "
            "aggregates; however the provider %(uuid)s does not "
            "exist."
            args = {
                'uuid': rp_uuid,
                'placement_req_id': placement_req_id,
            }
            LOG.warning(msg, args)
        else:
            msg = ("[%(placement_req_id)s] Failed to set aggregates "
                   "from placement API for resource provider with UUID "
                   "%(uuid)s. Got %(status_code)d: %(err_text)s.")
            args = {
                'placement_req_id': placement_req_id,
                'uuid': rp_uuid,
                'status_code': resp.status_code,
                'err_text': resp.text,
            }
            LOG.error(msg, args)

    @safe_connect
    def _get_resource_provider(self, uuid):
        """Queries the placement API for a resource provider record with the
        supplied UUID.

        Returns a dict of resource provider information if found or None if no
        such resource provider could be found.

        :param uuid: UUID identifier for the resource provider to look up
        """
        resp = self.get("/resource_providers/%s" % uuid)
        if resp.status_code == 200:
            data = resp.json()
            return data
        elif resp.status_code == 404:
            return None
        else:
            placement_req_id = get_placement_request_id(resp)
            msg = ("[%(placement_req_id)s] Failed to retrieve resource "
                   "provider record from placement API for UUID %(uuid)s. "
                   "Got %(status_code)d: %(err_text)s.")
            args = {
                'uuid': uuid,
                'status_code': resp.status_code,
                'err_text': resp.text,
                'placement_req_id': placement_req_id,
            }
            LOG.error(msg, args)

    @safe_connect
    def _create_resource_provider(self, uuid, name):
        """Calls the placement API to create a new resource provider record.

        Returns a dict of resource provider information object representing
        the newly-created resource provider.

        :param uuid: UUID of the new resource provider
        :param name: Name of the resource provider
        """
        url = "/resource_providers"
        payload = {
            'uuid': uuid,
            'name': name,
        }
        resp = self.post(url, payload)
        placement_req_id = get_placement_request_id(resp)
        if resp.status_code == 201:
            msg = ("[%(placement_req_id)s] Created resource provider "
                   "record via placement API for resource provider with "
                   "UUID %(uuid)s and name %(name)s.")
            args = {
                'uuid': uuid,
                'name': name,
                'placement_req_id': placement_req_id,
            }
            LOG.info(msg, args)
            return dict(
                uuid=uuid,
                name=name,
                generation=0,
            )
        elif resp.status_code == 409:
            # Another thread concurrently created a resource provider with the
            # same UUID. Log a warning and then just return the resource
            # provider object from _get_resource_provider()
            msg = ("[%(placement_req_id)s] Another thread already created "
                   "a resource provider with the UUID %(uuid)s. Grabbing "
                   "that record from the placement API.")
            args = {
                'uuid': uuid,
                'placement_req_id': placement_req_id,
            }
            LOG.info(msg, args)
            return self._get_resource_provider(uuid)
        else:
            msg = ("[%(placement_req_id)s] Failed to create resource "
                   "provider record in placement API for UUID %(uuid)s. "
                   "Got %(status_code)d: %(err_text)s.")
            args = {
                'uuid': uuid,
                'status_code': resp.status_code,
                'err_text': resp.text,
                'placement_req_id': placement_req_id,
            }
            LOG.error(msg, args)

    def _ensure_resource_provider(self, uuid, name=None):
        """Ensures that the placement API has a record of a resource provider
        with the supplied UUID. If not, creates the resource provider record in
        the placement API for the supplied UUID, optionally passing in a name
        for the resource provider.

        The found or created resource provider object is returned from this
        method. If the resource provider object for the supplied uuid was not
        found and the resource provider record could not be created in the
        placement API, we return None.

        :param uuid: UUID identifier for the resource provider to ensure exists
        :param name: Optional name for the resource provider if the record
                     does not exist. If empty, the name is set to the UUID
                     value
        """
        if uuid in self._resource_providers:
            # NOTE(jaypipes): This isn't optimal to check if aggregate
            # associations have changed each time we call
            # _ensure_resource_provider() and get a hit on the local cache of
            # provider objects, however the alternative is to force operators
            # to restart all their nova-compute workers every time they add or
            # change an aggregate. We might optionally want to add some sort of
            # cache refresh delay or interval as an optimization?
            msg = "Refreshing aggregate associations for resource provider %s"
            LOG.debug(msg, uuid)
            aggs = self._get_provider_aggregates(uuid)
            self._provider_aggregate_map[uuid] = aggs
            return self._resource_providers[uuid]

        rp = self._get_resource_provider(uuid)
        if rp is None:
            name = name or uuid
            rp = self._create_resource_provider(uuid, name)
            if rp is None:
                return
        msg = "Grabbing aggregate associations for resource provider %s"
        LOG.debug(msg, uuid)
        aggs = self._get_provider_aggregates(uuid)
        self._resource_providers[uuid] = rp
        self._provider_aggregate_map[uuid] = aggs
        return rp

    def _get_inventory(self, rp_uuid):
        url = '/resource_providers/%s/inventories' % rp_uuid
        result = self.get(url)
        if not result:
            return {'inventories': {}}
        return result.json()

    def _get_inventory_and_update_provider_generation(self, rp_uuid):
        """Helper method that retrieves the current inventory for the supplied
        resource provider according to the placement API. If the cached
        generation of the resource provider is not the same as the generation
        returned from the placement API, we update the cached generation.
        """
        curr = self._get_inventory(rp_uuid)

        # Update our generation immediately, if possible. Even if there
        # are no inventories we should always have a generation but let's
        # be careful.
        server_gen = curr.get('resource_provider_generation')
        if server_gen:
            my_rp = self._resource_providers[rp_uuid]
            if server_gen != my_rp['generation']:
                LOG.debug('Updating our resource provider generation '
                          'from %(old)i to %(new)i',
                          {'old': my_rp['generation'],
                           'new': server_gen})
            my_rp['generation'] = server_gen
        return curr

    def _update_inventory_attempt(self, rp_uuid, inv_data):
        """Update the inventory for this resource provider if needed.

        :param rp_uuid: The resource provider UUID for the operation
        :param inv_data: The new inventory for the resource provider
        :returns: True if the inventory was updated (or did not need to be),
                  False otherwise.
        """
        curr = self._get_inventory_and_update_provider_generation(rp_uuid)

        # Check to see if we need to update placement's view
        if inv_data == curr.get('inventories', {}):
            return True

        cur_rp_gen = self._resource_providers[rp_uuid]['generation']
        payload = {
            'resource_provider_generation': cur_rp_gen,
            'inventories': inv_data,
        }
        url = '/resource_providers/%s/inventories' % rp_uuid
        result = self.put(url, payload)
        if result.status_code == 409:
            LOG.info('[%(placement_req_id)s] Inventory update conflict '
                     'for %(resource_provider_uuid)s with generation ID '
                     '%(generation_id)s',
                     {'placement_req_id': get_placement_request_id(result),
                      'resource_provider_uuid': rp_uuid,
                      'generation_id': cur_rp_gen})
            match = _RE_INV_IN_USE.search(result.text)
            if match:
                rc = match.group(1)
                raise exception.InventoryInUse(
                    resource_classes=rc,
                    resource_provider=rp_uuid,
                )

            # Invalidate our cache and re-fetch the resource provider
            # to be sure to get the latest generation.
            del self._resource_providers[rp_uuid]
            # NOTE(jaypipes): We don't need to pass a name parameter to
            # _ensure_resource_provider() because we know the resource provider
            # record already exists. We're just reloading the record here.
            self._ensure_resource_provider(rp_uuid)
            return False
        elif not result:
            placement_req_id = get_placement_request_id(result)
            LOG.warning(('[%(placement_req_id)s] Failed to update '
                         'inventory for resource provider '
                         '%(uuid)s: %(status)i %(text)s'),
                        {'placement_req_id': placement_req_id,
                         'uuid': rp_uuid,
                         'status': result.status_code,
                         'text': result.text})
            # log the body at debug level
            LOG.debug('[%(placement_req_id)s] Failed inventory update request '
                      'for resource provider %(uuid)s with body: %(payload)s',
                      {'placement_req_id': placement_req_id,
                       'uuid': rp_uuid,
                       'payload': payload})
            return False

        if result.status_code != 200:
            placement_req_id = get_placement_request_id(result)
            LOG.info(
                ('[%(placement_req_id)s] Received unexpected response code '
                 '%(code)i while trying to update inventory for resource '
                 'provider %(uuid)s: %(text)s'),
                {'placement_req_id': placement_req_id,
                 'uuid': rp_uuid,
                 'code': result.status_code,
                 'text': result.text})
            return False

        # Update our view of the generation for next time
        updated_inventories_result = result.json()
        new_gen = updated_inventories_result['resource_provider_generation']
        self._resource_providers[rp_uuid]['generation'] = new_gen
        LOG.debug('Updated inventory for %s at generation %i',
                  rp_uuid, new_gen)
        return True

    @safe_connect
    def _update_inventory(self, rp_uuid, inv_data):
        for attempt in (1, 2, 3):
            if rp_uuid not in self._resource_providers:
                # NOTE(danms): Either we failed to fetch/create the RP
                # on our first attempt, or a previous attempt had to
                # invalidate the cache, and we were unable to refresh
                # it. Bail and try again next time.
                LOG.warning('Unable to refresh my resource provider record')
                return False
            if self._update_inventory_attempt(rp_uuid, inv_data):
                return True
            time.sleep(1)
        return False

    def set_inventory_for_provider(self, rp_uuid, rp_name, inv_data,
                                   resource_class):
        """Given the UUID of a provider, set the inventory records for the
        provider to the supplied dict of resources.

        :param rp_uuid: UUID of the resource provider to set inventory for
        :param rp_name: Name of the resource provider in case we need to create
                        a record for it in the placement API
        :param inv_data: Dict, keyed by resource class name, of inventory data
                         to set against the provider

        :raises: exc.InvalidResourceClass if a supplied custom resource class
                 name does not meet the placement API's format requirements.
        """
        self._ensure_resource_provider(rp_uuid, rp_name)

        # Auto-create custom resource classes coming from a virt driver
        self._ensure_resource_class(resource_class)

        self._update_inventory(rp_uuid, inv_data)

    @safe_connect
    def _ensure_resource_class(self, name):
        """Make sure a custom resource class exists.

        First attempt to PUT the resource class using microversion 1.7. If
        this results in a 406, fail over to a GET and POST with version 1.2.

        Returns the name of the resource class if it was successfully
        created or already exists. Otherwise None.

        :param name: String name of the resource class to check/create.
        :raises: `exception.InvalidResourceClass` upon error.
        """
        # no payload on the put request
        response = self.put("/resource_classes/%s" % name, None, version="1.7")
        if 200 <= response.status_code < 300:
            return name
        elif response.status_code == 406:
            # microversion 1.7 not available so try the earlier way
            # TODO(cdent): When we're happy that all placement
            # servers support microversion 1.7 we can remove this
            # call and the associated code.
            LOG.debug('Falling back to placement API microversion 1.2 '
                      'for resource class management.')
            return self._get_or_create_resource_class(name)
        else:
            msg = ("Failed to ensure resource class record with "
                   "placement API for resource class %(rc_name)s. "
                   "Got %(status_code)d: %(err_text)s.")
            args = {
                'rc_name': name,
                'status_code': response.status_code,
                'err_text': response.text,
            }
            LOG.error(msg, args)
            raise exception.InvalidResourceClass(resource_class=name)

    def _get_or_create_resource_class(self, name):
        """Queries the placement API for a resource class supplied resource
        class string name. If the resource class does not exist, creates it.

        Returns the resource class name if exists or was created, else None.

        :param name: String name of the resource class to check/create.
        """
        resp = self.get("/resource_classes/%s" % name, version="1.2")
        if 200 <= resp.status_code < 300:
            return name
        elif resp.status_code == 404:
            self._create_resource_class(name)
            return name
        else:
            msg = ("Failed to retrieve resource class record from "
                   "placement API for resource class %(rc_name)s. "
                   "Got %(status_code)d: %(err_text)s.")
            args = {
                'rc_name': name,
                'status_code': resp.status_code,
                'err_text': resp.text,
            }
            LOG.error(msg, args)
            return None

    def _create_resource_class(self, name):
        """Calls the placement API to create a new resource class.

        :param name: String name of the resource class to create.

        :returns: None on successful creation.
        :raises: `exception.InvalidResourceClass` upon error.
        """
        url = "/resource_classes"
        payload = {
            'name': name,
        }
        resp = self.post(url, payload, version="1.2")
        if 200 <= resp.status_code < 300:
            msg = ("Created resource class record via placement API "
                   "for resource class %s.")
            LOG.info(msg, name)
        elif resp.status_code == 409:
            # Another thread concurrently created a resource class with the
            # same name. Log a warning and then just return
            msg = ("Another thread already created a resource class "
                   "with the name %s. Returning.")
            LOG.info(msg, name)
        else:
            msg = ("Failed to create resource class %(resource_class)s in "
                   "placement API. Got %(status_code)d: %(err_text)s.")
            args = {
                'resource_class': name,
                'status_code': resp.status_code,
                'err_text': resp.text,
            }
            LOG.error(msg, args)
            raise exception.InvalidResourceClass(resource_class=name)

    @safe_connect
    def delete_allocation_for_server(self, uuid):
        url = '/allocations/%s' % uuid
        r = self.delete(url)
        if r:
            LOG.info('Deleted allocation for server %s', uuid)
        else:
            # Check for 404 since we don't need to log a warning if we tried to
            # delete something which doesn't actually exist.
            if r.status_code != 404:
                LOG.warning(
                    'Unable to delete allocation for server '
                    '%(uuid)s: (%(code)i %(text)s)',
                    {'uuid': uuid,
                     'code': r.status_code,
                     'text': r.text})

    @safe_connect
    def put_allocations(self, rp_uuid, consumer_uuid, alloc_data, project_id,
                        user_id):
        """Creates allocation records for the supplied server UUID against
        the supplied resource provider.

        :note Currently we only allocate against a single resource provider.
              Once shared storage and things like NUMA allocations are a
              reality, this will change to allocate against multiple providers.

        :param rp_uuid: The UUID of the resource provider to allocate against.
        :param consumer_uuid: The server's UUID.
        :param alloc_data: Dict, keyed by resource class, of amounts to
                           consume.
        :param project_id: The project_id associated with the allocations.
        :param user_id: The user_id associated with the allocations.
        :returns: True if the allocations were created, False otherwise.
        """
        payload = {
            'allocations': [
                {
                    'resource_provider': {
                        'uuid': rp_uuid,
                    },
                    'resources': alloc_data,
                },
            ],
            'project_id': project_id,
            'user_id': user_id,
        }
        url = '/allocations/%s' % consumer_uuid
        r = self.put(url, payload, version='1.8')
        if r.status_code == 406:
            # microversion 1.8 not available so try the earlier way
            # TODO(melwitt): Remove this when we can be sure all placement
            # servers support version 1.8.
            payload.pop('project_id')
            payload.pop('user_id')
            r = self.put(url, payload)
        if r.status_code != 204:
            LOG.warning(
                'Unable to submit allocation for server '
                '%(uuid)s (%(code)i %(text)s)',
                {'uuid': consumer_uuid,
                 'code': r.status_code,
                 'text': r.text})
        return r.status_code == 204

    @safe_connect
    def delete_resource_provider(self, rp_uuid):
        """Deletes the ResourceProvider record for the compute_node.

        :param rp_uuid: The uuid of resource provider being deleted.
        """
        url = "/resource_providers/%s" % rp_uuid
        resp = self.delete(url)
        if resp:
            LOG.info("Deleted resource provider %s", rp_uuid)
            # clean the caches
            self._resource_providers.pop(rp_uuid, None)
            self._provider_aggregate_map.pop(rp_uuid, None)
        else:
            # Check for 404 since we don't need to log a warning if we tried to
            # delete something which doesn"t actually exist.
            if resp.status_code != 404:
                LOG.warning(
                    "Unable to delete resource provider "
                    "%(uuid)s: (%(code)i %(text)s)",
                    {"uuid": rp_uuid,
                     "code": resp.status_code,
                     "text": resp.text})

    @safe_connect
    def get_allocations_for_resource_provider(self, rp_uuid):
        url = '/resource_providers/%s/allocations' % rp_uuid
        resp = self.get(url)
        if not resp:
            return {}
        else:
            return resp.json()['allocations']

    def delete_allocations_for_resource_provider(self, rp_uuid):
        allocations = self.get_allocations_for_resource_provider(rp_uuid)
        if allocations:
            LOG.info('Deleted allocation for resource provider %s', rp_uuid)
        for consumer_id in allocations:
            self.delete_allocation_for_server(consumer_id)

    def get_nodes_from_resource_providers(self):
        # Use the rps we cached
        rps = self._resource_providers
        return {'nodes': [rp['name'] for id, rp in rps.items()]}

    def get_nodes_from_aggregate(self, aggregate_uuid):
        # Use the aggregates we cached
        rps = self._resource_providers
        rp_aggs = self._provider_aggregate_map
        rp_uuids = []
        for rp, aggs in rp_aggs.items():
            if aggregate_uuid in aggs:
                rp_uuids.append(rp)
        return {'nodes': [rps[id]['name'] for id in rp_uuids]}

    def update_aggregate_node(self, aggregate_uuid, node, action):
        rps = self._resource_providers
        for id, rp in rps.items():
            if node == rp['name']:
                rp_uuid = id
                break
        else:
            raise exception.NodeNotFound(node=node)

        aggs = self._provider_aggregate_map[rp_uuid]
        if action == 'add':
            new_aggs = aggs | set([aggregate_uuid])
        elif action == 'remove':
            if aggregate_uuid in aggs:
                new_aggs = aggs - set([aggregate_uuid])
            else:
                return
        else:
            LOG.info('Bad action parameter for update_aggregate_node() %s',
                     action)
            return
        self._put_provider_aggregates(rp_uuid, list(new_aggs))
