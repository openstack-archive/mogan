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
from oslo_serialization import jsonutils

from mogan.common import exception
from mogan.common.i18n import _
from mogan.common import utils
from mogan.scheduler import driver
from mogan.scheduler import scheduler_options

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class FilterScheduler(driver.Scheduler):
    """Scheduler that can be used for filtering and weighing."""
    def __init__(self, *args, **kwargs):
        super(FilterScheduler, self).__init__(*args, **kwargs)
        self.options = scheduler_options.SchedulerOptions()
        self.max_attempts = self._max_attempts()

    def _get_configuration_options(self):
        """Fetch options dictionary. Broken out for testing."""
        return self.options.get_configuration()

    def populate_filter_properties(self, request_spec, filter_properties):
        """Stuff things into filter_properties.

        Can be overridden in a subclass to add more data.
        """
        server = request_spec['server_properties']
        filter_properties['availability_zone'] = \
            server.get('availability_zone')

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

    def _get_weighted_candidates(self, context, request_spec,
                                 filter_properties=None):
        """Return a list of nodes that meet required specs.

        Returned list is ordered by their fitness.
        """
        # Since Mogan is using mixed filters from Oslo and it's own, which
        # takes 'resource_XX' and 'server_XX' as input respectively, copying
        # 'flavor' to 'resource_type' will make both filters happy.
        flavor = resource_type = request_spec.get("flavor")

        config_options = self._get_configuration_options()

        if filter_properties is None:
            filter_properties = {}
        self._populate_retry(filter_properties, request_spec)

        request_spec_dict = jsonutils.to_primitive(request_spec)

        filter_properties.update({'request_spec': request_spec_dict,
                                  'config_options': config_options,
                                  'flavor': flavor,
                                  'resource_type': resource_type})

        self.populate_filter_properties(request_spec,
                                        filter_properties)

        # Find our local list of acceptable nodes by filtering and
        # weighing our options. we virtually consume resources on
        # it so subsequent selections can adjust accordingly.

        # Note: remember, we are using an iterator here. So only
        # traverse this list once.
        nodes = self.node_manager.get_all_node_states(context)

        # Filter local nodes based on requirements ...
        nodes = self.node_manager.get_filtered_nodes(nodes,
                                                     filter_properties)
        if not nodes:
            return []

        LOG.debug("Filtered %(nodes)s", {'nodes': nodes})
        # weighted_node = WeightedNode() ... the best
        # node for the job.
        weighed_nodes = self.node_manager.get_weighed_nodes(nodes,
                                                            filter_properties)
        LOG.debug("Weighed %(nodes)s", {'nodes': weighed_nodes})
        return weighed_nodes

    def schedule(self, context, request_spec, filter_properties=None):

        # TODO(zhenguo): Scheduler API is inherently multi-threaded as every
        # incoming RPC message will be dispatched in it's own green thread.
        # So we add a syncronized here to make sure the shared node states
        # consistent, but lock the whole schedule process is not a good choice,
        # we need to improve this.
        @utils.synchronized('schedule')
        def _schedule(self, context, request_spec, filter_properties):
            weighed_nodes = self._get_weighted_candidates(
                context, request_spec, filter_properties)
            if not weighed_nodes:
                LOG.warning('No weighed nodes found for server '
                            'with properties: %s',
                            request_spec.get('flavor'))
                raise exception.NoValidNode(_("No weighed nodes available"))

            node = self._choose_top_node(weighed_nodes, request_spec)
            node.obj.consume_from_request(context)
            dest = dict(node_uuid=node.obj.node_uuid, ports=node.obj.ports)
            return dest

        return _schedule(self, context, request_spec, filter_properties)

    def _choose_top_node(self, weighed_nodes, request_spec):
        return weighed_nodes[0]
