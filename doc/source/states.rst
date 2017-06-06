States and Transitions
======================

The following diagram shows the states that a server goes through
during the lifetime.

Allowed State Transitions
--------------------------

.. graphviz::

  digraph states {
    graph [pad=".35", ranksep="0.65", nodesep="0.55", concentrate=true];
    node [fontsize=10 fontname="Monospace"];
    edge [arrowhead="normal", arrowsize="0.8"];
    label="All states are allowed to transition to DELETING and ERROR.";
    forcelabels=true;
    labelloc=bottom;
    labeljust=left;

    /* states */
    building [label="BUILDING"]
    active [label="ACTIVE"]
    stopped [label="STOPPED"]
    powering_on [label="POWERING_ON"]
    powering_off [label="POWERING_OFF"]
    soft_powering_off [label="SOFT_POWERING_OFF"]
    rebooting [label="REBOOTING"]
    soft_rebooting [label="SOFT_REBOOTING"]
    rebuilding [label="REBUILDING"]
    deleting [label="DELETING", color="red"]
    error [label="ERROR", color="red"]

    /* transitions [action] */
    active -> rebuilding
    active -> powering_off
    active -> soft_powering_off
    active -> rebooting
    active -> soft_rebooting

    stopped -> powering_on
    stopped -> rebuilding

    building -> active
    rebuilding -> active
    powering_on -> active
    powering_off -> stopped
    soft_powering_off -> stopped
    rebooting -> active
    soft_rebooting -> active
  }
