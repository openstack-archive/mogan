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

from oslo_config import cfg

from nimble.common.i18n import _
from nimble.conf import auth

opts = [
    cfg.StrOpt('url',
               help=_("URL for connecting to neutron.")),
    cfg.IntOpt('url_timeout',
               default=30,
               help=_('Timeout value for connecting to neutron in seconds.')),
    cfg.IntOpt('retries',
               default=3,
               help=_('Client retries in the case of a failed request.')),
]

opt_group = cfg.OptGroup(name='neutron',
                         title='Options for the neutron service')


def register_opts(conf):
    conf.register_group(opt_group)
    conf.register_opts(opts, group=opt_group)


def list_opts():
    return auth.add_auth_opts(opts)
