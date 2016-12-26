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

from nimble.conf import api
from nimble.conf import configdrive
from nimble.conf import database
from nimble.conf import default
from nimble.conf import engine
from nimble.conf import glance
from nimble.conf import ironic
from nimble.conf import keystone
from nimble.conf import neutron
from nimble.conf import scheduler

CONF = cfg.CONF

api.register_opts(CONF)
configdrive.register_opts(CONF)
database.register_opts(CONF)
default.register_opts(CONF)
engine.register_opts(CONF)
glance.register_opts(CONF)
ironic.register_opts(CONF)
keystone.register_opts(CONF)
neutron.register_opts(CONF)
scheduler.register_opts(CONF)
