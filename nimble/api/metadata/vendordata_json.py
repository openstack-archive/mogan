# Copyright 2013 Canonical Ltd
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

"""Render Vendordata as stored in configured file."""

import errno

from oslo_log import log as logging
from oslo_serialization import jsonutils

from nimble.api.metadata import vendordata
import nimble.conf
from nimble.i18n import _LW

CONF = nimble.conf.CONF
LOG = logging.getLogger(__name__)


class JsonFileVendorData(vendordata.VendorDataDriver):
    def __init__(self, *args, **kwargs):
        super(JsonFileVendorData, self).__init__(*args, **kwargs)
        data = {}
        fpath = CONF.vendordata_jsonfile_path
        logprefix = "vendordata_jsonfile_path[%s]:" % fpath
        if fpath:
            try:
                with open(fpath, "r") as fp:
                    data = jsonutils.load(fp)
            except IOError as e:
                if e.errno == errno.ENOENT:
                    LOG.warning(_LW("%(logprefix)s file does not exist"),
                                {'logprefix': logprefix})
                else:
                    LOG.warning(_LW("%(logprefix)s unexpected IOError when "
                                    "reading"), {'logprefix': logprefix})
                raise
            except ValueError:
                LOG.warning(_LW("%(logprefix)s failed to load json"),
                            {'logprefix': logprefix})
                raise

        self._data = data

    def get(self):
        return self._data
