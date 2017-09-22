# Copyright 2016 Huawei Technologies Co.,LTD.
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

"""Functionality related to notifications common to multiple layers of
the system.
"""

from mogan.notifications.objects import base as notification_base
from mogan.notifications.objects import exception as notification_exception
from mogan.notifications.objects import server as server_notification
from mogan.objects import fields


def _get_fault_and_priority_from_exc(exception):
    fault = None
    priority = fields.NotificationPriority.INFO

    if exception:
        priority = fields.NotificationPriority.ERROR
        fault = notification_exception.ExceptionPayload.from_exception(
            exception)

    return fault, priority


def notify_about_server_action(context, server, host, action, phase=None,
                               binary='mogan-engine', exception=None):
    """Send versioned notification about the action made on the server
    :param server: the server which the action performed on
    :param host: the host emitting the notification
    :param action: the name of the action
    :param phase: the phase of the action
    :param binary: the binary emitting the notification
    :param exception: the thrown exception (used in error notifications)
    """

    fault, priority = _get_fault_and_priority_from_exc(exception)

    payload = server_notification.ServerActionPayload(
        server=server,
        fault=fault)
    notification = server_notification.ServerActionNotification(
        context=context,
        priority=priority,
        publisher=notification_base.NotificationPublisher(
            context=context, host=host, binary=binary),
        event_type=notification_base.EventType(
            object='server',
            action=action,
            phase=phase),
        payload=payload)
    notification.emit(context)
