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

import select
import socket

import BaseHTTPServer
import six
import SocketServer
import urlparse
from oslo_context import context

from mogan.consoleauth import rpcapi as consoleauth_rpcapi
from mogan.common import exception


class ProxyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    rbufsize = 0

    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def _connect_to(self, connect_info, soc):
        host_port = connect_info['host'], connect_info['port']
        try:
            soc.connect(host_port)
        except socket.error as e:
            self.send_error(404, six.text_type(e))
            return 0
        return 1

    def _check_valid(self):
        query = urlparse.urlparse(self.path).query
        token = urlparse.parse_qs(query).get("token", [""]).pop()
        referer = self.headers.get('Referer', None)
        if not token:
            token = referer.split('?token=')[1]

        ctxt = context.get_admin_context()
        rpcapi = consoleauth_rpcapi.ConsoleAuthAPI()
        connect_info = rpcapi.check_token(ctxt, token=token)

        if not connect_info:
            self.send_error(404, 'The token is invalid or has expired')
            self.connection.close()
            raise exception.InvalidToken(token=token)

        return connect_info

    def do_CONNECT(self):
        connect_info = self._check_valid()

        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self._connect_to(connect_info, soc):
                self.log_request(200)
                self.wfile.write(
                    self.protocol_version +
                    " 200 Connection Established\r\nConnection: close\r\n\r\n")
                self.wfile.write("\r\n")
                self._read_write(soc, 300)
        finally:
            soc.close()
            self.connection.close()

    def do_GET(self):
        connect_info = self._check_valid()

        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self._connect_to(connect_info, soc):
                self.log_request()
                soc.send("%s %s %s\r\n" % (
                    self.command,
                    urlparse.urlunparse(('', '', self.path, '', '', '')),
                    self.request_version))
                self.headers['Connection'] = 'close'
                for key_val in self.headers.items():
                    soc.send("%s: %s\r\n" % key_val)
                soc.send("\r\n")
                if self.command != 'GET':
                    length = int(self.headers['content-length'])
                    content = self.rfile.read(length)
                    soc.send("%s\r\n" % content)
                soc.send("\r\n")
                self._read_write(soc)
        finally:
            soc.close()
            self.connection.close()

    def _read_write(self, soc, max_idling=20):
        iw = [self.connection, soc]
        ow = []
        count = 0
        while 1:
            count += 1
            (ins, _, exs) = select.select(iw, ow, iw, 3)
            if exs:
                break
            if ins:
                for i in ins:
                    if i is soc:
                        out = self.connection
                    else:
                        out = soc
                    data = i.recv(8192)
                    if data:
                        out.send(data)
                        count = 0
            if count == max_idling:
                break

    def do_OPTIONS(self):
        try:
            self.send_response(200)
            self.end_headers()
        except Exception:
            pass

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET


class ThreadingHTTPServer(SocketServer.ThreadingMixIn,
                          BaseHTTPServer.HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, logger=None):
        BaseHTTPServer.HTTPServer.__init__(self, server_address,
                                           RequestHandlerClass)

    def service_start(self):
        self.serve_forever()
