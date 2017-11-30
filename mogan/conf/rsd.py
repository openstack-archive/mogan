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
    cfg.RSDUrl('url',
               help=_('The URL that is used to access pod manager.'
                      'It should include scheme and authority portion of the '
                      'URL. (for example "https://127.0.0.1:8443/redfish/v1"),'
                      'Defaults to None. If you want to use RSD, must '
                      'support the RSD pod manager URL.')),
    cfg.RSDUser('user',
                default='admin',
                help=_('User account with admin/server-profile access'
                       'privilege to access pod manager.')),
    cfg.RSDPassword('password',
                    default='admin',
                    help=_('User account password to access pod manager.')),
    cfg.RSDTlsVerify('tls_verify',
                     default=True,
                     help=_('Either a boolean value, a path to a CA_BUNDLE'
                            'file or directory with certificates of trusted '
                            'CAs. If set to True mogan will verify the host '
                            'certificates; if False mogan will ignore '
                            'verifying the SSL certificate; if it\'s a path '
                            'the driver will use the specified certificate or '
                            'one of the certificates in the directory. '
                            'Defaults to True.')),
]


opt_group = cfg.OptGroup(name='rsd',
                         title='Options for the rsd')


def register_opts(conf):
    conf.register_group(opt_group)
    conf.register_opts(opts, group=opt_group)
