# Copyright 2015 OpenStack Foundation
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

shellinabox_opt_group = cfg.OptGroup("shellinabox_console",
                                     title="The shellinabox console feature",
                                     help="""
The shellinabox console feature allows you to connect to a guest in case a
graphical console like VNC, RDP or SPICE is not available. This is only
currently supported for the Ironic driver.""")

shellinaboxproxy_host_opt = cfg.IPOpt('shellinaboxproxy_host',
                                      default='0.0.0.0',
                                      help="""
The IP address which is used by the ``mogan-shellinaboxproxy`` service to
listen for incoming requests.

The ``mogan-shellinaboxproxy`` service listens on this IP address for incoming
connection requests to instances which expose shellinabox serial console.

Possible values:

* An IP address

Services which consume this:

* ``mogan-shellinaboxproxy``

Interdependencies to other options:

* Ensure that this is the same IP address which is defined in the option
  ``shellinabox_base_url`` of this section or use ``0.0.0.0`` to listen on
  all addresses.
""")

shellinaboxproxy_port_opt = cfg.PortOpt('shellinaboxproxy_port',
                                        default=8866,
                                        min=1,
                                        max=65535,
                                        help="""
The port number which is used by the ``mogan-shellinaboxproxy`` service to
listen for incoming requests.

The ``mogan-shellinaboxproxy`` service listens on this port number for incoming
connection requests to instances which expose shellinabox serial console.

Possible values:

* A port number

Services which consume this:

* ``mogan-shellinaboxproxy``

Interdependencies to other options:

* Ensure that this is the same port number which is defined in the option
  ``shellinabox_base_url`` of this section.
""")

shellinabox_base_url_opt = cfg.URIOpt('shellinabox_base_url',
                                      default='http://127.0.0.1:8866/',
                                      help="""
The URL an end user would use to connect to the ``mogan-shellinaboxproxy``
service.

The ``mogan-shellinaboxproxy`` service is called with this token enriched URL
and establishes the connection to the proper instance.

Possible values:

* <scheme><IP-address><port-number>

Services which consume this:

* ``mogan-engine``

Interdependencies to other options:

* The IP address must be identical to the address to which the
  ``mogan-shellinaboxproxy`` service is listening (see option
  ``shellinaboxproxy_host``in this section).
* The port must be the same as in the option ``shellinaboxproxy_port`` of this
  section.
""")

ALL_OPTS = [shellinabox_base_url_opt]


def register_opts(conf):
    conf.register_group(shellinabox_opt_group)
    conf.register_opts(ALL_OPTS, group=shellinabox_opt_group)


def register_cli_opts(conf):
    conf.register_group(shellinabox_opt_group)
    conf.register_cli_opts(ALL_OPTS, shellinabox_opt_group)


def list_opts():
    return {shellinabox_opt_group: ALL_OPTS}
