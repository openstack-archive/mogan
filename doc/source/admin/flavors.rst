=======
Flavors
=======

Admin users can use the :command:`openstack baremetalcompute flavor` command to
customize and manage flavors. To see information for this command, run:

.. code-block:: console

    $ openstack baremetalcompute flavor [TAB]
    create  delete  list    set     show    unset

Flavors define these elements:

+---------------------+-------------------------------------------------------+
| Element             | Description                                           |
+=====================+=======================================================+
| Name                | A descriptive name.                                   |
+---------------------+-------------------------------------------------------+
| Description         | Typically used to put hardware specs and aggregates   |
|                     | informations.                                         |
+---------------------+-------------------------------------------------------+
| Resources           | Key and value pairs that corresponds to placement re\ |
|                     | source provider custom resource classes and           |
|                     | ``quantities`` for bare metal node, like\             |
|                     | ``baremetal=1``.                                      |
+---------------------+-------------------------------------------------------+
| Resource Traits     | Key and value pairs that corresponds to placement re\ |
|                     | source provider custom resource classes and           |
|                     | ``qualities`` for bare metal node, like               |
|                     | ``baremetal=FPGA``.                                   |
+---------------------+-------------------------------------------------------+
| Resource Aggregates | Key and value pairs that corresponds to node aggrega\ |
|                     | tes metadata.                                         |
+---------------------+-------------------------------------------------------+
| Is Public           | Boolean value, whether flavor is available to all us\ |
|                     | ers or private to the project it was created in. Def\ |
|                     | aults to ``True``.                                    |
+---------------------+-------------------------------------------------------+
| Disabled            | Boolean value, whether flavor is available for new s\ |
|                     | ervers creation. It is intended to be used when phas\ |
|                     | ing out flavors. Defaults to ``False``.               |
+---------------------+-------------------------------------------------------+

.. note::

    Flavor resource traits are not usable now, as placement doesn't support
    to list resource providers with tratis presently.

Is Public
~~~~~~~~~

Flavors can be assigned to particular projects. By default, a flavor is public
and available to all projects. Private flavors are only accessible to those on
the access list and are invisible to other projects. To create and assign a
private flavor to a project, run this command:

.. code-block:: console

   $ openstack flavor create --private p1.gold --description "gold" --resources gold=1
