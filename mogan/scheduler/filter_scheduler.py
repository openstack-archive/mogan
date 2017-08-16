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

"""The FilterScheduler is for creating servers.

You can customize this scheduler by specifying your own node Filters and
Weighing Functions.
"""
import itertools
import random

from oslo_config import cfg
from oslo_log import log as logging

from mogan import objects
from mogan.common import exception
from mogan.common import utils
from mogan.common.i18n import _
from mogan.scheduler import client
from mogan.scheduler import driver
from mogan.scheduler import utils as sched_utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class FilterScheduler(driver.Scheduler):
    """Scheduler that can be used for filtering and weighing."""
    def __init__(self, *args, **kwargs):
        super(FilterScheduler, self).__init__(*args, **kwargs)
        self.max_attempts = self._max_attempts()
        self.reportclient = client.SchedulerClient().reportclient

    def _max_attempts(self):
        max_attempts = CONF.scheduler.scheduler_max_attempts
        if max_attempts < 1:
            raise exception.InvalidParameterValue(
                err=_("Invalid value for 'scheduler_max_attempts', "
                      "must be >=1"))
        return max_attempts

    def _log_server_error(self, server_id, retry):
        """Log requests with exceptions from previous server operations."""
        exc = retry.pop('exc', None)  # string-ified exception from server
        if not exc:
            return  # no exception info from a previous attempt, skip

        nodes = retry.get('nodes', None)
        if not nodes:
            return  # no previously attempted nodes, skip

        last_node = nodes[-1]
        LOG.error("Error scheduling %(server_id)s from last node: "
                  "%(last_node)s : %(exc)s",
                  {'server_id': server_id,
                   'last_node': last_node,
                   'exc': exc})

    def _populate_retry(self, filter_properties, request_spec):
        """Populate filter properties with history of retries for request.

        If maximum retries is exceeded, raise NoValidNode.
        """
        max_attempts = self.max_attempts
        retry = filter_properties.pop('retry', {})

        if max_attempts == 1:
            # re-scheduling is disabled.
            return

        server_id = request_spec.get('server_ids')[0]
        self._log_server_error(server_id, retry)

        if retry['num_attempts'] > max_attempts:
            raise exception.NoValidNode(
                _("Exceeded max scheduling attempts %(max_attempts)d "
                  "for server %(server_id)s") %
                {'max_attempts': max_attempts,
                 'server_id': server_id})

    @staticmethod
    def _get_res_cls_filters(request_spec):
        flavor_dict = request_spec['flavor']
        resources = dict([(sched_utils.ensure_resource_class_name(res[0]),
                           int(res[1]))
                          for res in flavor_dict['resources'].items()])
        return resources

    @staticmethod
    def _get_res_aggregates_filters(context, request_spec):
        flavor_dict = request_spec['flavor']
        resource_aggregates = flavor_dict.get('resource_aggregates', {})
        resource_aggregates_items = resource_aggregates.items()
        # Add availability_zone aggregate
        if request_spec['availability_zone']:
            resource_aggregates_items.append(
                ('availability_zone', request_spec['availability_zone']))

        filters = []
        for key, value in resource_aggregates_items:
            aggregates = objects.AggregateList.get_by_metadata(
                context, key, value)
            if not aggregates:
                # if no aggregates match with the key/value,
                # fail the scheduling.
                return None
            filters.extend([agg.uuid for agg in aggregates])

        return filters

    @staticmethod
    def _get_server_group_obj(context, request_spec):
        server_group = request_spec.get('scheduler_hints', {}).get('group')
        if not server_group:
            return
        server_group = objects.ServerGroup.get_by_uuid(context, server_group)
        return server_group

    def _get_affinity_available_nodes(self, context, sg_obj):
        if not sg_obj.members:
            return
        member = sg_obj.members[0]
        server = object.Server.get(context, member)
        affinity_zone = server.affinity_zone
        aggregates = objects.AggregateList.get_by_metadata(
            context, 'affinity_zone', affinity_zone)
        agg_uuids = [agg.uuid for agg in aggregates]
        query_filters = {'member_of': 'in:' + ','.join(agg_uuids)}
        aff_filtered_nodes = self.reportclient.get_filtered_resource_providers(
            query_filters)
        return [rp['uuid'] for rp in aff_filtered_nodes]

    def _get_anti_affinity_available_nodes(self, context, sg_obj):
        affinity_zones = []
        for member in sg_obj.members:
            server = object.Server.get(context, member)
            affinity_zone = server.affinity_zone
            affinity_zones.append(affinity_zone)
        all_aggs = object.AggregateList.get_all(context)
        all_aggs = sorted(all_aggs, key=lambda a: a.metadata.get(
            'affinity_zone'))
        grouped_aggs = itertools.groupby(all_aggs, lambda
            a: a.metadata.get('affinity_zone'))
        available_az_nodes = {}
        for az, aggs in grouped_aggs:
            if az in affinity_zones:
                continue
            agg_uuids = [agg.uuid for agg in aggs]
            query_filters = {'member_of': 'in:' + ','.join(agg_uuids)}
            az_rps = self.reportclient.get_filtered_resource_providers(
                query_filters)
            az_nodes = [rp['uuid'] for rp in az_rps]
            available_az_nodes.update({az: az_nodes})
        return available_az_nodes


    def _get_filtered_nodes(self, context, request_spec, server_group=None):
        resources_filter = self._get_res_cls_filters(request_spec)
        aggs_filters = self._get_res_aggregates_filters(context, request_spec)

        # None indicates no matching aggregates
        if aggs_filters is None:
            return []

        if aggs_filters:
            filtered_nodes = set()
            for agg_filter in aggs_filters:
                query_filters = {'resources': resources_filter,
                                 'member_of': 'in:' + ','.join(agg_filter)}
                filtered_rps = self.reportclient.\
                    get_filtered_resource_providers(query_filters)
                if not filtered_rps:
                    # if got empty, just break here.
                    return []
                filtered_rps = set([rp['uuid'] for rp in filtered_rps])
                if not filtered_nodes:
                    # initialize the filtered_nodes
                    filtered_nodes = filtered_rps
                else:
                    filtered_nodes &= filtered_rps
                if not filtered_nodes:
                    # if got empty, just break here.
                    return []
        else:
            query_filters = {'resources': resources_filter}
            filtered_nodes = self.reportclient.\
                get_filtered_resource_providers(query_filters)
            filtered_nodes = set([node['uuid'] for node in filtered_nodes])
        if not server_group:
            return list(filtered_nodes)

        if 'affinity' in server_group.policies:
            aff_available_nodes = self._get_affinity_available_nodes(
                context, server_group)
            return list(filtered_nodes & set(aff_available_nodes))
        elif 'anti-affinity' in server_group.policies:
            anti_filtered_nodes = []
            anti_available_nodes = self._get_anti_affinity_available_nodes(
                context, server_group)
            for aff_zone_nodes in anti_available_nodes.values():
                filtered_aff_zone_nodes = filtered_nodes & set(aff_zone_nodes)
                if filtered_aff_zone_nodes:
                    anti_filtered_nodes.append(filtered_aff_zone_nodes)
            return anti_filtered_nodes

    def schedule(self, context, request_spec, filter_properties=None):

        # TODO(zhenguo): Scheduler API is inherently multi-threaded as every
        # incoming RPC message will be dispatched in it's own green thread.
        # So we add a syncronized here to make sure the shared node states
        # consistent, but lock the whole schedule process is not a good choice,
        # we need to improve this.
        @utils.synchronized('schedule')
        def _schedule(self, context, request_spec, filter_properties):
            self._populate_retry(filter_properties, request_spec)
            server_group = self._get_server_group_obj(context, request_spec)
            filtered_nodes = self._get_filtered_nodes(context, request_spec,
                                                      server_group)
            if not filtered_nodes:
                LOG.warning('No filtered nodes found for server '
                            'with properties: %s',
                            request_spec.get('flavor'))
                raise exception.NoValidNode(_("No filtered nodes available"))
            dest_nodes = self._choose_nodes(context, filtered_nodes,
                                            request_spec, server_group)
            for server_id, node in zip(request_spec['server_ids'], dest_nodes):
                server_obj = objects.Server.get(
                    context, server_id)
                alloc_data = self._get_res_cls_filters(request_spec)
                self.reportclient.put_allocations(
                    node, server_obj.uuid, alloc_data,
                    server_obj.project_id, server_obj.user_id)
            return dest_nodes

        return _schedule(self, context, request_spec, filter_properties)

    def _choose_nodes(self, context, filtered_nodes, request_spec,
                      server_group=None):
        num_servers = request_spec['num_servers']
        if server_group and 'anti-affinity' in server_group.policies:
            if len(num_servers) > len(filtered_nodes):
                msg = ('Not enough available affinity zones found for servers '
                       'request with anti-affinity requirement, request '
                       '%s servers in different affinity zones, but only '
                       '%s available affinity zones'
                       % (str(num_servers), str(len(filtered_nodes))))
                raise exception.NoValidNode(_("Choose Node: %s") % msg)
            selected = random.sample(filtered_nodes, num_servers)
            return [nodes[0] for nodes in selected]

        if num_servers > len(filtered_nodes):
            msg = 'Not enough nodes found for servers, request ' \
                  'servers: %s, but only available nodes: %s' \
                  % (str(num_servers), str(len(filtered_nodes)))
            raise exception.NoValidNode(_("Choose Node: %s") % msg)

        return filtered_nodes[:num_servers]
