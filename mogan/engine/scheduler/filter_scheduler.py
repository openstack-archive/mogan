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

"""The FilterScheduler is for creating instances.

You can customize this scheduler by specifying your own node Filters and
Weighing Functions.
"""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils

from mogan.common import exception
from mogan.common.i18n import _
from mogan.engine.scheduler import driver
from mogan.engine.scheduler import scheduler_options

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
        instance = request_spec['instance_properties']
        filter_properties['availability_zone'] = \
            instance.get('availability_zone')

    def _add_retry_node(self, filter_properties, node):
        """Add a retry entry for the selected Ironic node.

        In the event that the request gets re-scheduled, this entry will signal
        that the given node has already been tried.
        """
        retry = filter_properties.get('retry', None)
        if not retry:
            return
        nodes = retry['nodes']
        nodes.append(node)

    def _max_attempts(self):
        max_attempts = CONF.scheduler.scheduler_max_attempts
        if max_attempts < 1:
            raise exception.InvalidParameterValue(
                err=_("Invalid value for 'scheduler_max_attempts', "
                      "must be >=1"))
        return max_attempts

    def _log_instance_error(self, instance_id, retry):
        """Log requests with exceptions from previous instance operations."""
        exc = retry.pop('exc', None)  # string-ified exception from instance
        if not exc:
            return  # no exception info from a previous attempt, skip

        nodes = retry.get('nodes', None)
        if not nodes:
            return  # no previously attempted nodes, skip

        last_node = nodes[-1]
        LOG.error(_LE("Error scheduling %(instance_id)s from last node: "
                      "%(last_node)s : %(exc)s"),
                  {'instance_id': instance_id,
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

        # retry is enabled, update attempt count:
        if retry:
            retry['num_attempts'] += 1
        else:
            retry = {
                'num_attempts': 1,
                'nodes': []  # list of Ironic nodes tried
            }
        filter_properties['retry'] = retry

        instance_id = request_spec.get('instance_id')
        self._log_instance_error(instance_id, retry)

        if retry['num_attempts'] > max_attempts:
            raise exception.NoValidNode(
                _("Exceeded max scheduling attempts %(max_attempts)d "
                  "for instance %(instance_id)s") %
                {'max_attempts': max_attempts,
                 'instance_id': instance_id})

    def _get_weighted_candidates(self, context, request_spec,
                                 filter_properties=None):
        """Return a list of nodes that meet required specs.

        Returned list is ordered by their fitness.
        """
        # Since Mogan is using mixed filters from Oslo and it's own, which
        # takes 'resource_XX' and 'instance_XX' as input respectively, copying
        # 'instance_type' to 'resource_type' will make both filters happy.
        instance_type = resource_type = request_spec.get("instance_type")

        config_options = self._get_configuration_options()

        if filter_properties is None:
            filter_properties = {}
        self._populate_retry(filter_properties, request_spec)

        request_spec_dict = jsonutils.to_primitive(request_spec)

        filter_properties.update({'request_spec': request_spec_dict,
                                  'config_options': config_options,
                                  'instance_type': instance_type,
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
        weighed_nodes = self._get_weighted_candidates(context, request_spec,
                                                      filter_properties)
        if not weighed_nodes:
            LOG.warning('No weighed nodes found for instance '
                            'with properties: %s',
                        request_spec.get('instance_type'))
            raise exception.NoValidNode(_("No weighed nodes available"))

        top_node = self._choose_top_node(weighed_nodes, request_spec)
        top_node.obj.consume_from_request(context)
        self._add_retry_node(filter_properties, top_node.obj.node)
        return top_node.obj.node

    def _choose_top_node(self, weighed_nodes, request_spec):
        return weighed_nodes[0]
