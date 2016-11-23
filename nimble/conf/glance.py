# Copyright 2016 Intel Corporation
# Copyright 2010 OpenStack Foundation
# Copyright 2013 Hewlett-Packard Development Company, L.P.
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

from nimble.common.i18n import _

opts = [
    cfg.ListOpt('glance_api_servers',
                required=True,
                help=_('A list of the glance api servers available to nimble. '
                       'Prefix with https:// for SSL-based glance API '
                       'servers. Format is [hostname|IP]:port.')),
    cfg.BoolOpt('glance_api_insecure',
                default=False,
                help=_('Allow to perform insecure SSL (https) requests to '
                       'glance.')),
    cfg.IntOpt('glance_num_retries',
               default=0,
               help=_('Number of retries when downloading an image from '
                      'glance.')),
    cfg.StrOpt('glance_cafile',
               help=_('Optional path to a CA certificate bundle to be used to '
                      'validate the SSL certificate served by glance. It is '
                      'used when glance_api_insecure is set to False.')),
]


def register_opts(conf):
    conf.register_opts(opts, group='glance')
