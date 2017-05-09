# Copyright 2017 Huawei Technologies Co.,LTD.
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


from oslo_versionedobjects import base as object_base

from mogan.common import exception
from mogan.db import api as dbapi
from mogan import objects
from mogan.objects import base
from mogan.objects import fields

KEYPAIR_TYPE_SSH = 'ssh'
KEYPAIR_TYPE_X509 = 'x509'


@base.MoganObjectRegistry.register
class KeyPair(base.MoganObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'id': fields.IntegerField(),
        'name': fields.StringField(nullable=False),
        'user_id': fields.StringField(nullable=True),
        'fingerprint': fields.StringField(nullable=True),
        'public_key': fields.StringField(nullable=True),
        'type': fields.StringField(nullable=False),
    }

    @staticmethod
    def _from_db_object(context, keypair, db_keypair):
        ignore = {'deleted': False,
                  'deleted_at': None}
        for key in keypair.fields:
            if key in ignore and not hasattr(db_keypair, key):
                setattr(keypair, key, ignore[key])
            else:
                setattr(keypair, key, db_keypair[key])
        keypair._context = context
        keypair.obj_reset_changes()
        return keypair

    @classmethod
    def get_by_name(cls, context, user_id, name):
        db_keypair = cls.dbapi.key_pair_get(context, user_id, name)
        return cls._from_db_object(context, cls(), db_keypair)

    @classmethod
    def destroy_by_name(cls, context, user_id, name):
        cls.dbapi.key_pair_destroy(context, user_id, name)

    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason='already created')
        try:
            self.dbapi.key_pair_get(self._context, self.user_id, self.name)
            raise exception.KeyPairExists(key_name=self.name)
        except exception.KeypairNotFound:
            pass
        updates = self.obj_get_changes()
        db_keypair = self.dbapi.key_pair_create(self._context, updates)
        self._from_db_object(self._context, self, db_keypair)

    def destroy(self):
        self.dbapi.key_pair_destroy(self._context, self.user_id, self.name)


@base.MoganObjectRegistry.register
class KeyPairList(object_base.ObjectListBase, base.MoganObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    dbapi = dbapi.get_instance()

    fields = {
        'objects': fields.ListOfObjectsField('KeyPair'),
    }

    @classmethod
    def get_count_from_db(cls, context, user_id):
        return cls.dbapi.key_pair_count_by_user(context, user_id)

    @classmethod
    def get_by_user(cls, context, user_id):
        db_keypairs = cls.dbapi.key_pair_get_all_by_user(context, user_id)

        return object_base.obj_make_list(
            context, cls(context), objects.KeyPair, db_keypairs)
