# Copyright 2017 Huawei Technologies Co.,LTD.
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
"""
Request Body validating middleware.

"""

import jsonschema

from mogan.common import exception
from mogan.common.i18n import _


def check_schema(body, schema):
    """Ensure all necessary keys are present and correct in create body.

    Check that the user-specified create body is in the expected format and
    include the required information.

    :param body: create body
    :raises InvalidParameterValue: if validation of create body fails.
    """
    validator = jsonschema.Draft4Validator(
        schema, format_checker=jsonschema.FormatChecker())
    try:
        validator.validate(body)
    except jsonschema.ValidationError as exc:
        raise exception.InvalidParameterValue(_('Invalid create body: %s') %
                                              exc)
