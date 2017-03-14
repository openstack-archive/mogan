===========================================
Welcome to Mogan's developer documentation!
===========================================

Introduction
============

Mogan is an OpenStack project dedicated for bare metal computing management,
which is designed specifically for bare metals, so compared with Nova, we can
provide a more lightweight and convenient platform with more advanced features
by leveraging Ironic. Besides this, we also plan to support RSD, then we can
not only provide Pre-set Configuration Servers, but also Custom Servers.

Site Notes
----------

This site is primarily intended to provide documentation for developers
interested in contributing to or working with mogan. It *also* contains
references and guides for administrators which are not yet hosted elsewhere on
the OpenStack documentation sites.


Developer's Guide
=================

Getting Started
---------------

If you are new to mogan, this section contains information that should help
you get started as a developer working on the project or contributing to the
project.

.. toctree::
  :maxdepth: 1

  Developer Contribution Guide <dev/code-contribution-guide>
  Setting Up Your Development Environment <dev/dev-quickstart>


Administrator's Guide
=====================

Configuration
-------------

There are many aspects of the Bare Metal Compute service which are environment
specific. The following pages will be helpful in configuring specific aspects
of mogan that may or may not be suitable to every situation.

You can use `tox -egenconfig` to generate the sample config file.

Command References
==================

Here are references for commands not elsewhere documented.

.. toctree::
  :maxdepth: 1

  cmds/mogan-dbsync

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
