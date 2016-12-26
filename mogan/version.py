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

import pbr.version

from mogan.common.i18n import _LE


MOGAN_PRODUCT = "OpenStack Mogan"
MOGAN_PACKAGE = None  # OS distro package version suffix

loaded = False
version_info = pbr.version.VersionInfo('mogan')


def _load_config():
    # Don't load in global context, since we can't assume
    # these modules are accessible when distutils uses
    # this module
    from six.moves import configparser

    from oslo_config import cfg

    from oslo_log import log as logging

    global loaded, MOGAN_VENDOR, MOGAN_PRODUCT, MOGAN_PACKAGE
    if loaded:
        return

    loaded = True

    cfgfile = cfg.CONF.find_file("release")
    if cfgfile is None:
        return

    try:
        cfg = configparser.RawConfigParser()
        cfg.read(cfgfile)

        if cfg.has_option("Mogan", "vendor"):
            MOGAN_VENDOR = cfg.get("Mogan", "vendor")

        if cfg.has_option("Mogan", "product"):
            MOGAN_PRODUCT = cfg.get("Mogan", "product")

        if cfg.has_option("Mogan", "package"):
            MOGAN_PACKAGE = cfg.get("Mogan", "package")
    except Exception as ex:
        LOG = logging.getLogger(__name__)
        LOG.error(_LE("Failed to load %(cfgfile)s: %(ex)s"),
                  {'cfgfile': cfgfile, 'ex': ex})


def product_string():
    _load_config()
    return MOGAN_PRODUCT


def package_string():
    _load_config()

    return MOGAN_PACKAGE


def version_string_with_package():
    if package_string() is None:
        return version_info.version_string()
    else:
        return "%s-%s" % (version_info.version_string(), package_string())
