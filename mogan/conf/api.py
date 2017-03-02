# Copyright 2016 Huawei Technologies Co.,LTD.
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

from oslo_config import cfg

from mogan.common.i18n import _

opts = [
    cfg.StrOpt('host_ip',
               default='0.0.0.0',
               help=_('The IP address on which mogan-api listens.')),
    cfg.PortOpt('port',
                default=6688,
                help=_('The TCP port on which mogan-api listens.')),
    cfg.IntOpt('max_limit',
               default=1000,
               help=_('The maximum number of items returned in a single '
                      'response from a collection resource.')),
    cfg.StrOpt('public_endpoint',
               help=_("Public URL to use when building the links to the API "
                      "resources (for example, \"https://mogan.rocks:6688\")."
                      " If None the links will be built using the request's "
                      "host URL. If the API is operating behind a proxy, you "
                      "will want to change this to represent the proxy's URL. "
                      "Defaults to None.")),
    cfg.IntOpt('api_workers',
               help=_('Number of workers for OpenStack Mogan API service. '
                      'The default is equal to the number of CPUs available '
                      'if that can be determined, else a default worker '
                      'count of 1 is returned.')),
    cfg.BoolOpt('enable_ssl_api',
                default=False,
                help=_("Enable the integrated stand-alone API to service "
                       "requests via HTTPS instead of HTTP. If there is a "
                       "front-end service performing HTTPS offloading from "
                       "the service, this option should be False; note, you "
                       "will want to change public API endpoint to represent "
                       "SSL termination URL with 'public_endpoint' option.")),
    cfg.StrOpt('multi_instance_name_template',
               default='%(name)s-%(count)d',
               help='When creating multiple instances with a single request '
                    'this template will be used to build the instance name '
                    'for each instance. The benefit is that the instances '
                    'end up with different names. To restore legacy '
                    'behavior of every instance having the same name, set '
                    'this option to "%(name)s".  Valid keys for the '
                    'template are: name, uuid, count.'),
]

opt_group = cfg.OptGroup(name='api',
                         title='Options for the mogan-api service')

quota_opts = [
    cfg.StrOpt('quota_driver',
               help=_("Specify the quota driver which is used in Mogan "
                      "service.")),
    cfg.IntOpt('reservation_expire',
               default=86400,
               help=_('Number of seconds until a reservation expires')),
    cfg.IntOpt('until_refresh',
               default=0,
               help=_('Count of reservations until usage is refreshed')),
    cfg.IntOpt('max_age',
               default=0,
               help=_('Number of seconds between subsequent usage refreshes')),
]

opt_quota_group = cfg.OptGroup(name='quota',
                               title='Options for the mogan quota')


def register_opts(conf):
    conf.register_group(opt_group)
    conf.register_opts(opts, group=opt_group)
    conf.register_group(opt_quota_group)
    conf.register_opts(quota_opts, group=opt_quota_group)
