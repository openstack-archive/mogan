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

"""
The Mogan console auth Service
"""

import sys

from oslo_config import cfg
from oslo_reports import guru_meditation_report as gmr
from oslo_reports import opts as gmr_opts
from oslo_service import service

from mogan.common import constants
from mogan.common import service as mogan_service
from mogan import version

CONF = cfg.CONF


def main():
    gmr_opts.set_defaults(CONF)
    # Parse config file and command line options, then start logging
    mogan_service.prepare_service(sys.argv)

    gmr.TextGuruMeditation.setup_autorun(version, conf=CONF)

    mgr = mogan_service.RPCService('mogan.consoleauth.manager',
                                   'ConsoleAuthManager',
                                   constants.MANAGER_CONSOLEAUTH_TOPIC)

    launcher = service.launch(CONF, mgr, restart_method='mutate')
    launcher.wait()
