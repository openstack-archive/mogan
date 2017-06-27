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
from oslo_config import cfg
from oslo_log import log as logging

from mogan.common import exception
from mogan.common.i18n import _
from mogan.common import utils
from mogan import objects
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
        self.scheduler_client = client.SchedulerClient()
        self.reportclient = self.scheduler_client.reportclient

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

        server_id = request_spec.get('server_id')
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
        resources = dict([(sched_utils.ensure_resource_class(res[0]),
                           int(res[1]))
                          for res in flavor_dict['resources'].items()])
        return resources

    def _get_filtered_nodes(self, request_spec):
        query_filters = {'resources': self._get_res_cls_filters(request_spec)}
        filtered_nodes = self.reportclient.get_filtered_resource_providers(
            query_filters)
        if not filtered_nodes:
            return []
        return [node['uuid'] for node in filtered_nodes]

    def schedule(self, context, request_spec, filter_properties=None):

        # TODO(zhenguo): Scheduler API is inherently multi-threaded as every
        # incoming RPC message will be dispatched in it's own green thread.
        # So we add a syncronized here to make sure the shared node states
        # consistent, but lock the whole schedule process is not a good choice,
        # we need to improve this.
        @utils.synchronized('schedule')
        def _schedule(self, context, request_spec, filter_properties):
            self._populate_retry(filter_properties, request_spec)
            filtered_nodes = self._get_filtered_nodes(request_spec)
            if not filtered_nodes:
                LOG.warning('No filtered nodes found for server '
                            'with properties: %s',
                            request_spec.get('flavor'))
                raise exception.NoValidNode(_("No filtered nodes available"))
            dest_nodes = self._choose_nodes(filtered_nodes, request_spec)
            for node in dest_nodes:
                server_obj = objects.Server.get(
                    context, request_spec['server_id'])
                alloc_data = self._get_res_cls_filters(request_spec)
                self.reportclient.update_server_allocation(
                    node, server_obj.uuid, 1, server_obj.user_id,
                    server_obj.project_id, alloc_data)
            return dest_nodes

        return _schedule(self, context, request_spec, filter_properties)

    def _choose_nodes(self, weighed_nodes, request_spec):
        num_servers = request_spec['num_servers']
        if num_servers > len(weighed_nodes):
            msg = 'Not enough nodes found for servers, request ' \
                  'servers: %s, but only available nodes: %s' \
                  % (str(num_servers), str(len(weighed_nodes)))
            raise exception.NoValidNode(_("Choose Node: %s") % msg)

        return weighed_nodes[:num_servers]
