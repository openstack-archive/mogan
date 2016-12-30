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
import os

from oslo_config import cfg
from oslo_log import log
from paste import deploy
import pecan

from nimble.api import config
from nimble.api import hooks
from nimble.api import middleware
from nimble.conf import CONF
from nimble.common.i18n import _LI

LOG = log.getLogger(__name__)


def get_pecan_config():
    # Set up the pecan configuration
    filename = config.__file__.replace('.pyc', '.py')
    return pecan.configuration.conf_from_file(filename)


def init_app(pecan_config=None, extra_hooks=None):
    if not pecan_config:
        pecan_config = get_pecan_config()
    app_hooks = [hooks.ConfigHook(),
                 hooks.DBHook(),
                 hooks.EngineAPIHook(),
                 hooks.ContextHook(),
                 hooks.NoExceptionTracebackHook(),
                 hooks.PublicUrlHook()]
    if extra_hooks:
        app_hooks.extend(extra_hooks)

    pecan.configuration.set_config(dict(pecan_config), overwrite=True)

    app = pecan.make_app(
        pecan_config.app.root,
        static_root=pecan_config.app.static_root,
        debug=False,
        force_canonical=getattr(pecan_config.app, 'force_canonical', True),
        hooks=app_hooks,
        wrap_app=middleware.ParsableErrorMiddleware,
    )
    return app


def setup_app(pecan_cfg=None, paste_cfg_file=None):
    if not paste_cfg_file:
        paste_cfg = CONF.api.paste_config
        paste_cfg_file = None
        if not os.path.isabs(paste_cfg):
            paste_cfg_file = CONF.find_file(paste_cfg)
        elif os.path.exists(paste_cfg):
            paste_cfg_file = paste_cfg
        if not paste_cfg:
            raise cfg.ConfigFilesNotFoundError([CONF.api.paste_config])
    LOG.info(_LI("Full WSGI config used: %s"), paste_cfg_file)
    global_conf = {}
    if pecan_cfg:
        global_conf.update({'pecan_cfg': pecan_cfg})
    return deploy.loadapp("config:" + paste_cfg_file, global_conf=global_conf)


def app_factory(global_config, **local_conf):
    pecan_config = global_config.pop('pecan_cfg', None)
    return init_app(pecan_config=pecan_config)
