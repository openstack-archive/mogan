# -*- encoding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_concurrency import processutils
from oslo_context import context
from oslo_log import log
import oslo_messaging as messaging
from oslo_service import service
from oslo_service import wsgi
from oslo_utils import importutils

from nimble.api import app
from nimble.common import config
from nimble.common import exception
from nimble.common.i18n import _
from nimble.common.i18n import _LE
from nimble.common.i18n import _LI
from nimble.common import rpc
from nimble.conf import CONF
from nimble import objects
from nimble.objects import base as objects_base

LOG = log.getLogger(__name__)


class RPCService(service.Service):

    def __init__(self, host, manager_module, manager_class, topic):
        super(RPCService, self).__init__()
        self.host = host
        manager_module = importutils.try_import(manager_module)
        manager_class = getattr(manager_module, manager_class)
        self.manager = manager_class(host, topic)
        self.topic = topic
        self.rpcserver = None

    def start(self):
        super(RPCService, self).start()
        admin_context = context.get_admin_context()

        target = messaging.Target(topic=self.topic, server=self.host)
        endpoints = [self.manager]
        serializer = objects_base.NimbleObjectSerializer()
        self.rpcserver = rpc.get_server(target, endpoints, serializer)
        self.rpcserver.start()

        self.manager.init_host()
        self.tg.add_dynamic_timer(
            self.manager.periodic_tasks,
            periodic_interval_max=CONF.periodic_interval,
            context=admin_context)

        LOG.info(_LI('Created RPC server for service %(service)s on host '
                     '%(host)s.'),
                 {'service': self.topic, 'host': self.host})

    def stop(self):
        try:
            self.rpcserver.stop()
            self.rpcserver.wait()
        except Exception as e:
            LOG.exception(_LE('Service error occurred when stopping the '
                              'RPC server. Error: %s'), e)
        try:
            self.manager.del_host()
        except Exception as e:
            LOG.exception(_LE('Service error occurred when cleaning up '
                              'the RPC manager. Error: %s'), e)

        super(RPCService, self).stop(graceful=True)
        LOG.info(_LI('Stopped RPC server for service %(service)s on host '
                     '%(host)s.'),
                 {'service': self.topic, 'host': self.host})


def prepare_service(argv=None):
    argv = [] if argv is None else argv
    log.register_options(CONF)
    log.set_defaults(default_log_levels=CONF.default_log_levels + [
        'eventlet.wsgi.server=INFO', 'neutronclient=WARNING'])
    config.parse_args(argv)
    log.setup(CONF, 'nimble')
    objects.register_all()


def process_launcher():
    return service.ProcessLauncher(CONF)


class WSGIService(service.ServiceBase):
    """Provides ability to launch nimble API from wsgi app."""

    def __init__(self, name, use_ssl=False):
        """Initialize, but do not start the WSGI server.

        :param name: The name of the WSGI server given to the loader.
        :param use_ssl: Wraps the socket in an SSL context if True.
        :returns: None
        """
        self.name = name
        self.app = app.VersionSelectorApplication()
        self.workers = (CONF.api.api_workers or
                        processutils.get_worker_count())
        if self.workers and self.workers < 1:
            raise exception.ConfigInvalid(
                _("api_workers value of %d is invalid, "
                  "must be greater than 0.") % self.workers)

        self.server = wsgi.Server(CONF, name, self.app,
                                  host=CONF.api.host_ip,
                                  port=CONF.api.port,
                                  use_ssl=use_ssl)

    def start(self):
        """Start serving this service using loaded configuration.

        :returns: None
        """
        self.server.start()

    def stop(self):
        """Stop serving this API.

        :returns: None
        """
        self.server.stop()

    def wait(self):
        """Wait for the service to stop serving this API.

        :returns: None
        """
        self.server.wait()

    def reset(self):
        """Reset server greenpool size to default.

        :returns: None
        """
        self.server.reset()
