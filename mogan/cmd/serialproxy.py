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
Websocket proxy that is compatible with OpenStack Nova
Serial consoles. Leverages websockify.py by Joel Martin.
Based on nova-novncproxy.
"""
import os
import sys

from oslo_log import log as logging

from mogan.conf import serial_console as serial

from mogan.conf import CONF
from mogan.console import websocketproxy
from mogan.common import service as mogan_service

serial.register_cli_opts(CONF)


def main():
    # set default web flag option
    CONF.set_default('web', None)
    mogan_service.prepare_service(sys.argv)

    proxy(host=CONF.serial_console.serialproxy_host,
          port=CONF.serial_console.serialproxy_port)


def exit_with_error(msg, errno=-1):
    sys.stderr.write(msg + '\n')
    sys.exit(errno)


def proxy(host, port):
    if CONF.ssl_only and not os.path.exists(CONF.cert):
        exit_with_error("SSL only and %s not found" % CONF.cert)

    # Check to see if tty html/js/css files are present
    if CONF.web and not os.path.exists(CONF.web):
        exit_with_error("Can not find html/js files at %s." % CONF.web)

    logging.setup(CONF, "mogan")

    # Create and start the MoganWebSockets proxy
    websocketproxy.MoganWebSocketProxy(
        listen_host=host,
        listen_port=port,
        source_is_ipv6=CONF.source_is_ipv6,
        cert=CONF.cert,
        key=CONF.key,
        ssl_only=CONF.ssl_only,
        daemon=CONF.daemon,
        record=CONF.record,
        traffic=not CONF.daemon,
        web=CONF.web,
        file_only=True,
        RequestHandlerClass=websocketproxy.MoganProxyRequestHandler
    ).start_server()
