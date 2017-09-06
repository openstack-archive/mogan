Build user images
=================

Mogan bare metal provisioning supports two types of images, partition
images and whole disk images.

But we only support local boot, so it's important to note that in order
for this to work, the partition image being deployed with Mogan **must**
contain ``grub2`` installed within it.

Config Drive
************

The configuration drive is used to store server specific metadata.
``Cloud-init`` has a collection of data source modules, so when building the
image with `disk-image-builder`_ we have to define ``DIB_CLOUD_INIT_DATASOURCES``
environment variable and set the appropriate sources to enable the configuration
drive, for example::

    DIB_CLOUD_INIT_DATASOURCES="ConfigDrive, OpenStack" disk-image-create -o fedora-cloud-image fedora baremetal grub2

For more information see `how to configure cloud-init data sources
<https://docs.openstack.org/diskimage-builder/latest/elements/cloud-init-datasources/README.html>`_.

Build images with disk-image-builder
************************************

The `disk-image-builder`_ can be used to create user images required for
deployment and the actual OS which the user is going to run.

.. _disk-image-builder: https://docs.openstack.org/diskimage-builder/latest/

#. Partition images

   .. code-block:: console

      $ DIB_CLOUD_INIT_DATASOURCES="ConfigDrive, OpenStack" disk-image-create ubuntu baremetal grub2 dhcp-all-interfaces cloud-init-datasources -o my-image

#. Whole disk images

   .. code-block:: console

      $ DIB_CLOUD_INIT_DATASOURCES="ConfigDrive, OpenStack" disk-image-create ubuntu vm dhcp-all-interfaces cloud-init-datasources -o my-image

.. _disk-image-builder: https://docs.openstack.org/diskimage-builder/latest/
