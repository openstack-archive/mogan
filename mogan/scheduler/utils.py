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

"""Utility methods for scheduling."""

import functools

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def retry_on_timeout(retries=1):
    """Retry the call in case a MessagingTimeout is raised.

    A decorator for retrying calls when a service dies mid-request.

    :param retries: Number of retries
    :returns: Decorator
    """

    def outer(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except messaging.MessagingTimeout:
                    attempt += 1
                    if attempt <= retries:
                        LOG.warning(
                            "Retrying %(name)s after a MessagingTimeout, "
                            "attempt %(attempt)s of %(retries)s.",
                            {'attempt': attempt, 'retries': retries,
                             'name': func.__name__})
                    else:
                        raise

        return wrapped

    return outer


retry_select_destinations = retry_on_timeout(CONF.scheduler.max_attempts - 1)
