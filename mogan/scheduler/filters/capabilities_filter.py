# Copyright (c) 2011 OpenStack Foundation.
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

from oslo_log import log as logging

from mogan.scheduler import filters
from mogan.scheduler.filters import extra_specs_ops

LOG = logging.getLogger(__name__)


class CapabilitiesFilter(filters.BaseNodeFilter):
    """NodeFilter to work with resource instance type records."""

    def _satisfies_extra_specs(self, capabilities, resource_type):
        """Check if capabilities satisfy resource type requirements.

        Check that the capabilities provided by the services satisfy
        the extra specs associated with the resource type.
        """

        if not resource_type:
            return True

        extra_specs = resource_type.get('extra_specs', [])
        if not extra_specs:
            return True

        for key, req in extra_specs.items():

            # Either not scoped format, or in capabilities scope
            scope = key.split(':')

            # Ignore scoped (such as vendor-specific) capabilities
            if len(scope) > 1 and scope[0] != "capabilities":
                continue
            # Strip off prefix if spec started with 'capabilities:'
            elif scope[0] == "capabilities":
                del scope[0]

            cap = capabilities
            for index in range(len(scope)):
                try:
                    cap = cap[scope[index]]
                except (TypeError, KeyError):
                    LOG.debug("Node doesn't provide capability '%(cap)s' " %
                              {'cap': scope[index]})
                    return False

            # Make all capability values a list so we can handle lists
            cap_list = [cap] if not isinstance(cap, list) else cap

            # Loop through capability values looking for any match
            for cap_value in cap_list:
                if extra_specs_ops.match(cap_value, req):
                    break
            else:
                # Nothing matched, so bail out
                LOG.debug('Instance type extra spec requirement '
                          '"%(key)s=%(req)s" does not match reported '
                          'capability "%(cap)s"',
                          {'key': key, 'req': req, 'cap': cap})
                return False
        return True

    def node_passes(self, node_state, filter_properties):
        """Return a list of nodes that can create resource_type."""
        resource_type = filter_properties.get('resource_type')
        if not self._satisfies_extra_specs(node_state.capabilities,
                                           resource_type):
            LOG.debug("%(node_state)s fails resource_type extra_specs "
                      "requirements", {'node_state': node_state})
            return False
        return True
