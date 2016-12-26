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


# FIXME(Shaohe): can not import mogan.common.paths.basedir_def
# There will be a circle import.
def basedir_def(*args):
    """Return an uninterpolated path relative to $pybasedir."""
    return os.path.join('$pybasedir', *args)

config_drive_opts = [
    cfg.StrOpt(
        'config_drive_format',
        default='iso9660',
        choices=('iso9660', 'vfat'),
        help="""
Configuration drive format

Configuration drive format that will contain metadata attached to the
instance when it boots.

Possible values:

* iso9660: A file system image standard that is widely supported across
  operating systems. NOTE: Mind the libvirt bug
  (https://bugs.launchpad.net/mogan/+bug/1246201) - If your hypervisor
  driver is libvirt, and you want live migrate to work without shared storage,
  then use VFAT.
* vfat: For legacy reasons, you can configure the configuration drive to
  use VFAT format instead of ISO 9660.

Related options:

* This option is meaningful when one of the following alternatives occur:
  1. force_config_drive option set to 'true'
  2. the REST API call to create the instance contains an enable flag for
     config drive option
  3. the image used to create the instance requires a config drive,
     this is defined by img_config_drive property for that image.
* A compute node running Hyper-V hypervisor can be configured to attach
  configuration drive as a CD drive. To attach the configuration drive as a CD
  drive, set config_drive_cdrom option at hyperv section, to true.
"""),
    cfg.BoolOpt(
        'force_config_drive',
        default=False,
        help="""
Force injection to take place on a config drive

When this option is set to true configuration drive functionality will be
forced enabled by default, otherwise user can still enable configuration
drives via the REST API or image metadata properties.

Possible values:

* True: Force to use of configuration drive regardless the user's input in the
        REST API call.
* False: Do not force use of configuration drive. Config drives can still be
         enabled via the REST API or image metadata properties.

Related options:

* Use the 'mkisofs_cmd' flag to set the path where you install the
  genisoimage program. If genisoimage is in same path as the
  mogan-compute service, you do not need to set this flag.
* To use configuration drive with Hyper-V, you must set the
  'mkisofs_cmd' value to the full path to an mkisofs.exe installation.
  Additionally, you must set the qemu_img_cmd value in the hyperv
  configuration section to the full path to an qemu-img command
  installation.
"""),
    cfg.StrOpt(
        'mkisofs_cmd',
        default='genisoimage',
        help="""
Name or path of the tool used for ISO image creation

Use the mkisofs_cmd flag to set the path where you install the genisoimage
program. If genisoimage is on the system path, you do not need to change
the default value.

To use configuration drive with Hyper-V, you must set the mkisofs_cmd value
to the full path to an mkisofs.exe installation. Additionally, you must set
the qemu_img_cmd value in the hyperv configuration section to the full path
to an qemu-img command installation.

Possible values:

* Name of the ISO image creator program, in case it is in the same directory
  as the mogan-compute service
* Path to ISO image creator program

Related options:

* This option is meaningful when config drives are enabled.
* To use configuration drive with Hyper-V, you must set the qemu_img_cmd
  value in the hyperv configuration section to the full path to an qemu-img
  command installation.
"""),
    cfg.BoolOpt(
        "use_ipv6",
        default=False,
        help="""
Assign IPv6 and IPv4 addresses when creating instances.

"""),
    cfg.StrOpt(
        'injected_network_template',
        default=basedir_def('engine/interfaces.template'),
        help="""Path to '/etc/network/interfaces' template.

The path to a template file for the '/etc/network/interfaces'-style file, which
will be populated by mogan and subsequently used by cloudinit. This provides a
method to configure network connectivity in environments without a DHCP server.

The template will be rendered using Jinja2 template engine, and receive a
top-level key called ``interfaces``. This key will contain a list of
dictionaries, one for each interface.

Refer to the cloudinit documentaion for more information:

  https://cloudinit.readthedocs.io/en/latest/topics/datasources.html

Possible values:

* A path to a Jinja2-formatted template for a Debian '/etc/network/interfaces'
  file. This applies even if using a non Debian-derived guest.

Related options:

* ``flat_inject``: This must be set to ``True`` to ensure mogan embeds network
  configuration information in the metadata provided through the config drive.
"""),
    cfg.StrOpt(
        "vendordata_jsonfile_path",
        deprecated_group="default",
        help="""
Cloud providers may store custom data in vendor data file that will then be
available to the instances via the metadata service, and to the rendering of
config-drive. The default class for this, JsonFileVendorData, loads this
information from a JSON file, whose path is configured by this option. If
there is no path set by this option, the class returns an empty dictionary.

Possible values:

* Any string representing the path to the data file, or an empty string
    (default).
"""),
    # FIXME(Shaohe): Need to remove this one.
    cfg.StrOpt(
        "vendordata_driver",
        default="mogan.api.metadata.vendordata_json.JsonFileVendorData",
        deprecated_for_removal=True,
        deprecated_since="13.0.0",
        help="""
When returning instance metadata, this is the class that is used
for getting vendor metadata when that class isn't specified in the individual
request. The value should be the full dot-separated path to the class to use.

Possible values:

* Any valid dot-separated class path that can be imported.
"""),
    # FIXME(Shaohe): Need to remove this one.
    cfg.StrOpt(
        "dhcp_domain",
        default="moganlocal",
        deprecated_for_removal=True,
        deprecated_since='15.0.0',
        deprecated_reason="""
nova-network is deprecated, as are any related configuration options.
""",
        help="""
This option allows you to specify the domain for the DHCP server.

Possible values:

    Any string that is a valid domain name.

Related options:

    ``use_neutron``
"""),
    cfg.ListOpt(
        'vendordata_providers',
        default=[],
        deprecated_group="default",
        help="""
A list of vendordata providers.

vendordata providers are how deployers can provide metadata via configdrive
and metadata that is specific to their deployment. There are currently two
supported providers: StaticJSON and DynamicJSON.

StaticJSON reads a JSON file configured by the flag vendordata_jsonfile_path
and places the JSON from that file into vendor_data.json and
vendor_data2.json.

DynamicJSON is configured via the vendordata_dynamic_targets flag, which is
documented separately. For each of the endpoints specified in that flag, a
section is added to the vendor_data2.json.

For more information on the requirements for implementing a vendordata
dynamic endpoint, please see the vendordata.rst file in the nova developer
reference.

Possible values:

* A list of vendordata providers, with StaticJSON and DynamicJSON being
  current options.

Related options:

* vendordata_dynamic_targets
* vendordata_dynamic_ssl_certfile
* vendordata_dynamic_connect_timeout
* vendordata_dynamic_read_timeout
"""),
]


def register_opts(conf):
    conf.register_opts(config_drive_opts)


def list_opts():
    return {"DEFAULT": config_drive_opts}
