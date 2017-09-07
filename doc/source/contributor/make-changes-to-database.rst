==============================
Making changes to the database
==============================

In order to make a change to the mogan database you must update the database
models and then create a migration to reflect that change.

There are two ways to create a migration which are described below, both of
these generate a new migration file. In this file there is only one function:

* ``upgrade`` - The function to run when
    ``mogan-dbsync upgrade`` is run, and should be populated with
    code to bring the database up to its new state from the state it was in
    after the last migration.

For further information on creating a migration, refer to
`Create a Migration Script`_ from the alembic documentation.

Autogenerate
------------

This is the simplest way to create a migration. Alembic will compare the models
to an up to date database, and then attempt to write a migration based on the
differences. This should generate correct migrations in most cases however
there are some cases when it can not detect some changes and may require
manual modification, see `What does Autogenerate Detect (and what does it not
detect?)`_ from the alembic documentation.

::

    mogan-dbsync upgrade
    mogan-dbsync revision -m "A short description" --autogenerate

Manual
------

This will generate an empty migration file, with the correct revision
information already included. However the upgrade function is left empty
and must be manually populated in order to perform the correct actions on
the database::

    mogan-dbsync revision -m "A short description"

.. _Create a Migration Script: http://alembic.zzzcomputing.com/en/latest/tutorial.html#create-a-migration-script
.. _What does Autogenerate Detect (and what does it not detect?): http://alembic.zzzcomputing.com/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect
