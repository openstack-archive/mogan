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

from nimble.common.i18n import _

opts = [
    cfg.StrOpt('scheduler_driver',
               default='nimble.engine.scheduler.filter_scheduler.'
                       'FilterScheduler',
               help=_('Default scheduler driver to use')),
    cfg.StrOpt('scheduler_node_manager',
               default='nimble.engine.scheduler.node_manager.NodeManager',
               help=_('The scheduler node manager class to use')),
    cfg.IntOpt('scheduler_max_attempts',
               default=3,
               help=_('Maximum number of attempts to schedule a node')),
    cfg.StrOpt('scheduler_json_config_location',
               default='',
               help=_('Absolute path to scheduler configuration JSON file.')),
    cfg.ListOpt('scheduler_default_filters',
                default=[
                    'AvailabilityZoneFilter',
                    'CapabilitiesFilter'
                ],
                help=_('Which filter class names to use for filtering nodes '
                       'when not specified in the request.')),
    cfg.ListOpt('scheduler_default_weighers',
                default=[],
                help=_('Which weigher class names to use for weighing '
                       'nodes.')),
    cfg.StrOpt('scheduler_weight_handler',
               default='nimble.engine.scheduler.weights.'
                       'OrderedNodeWeightHandler',
               help=_('Which handler to use for selecting the node after '
                      'weighing')),
]

# These opts are registered as a separate OptGroup
trusted_opts = [
    cfg.StrOpt("attestation_server",
            help="""
The host to use as the attestation server.

Cloud computing pools can involve thousands of compute nodes located at
different geographical locations, making it difficult for cloud providers to
identify a node's trustworthiness. When using the Trusted filter, users can
request that their VMs only be placed on nodes that have been verified by the
attestation server specified in this option.

The value is a string, and can be either an IP address or FQDN.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect. Also note that this setting
only affects scheduling if the 'TrustedFilter' filter is enabled.

* Services that use this:

    ``nimble-scheduler``

* Related options:

    attestation_server_ca_file
    attestation_port
    attestation_api_url
    attestation_auth_blob
    attestation_auth_timeout
    attestation_insecure_ssl
"""),
    cfg.StrOpt("attestation_server_ca_file",
            help="""
The absolute path to the certificate to use for authentication when connecting
to the attestation server. See the `attestation_server` help text for more
information about host verification.

The value is a string, and must point to a file that is readable by the
scheduler.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect. Also note that this setting
only affects scheduling if the 'TrustedFilter' filter is enabled.

* Services that use this:

    ``nimble-scheduler``

* Related options:

    attestation_server
    attestation_port
    attestation_api_url
    attestation_auth_blob
    attestation_auth_timeout
    attestation_insecure_ssl
"""),
    cfg.StrOpt("attestation_port",
            default="8443",
            help="""
The port to use when connecting to the attestation server. See the
`attestation_server` help text for more information about host verification.

Valid values are strings, not integers, but must be digits only.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect. Also note that this setting
only affects scheduling if the 'TrustedFilter' filter is enabled.

* Services that use this:

    ``nimble-scheduler``

* Related options:

    attestation_server
    attestation_server_ca_file
    attestation_api_url
    attestation_auth_blob
    attestation_auth_timeout
    attestation_insecure_ssl
"""),
    cfg.StrOpt("attestation_api_url",
            default="/OpenAttestationWebServices/V1.0",
            help="""
The URL on the attestation server to use. See the `attestation_server` help
text for more information about host verification.

This value must be just that path portion of the full URL, as it will be joined
to the host specified in the attestation_server option.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect. Also note that this setting
only affects scheduling if the 'TrustedFilter' filter is enabled.

* Services that use this:

    ``nimble-scheduler``

* Related options:

    attestation_server
    attestation_server_ca_file
    attestation_port
    attestation_auth_blob
    attestation_auth_timeout
    attestation_insecure_ssl
"""),
    cfg.StrOpt("attestation_auth_blob",
            help="""
Attestation servers require a specific blob that is used to authenticate. The
content and format of the blob are determined by the particular attestation
server being used. There is no default value; you must supply the value as
specified by your attestation service. See the `attestation_server` help text
for more information about host verification.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect. Also note that this setting
only affects scheduling if the 'TrustedFilter' filter is enabled.

* Services that use this:

    ``nimble-scheduler``

* Related options:

    attestation_server
    attestation_server_ca_file
    attestation_port
    attestation_api_url
    attestation_auth_timeout
    attestation_insecure_ssl
"""),
    cfg.IntOpt("attestation_auth_timeout",
            default=60,
            help="""
This value controls how long a successful attestation is cached. Once this
period has elapsed, a new attestation request will be made. See the
`attestation_server` help text for more information about host verification.

The value is in seconds. Valid values must be positive integers for any
caching; setting this to zero or a negative value will result in calls to the
attestation_server for every request, which may impact performance.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect. Also note that this setting
only affects scheduling if the 'TrustedFilter' filter is enabled.

* Services that use this:

    ``nimble-scheduler``

* Related options:

    attestation_server
    attestation_server_ca_file
    attestation_port
    attestation_api_url
    attestation_auth_blob
    attestation_insecure_ssl
"""),
    cfg.BoolOpt("attestation_insecure_ssl",
            default=False,
            help="""
When set to True, the SSL certificate verification is skipped for the
attestation service. See the `attestation_server` help text for more
information about host verification.

Valid values are True or False. The default is False.

This option is only used by the FilterScheduler and its subclasses; if you use
a different scheduler, this option has no effect. Also note that this setting
only affects scheduling if the 'TrustedFilter' filter is enabled.

* Services that use this:

    ``nimble-scheduler``

* Related options:

    attestation_server
    attestation_server_ca_file
    attestation_port
    attestation_api_url
    attestation_auth_blob
    attestation_auth_timeout
"""),
]

def register_opts(conf):
    conf.register_opts(opts, group='scheduler')
    conf.register_opts(trusted_opts, group='trusted_node')
