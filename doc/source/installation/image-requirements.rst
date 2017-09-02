Image requirements
~~~~~~~~~~~~~~~~~~

Mogan bare metal provisioning supports two types of images, partition
images and whole disk images. Both of them support only local boot.

It's important to note that in order for this to work, the partition image
being deployed with Mogan **must** contain ``grub2`` installed within it.

Mogan only support config drive with cloud-init, so the image **must** contain
configdrive datasource.

Build user images
~~~~~~~~~~~~~~~~~

This section describes how to build user images which are installed
on the bare metal server through mogan.

The `disk-image-builder`_ can be used to create user images required for
deployment and the actual OS which the user is going to run.

.. _disk-image-builder: https://docs.openstack.org/diskimage-builder/latest/

#. Partition images

   .. code-block:: console

      $ DIB_CLOUD_INIT_DATASOURCES="ConfigDrive, OpenStack" disk-image-create ubuntu baremetal grub2 dhcp-all-interfaces cloud-init-datasources -o my-image

#. Whole disk images

   .. code-block:: console

      $ DIB_CLOUD_INIT_DATASOURCES="ConfigDrive, OpenStack" disk-image-create ubuntu vm dhcp-all-interfaces cloud-init-datasources -o my-image
