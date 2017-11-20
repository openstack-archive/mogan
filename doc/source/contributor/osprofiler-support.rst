.. _OSProfiler-support:

================
About OSProfiler
================

OSProfiler is an OpenStack cross-project profiling library. Its API
provides different ways to add a new trace point. Trace points contain
two messages (start and stop). Messages like below are sent to a collector::

    {
        "name": <point_name>-(start|stop),
        "base_id": <uuid>,
        "parent_id": <uuid>,
        "trace_id": <uuid>,
        "info": <dict>
    }

The fields are defined as follows:

``base_id`` - <uuid> that is same for all trace points that belong to
one trace. This is used to simplify the process of retrieving all
trace points (related to one trace) from the collector.

``parent_id`` - <uuid> of parent trace point.

``trace_id`` - <uuid> of current trace point.

``info`` - the dictionary that contains user information passed when
calling profiler start() & stop() methods.

The profiler uses ceilometer as a centralized collector. Two other
alternatives for ceilometer are pure MongoDB driver and Elasticsearch.

A notifier is setup to send notifications to ceilometer using oslo.messaging
and ceilometer API is used to retrieve all messages related to one trace.

OSProfiler has entry point that allows the user to retrieve information
about traces and present it in HTML/JSON using CLI.

For more details see `OSProfiler – Cross-project profiling library`_.


How to Use OSProfiler with Mogan in Devstack
=============================================

To use or test OSProfiler in mogan, the user needs to setup Devstack
with OSProfiler and ceilometer. In addition to the setup described at
:ref:`deploy_devstack`, the user needs to do the following:

Add the following to ``localrc`` to enable OSProfiler and ceilometer::

    enable_plugin panko https://git.openstack.org/openstack/panko
    enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer
    enable_plugin osprofiler https://git.openstack.org/openstack/osprofiler


    CEILOMETER_NOTIFICATION_TOPICS=notifications,profiler


Run stack.sh.
Once Devstack environment is setup, edit ``mogan.conf`` to set the following
profiler options and restart mogan services::

    [profiler]
    enabled = True
    hmac_keys = SECRET_KEY # default value used across several OpenStack projects
    trace_sqlalchemy = True


In order to trace mogan using OSProfiler, use openstackclient to run
baremetal commands with ``--os-profile SECRET_KEY``.

For example, the following will cause a <trace-id> to be printed after node list::

    $ openstack --os-profile SECRET_KEY baremetalcompute flavor list

Output of the above command will include the following::

    Trace ID: <trace-id>
    Display trace with command:
    osprofiler trace show --html <trace-id>

The trace results can be seen using this command::

    $ osprofiler trace show --html <trace-id>

The trace results can be saved in a file with ``--out file-name`` option::

    $ osprofiler trace show --html <trace-id> --out trace.html

More detailed db tracing is enabled if ``trace_sqlalchemy`` is set to true.


References
==========

- `OSProfiler – Cross-project profiling library`_
- :ref:`deploy_devstack`

.. _OSProfiler – Cross-project profiling library: https://docs.openstack.org/osprofiler/latest/index.html
