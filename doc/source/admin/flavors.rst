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
| Resources           | Key and value pairs that corresponds to placement     |
|                     | resource classes and amounts, like ``baremetal=1``.   |
+---------------------+-------------------------------------------------------+
| Resource Aggregates | Key and value pairs that corresponds to node          |
|                     | aggregates metadata.                                  |
+---------------------+-------------------------------------------------------+
| Is Public           | Boolean value, whether flavor is available to all     |
|                     | users or private to the project it was created in.    |
|                     | Defaults to ``True``.                                 |
+---------------------+-------------------------------------------------------+
| Disabled            | Boolean value, whether flavor is available for new    |
|                     | servers creation. It is intended to be used when      |
|                     | phasing out flavors. Defaults to ``False``.           |
+---------------------+-------------------------------------------------------+

.. note::

    Flavors are not allowed to be deleted if there are still live servers
    associated with it. You should disable it instead in such situation.

Is Public
~~~~~~~~~

Flavors can be assigned to particular projects. By default, a flavor is public
and available to all projects. Private flavors are only accessible to those on
the access list and are invisible to other projects. To create and assign a
private flavor to a project, run this command:

.. code-block:: console

   $ openstack baremetalcompute flavor create --private p1.gold --description "gold" \
     --resources gold=1
