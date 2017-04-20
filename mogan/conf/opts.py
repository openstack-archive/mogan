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

import mogan.conf.api
import mogan.conf.configdrive
import mogan.conf.database
import mogan.conf.default
import mogan.conf.engine
import mogan.conf.glance
import mogan.conf.ironic
import mogan.conf.keystone
import mogan.conf.neutron
import mogan.conf.quota
import mogan.conf.scheduler

_default_opt_lists = [
    mogan.conf.default.api_opts,
    mogan.conf.default.exc_log_opts,
    mogan.conf.default.path_opts,
    mogan.conf.default.service_opts,
    mogan.conf.default.utils_opts,
]

_opts = [
    ('DEFAULT', itertools.chain(*_default_opt_lists)),
    ('api', mogan.conf.api.opts),
    ('configdrive', mogan.conf.configdrive.opts),
    ('database', mogan.conf.database.opts),
    ('engine', mogan.conf.engine.opts),
    ('glance', mogan.conf.glance.opts),
    ('ironic', mogan.conf.ironic.ironic_opts),
    ('keystone', mogan.conf.keystone.opts),
    ('neutron', mogan.conf.neutron.opts),
    ('quota', mogan.conf.quota.quota_opts),
    ('scheduler', mogan.conf.scheduler.opts),
]


def list_opts():
    """Return a list of oslo.config options available in Mogan code.

    The returned list includes all oslo.config options. Each element of
    the list is a tuple. The first element is the name of the group, the
    second element is the options.

    The function is discoverable via the 'mogan' entry point under the
    'oslo.config.opts' namespace.

    The function is used by Oslo sample config file generator to discover the
    options.

    :returns: a list of (group, options) tuples
    """
    return _opts
