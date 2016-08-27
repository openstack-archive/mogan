# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools

import nimble.conf.api
import nimble.conf.database
import nimble.conf.default
import nimble.conf.engine
import nimble.conf.ironic
import nimble.conf.neutron

_default_opt_lists = [
    nimble.conf.default.api_opts,
    nimble.conf.default.exc_log_opts,
    nimble.conf.default.path_opts,
    nimble.conf.default.service_opts,
]

_opts = [
    ('DEFAULT', itertools.chain(*_default_opt_lists)),
    ('api', nimble.conf.api.opts),
    ('database', nimble.conf.database.opts),
    ('engine', nimble.conf.engine.opts),
    ('ironic', nimble.conf.ironic.opts),
    ('neutron', nimble.conf.neutron.opts),
]


def list_opts():
    """Return a list of oslo.config options available in Nimble code.

    The returned list includes all oslo.config options. Each element of
    the list is a tuple. The first element is the name of the group, the
    second element is the options.

    The function is discoverable via the 'nimble' entry point under the
    'oslo.config.opts' namespace.

    The function is used by Oslo sample config file generator to discover the
    options.

    :returns: a list of (group, options) tuples
    """
    return _opts
