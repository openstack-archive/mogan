# Copyright 2017 Huawei Technologies Co.,LTD.
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


quota_opts = [
    cfg.StrOpt('quota_driver',
               default="database",
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
    cfg.IntOpt('servers_hard_limit',
               default=10,
               help=_('Number of servers quota hard limit.')),
    cfg.IntOpt('keypairs_hard_limit',
               default=100,
               help=_('Number of keypairs quota hard limit.')),
]

opt_quota_group = cfg.OptGroup(name='quota',
                               title='Options for the mogan quota')


def register_opts(conf):
    conf.register_group(opt_quota_group)
    conf.register_opts(quota_opts, group=opt_quota_group)
