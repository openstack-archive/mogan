# Copyright (c) 2012 OpenStack Foundation
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

'''
Websocket proxy that is compatible with OpenStack Nova.
Leverages websockify.py by Joel Martin
'''

import socket
import sys

from mogan.conf import CONF
from mogan.common.i18n import _, _LW

from oslo_log import log as logging
from six.moves import http_cookies as Cookie
import six.moves.urllib.parse as urlparse
import websockify

LOG = logging.getLogger(__name__)


class MoganProxyRequestHandlerBase(object):
    def address_string(self):
        # NOTE(rpodolyaka): override the superclass implementation here and
        # explicitly disable the reverse DNS lookup, which might fail on some
        # deployments due to DNS configuration and break VNC access completely
        return str(self.client_address[0])

    def verify_origin_proto(self, connection_info, origin_proto):
        access_url = connection_info.get('access_url')
        if not access_url:
            detail = _("No access_url in connection_info. "
                        "Cannot validate protocol")
            raise Exception(detail)
        expected_protos = [urlparse.urlparse(access_url).scheme]
        # NOTE: For serial consoles the expected protocol could be ws or
        # wss which correspond to http and https respectively in terms of
        # security.
        if 'ws' in expected_protos:
            expected_protos.append('http')
        if 'wss' in expected_protos:
            expected_protos.append('https')

        return origin_proto in expected_protos

    def new_websocket_client(self):
        """Called after a new WebSocket connection has been established."""
        # Reopen the eventlet hub to make sure we don't share an epoll
        # fd with parent and/or siblings, which would be bad
        from eventlet import hubs
        hubs.use_hub()

        # The nova expected behavior is to have token
        # passed to the method GET of the request
        parse = urlparse.urlparse(self.path)
        if parse.scheme not in ('http', 'https'):
            # From a bug in urlparse in Python < 2.7.4 we cannot support
            # special schemes (cf: http://bugs.python.org/issue9374)
            if sys.version_info < (2, 7, 4):
                raise Exception(
                    _("We do not support scheme '%s' under Python < 2.7.4, "
                      "please use http or https") % parse.scheme)

        query = parse.query
        token = urlparse.parse_qs(query).get("token", [""]).pop()
        if not token:
            # NoVNC uses it's own convention that forward token
            # from the request to a cookie header, we should check
            # also for this behavior
            hcookie = self.headers.getheader('cookie')
            if hcookie:
                cookie = Cookie.SimpleCookie()
                for hcookie_part in hcookie.split(';'):
                    hcookie_part = hcookie_part.lstrip()
                    try:
                        cookie.load(hcookie_part)
                    except Cookie.CookieError:
                        # NOTE(stgleb): Do not print out cookie content
                        # for security reasons.
                        LOG.warning(_LW('Found malformed cookie'))
                    else:
                        if 'token' in cookie:
                            token = cookie['token'].value

        # ctxt = context.get_admin_context()
        # rpcapi = consoleauth_rpcapi.ConsoleAuthAPI()
        # connect_info = rpcapi.check_token(ctxt, token=token)

        connect_info = {
            'token': 'fake',
            'instance_uuid': '7b998ca9-aa9b-4855-a17e-e68d30e87490',
            'console_type': 'serial',
            'host': 'http://10.229.40.107',
            'port': 4321,
            #'internal_access_path': internal_access_path,
            #'access_url': access_url,
            #'last_activity_at': time.time()
        }
        #if not connect_info:
        #    raise exception.InvalidToken(token=token)

        # Verify Origin
        # expected_origin_hostname = self.headers.getheader('Host')
        # if ':' in expected_origin_hostname:
        #     e = expected_origin_hostname
        #     if '[' in e and ']' in e:
        #         expected_origin_hostname = e.split(']')[0][1:]
        #     else:
        #         expected_origin_hostname = e.split(':')[0]
        # expected_origin_hostnames = CONF.console_allowed_origins
        # expected_origin_hostnames.append(expected_origin_hostname)
        #origin_url = self.headers.getheader('Origin')
        # missing origin header indicates non-browser client which is OK
        # if origin_url is not None:
        #     origin = urlparse.urlparse(origin_url)
        #     origin_hostname = origin.hostname
        #     origin_scheme = origin.scheme
        #     if origin_hostname == '' or origin_scheme == '':
        #         detail = _("Origin header not valid.")
        #         raise Exception(detail)
        #     if origin_hostname not in expected_origin_hostnames:
        #         detail = _("Origin header does not match this host.")
        #         raise Exception(detail)
            # if not self.verify_origin_proto(connect_info, origin_scheme):
            #     detail = _("Origin header protocol does not match this host.")
            #     raise Exception(detail)

        self.msg(_('connect info: %s'), str(connect_info))
        host = connect_info['host']
        port = int(connect_info['port'])

        # Connect to the target
        self.msg(_("connecting to: %(host)s:%(port)s") % {'host': host,
                                                          'port': port})
        tsock = self.socket(host, port, connect=True)

        # Handshake as necessary
        if connect_info.get('internal_access_path'):
            tsock.send("CONNECT %s HTTP/1.1\r\n\r\n" %
                        connect_info['internal_access_path'])
            while True:
                data = tsock.recv(4096, socket.MSG_PEEK)
                if data.find("\r\n\r\n") != -1:
                    if data.split("\r\n")[0].find("200") == -1:
                        raise Exception('xxxxxxxxxxxx')
                    tsock.recv(len(data))
                    break

        # Start proxying
        try:
            self.do_proxy(tsock)
        except Exception:
            if tsock:
                tsock.shutdown(socket.SHUT_RDWR)
                tsock.close()
                self.vmsg(_("%(host)s:%(port)s: "
                          "Websocket client or target closed") %
                          {'host': host, 'port': port})
            raise


class MoganProxyRequestHandler(MoganProxyRequestHandlerBase,
                              websockify.ProxyRequestHandler):
    def __init__(self, *args, **kwargs):
        websockify.ProxyRequestHandler.__init__(self, *args, **kwargs)

    def socket(self, *args, **kwargs):
        return websockify.WebSocketServer.socket(*args, **kwargs)


class MoganWebSocketProxy(websockify.WebSocketProxy):
    @staticmethod
    def get_logger():
        return LOG
