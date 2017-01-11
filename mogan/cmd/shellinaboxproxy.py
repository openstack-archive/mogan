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

import sys

from mogan.conf import CONF
from mogan.console import shellinaboxproxy
from mogan.common import service as mogan_service
from mogan.conf import shellinabox

shellinabox.register_cli_opts(CONF)


def main():
    mogan_service.prepare_service(sys.argv)

    server_address = (CONF.shellinabox_console.shellinaboxproxy_host,
                      CONF.shellinabox_console.shellinaboxproxy_port)

    httpd = shellinaboxproxy.ThreadingHTTPServer(
        server_address,
        shellinaboxproxy.ProxyHandler)
    httpd.service_start()
