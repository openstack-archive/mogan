#
# Copyright 2012 OpenStack Foundation
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

from oslo_config import cfg

service_available_group = cfg.OptGroup(name="service_available",
                                       title="Available OpenStack Services")

ServiceAvailableGroup = [
    cfg.BoolOpt("mogan_plugin",
                default=True,
                help="Whether or not Mogan is expected to be available"),
    cfg.BoolOpt("ironic_plugin",
                default=True,
                help="Whether or not Ironic is expected to be available")
]

baremetal_compute_group = cfg.OptGroup(
    name='baremetal_compute_plugin', title='Baremetal compute Service Options')

BaremetalComputeGroup = [
    cfg.StrOpt('baremetal_resource_class',
               default='baremetal_1cpu_1024mbram_10gbdisk',
               help="The resource class of baremetal resource providers, "
                    "which will be reported to placement service and be "
                    "matched with Mogan flavor for scheduling."),
    cfg.StrOpt('catalog_type',
               default='baremetal_compute',
               help="Catalog type of the baremetal_compute service."),
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               choices=['public', 'admin', 'internal',
                        'publicURL', 'adminURL', 'internalURL'],
               help="The endpoint type to use for the baremetal_compute"
                    " service."),
]

baremetal_node_group = cfg.OptGroup(
    name='baremetal_node_plugin', title='Baremetal Service Options')

BaremetalNodeGroup = [
    cfg.StrOpt('catalog_type',
               default='baremetal',
               help="Catalog type of the baremetal service."),
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               choices=['public', 'admin', 'internal',
                        'publicURL', 'adminURL', 'internalURL'],
               help="The endpoint type to use for the baremetal service."),
]
