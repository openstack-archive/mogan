# -*- mode: python -*-
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
"""Use this file for deploying the API under uwsgi.

See http://pecan.readthedocs.org/en/latest/deployment.html for details.
"""
import sys

from mogan.api import app
from mogan.common import service as mogan_service

mogan_service.prepare_service(sys.argv)
application = app.VersionSelectorApplication()
