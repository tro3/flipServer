#!/usr/bin/env python

from schemongo.schema_layer.database import SchemaDatabaseWrapper, SchemaCollectionWrapper, SchemaCursorWrapper
from schemongo.schema_layer.schema_doc import is_object, is_list_of_objects, generate_prototype, enforce_schema_behaviors, \
                                              enforce_datatypes, fill_in_prototypes, merge, run_auto_funcs
from auth_doc import add_authstates, enforce_auth, enforce_auth_read

"""
Config:

auth: {
    create:
    read:
    edit:
    delete:
},
schema: {
    objname: {type: dict,
        auth: {
            read:
            edit:            
        }
        schema:{
        
        }
    }
    listname: {type: list, schema: {type: dict,
        auth: {
            create:
            read:
            edit:
            delete:            
        }
        schema:{
        
        }
    }}
}

"""


def gen_auth(authstate, subdoc=False):
    result = dict(authstate)
    result.pop('_create')
    result.pop('_read')
    if subdoc:
        result.pop('_delete')
    return result



class AuthDatabaseWrapper(SchemaDatabaseWrapper):
    def __init__(self, *args, **kwords):
        super(AuthDatabaseWrapper, self).__init__(*args, **kwords)
        self.endpoints = {}
        
    def __getitem__(self, key):
        return AuthCollectionWrapper(self.endpoints[key], self._db[key], self)
        
    def register_endpoint(self, key, endpoint):
        self.endpoints[key] = endpoint
        schema = endpoint['schema']
        schema['_auth'] = {
            'type': 'dict',
            'serialize': lambda e: gen_auth(e._authstate)
        }                
        self._add_auth_schemas(schema)
        self.register_schema(key, schema)
                                
    def _add_auth_schemas(self, schema):
        for key, val in schema.items():
            if is_object(val):
                val['schema']['_auth'] = {
                    'type': 'dict',
                    'serialize': lambda e: gen_auth(e._authstate, subdoc=True)
                }                
                self._add_auth_schemas(val['schema'])
            if is_list_of_objects(val):
                val['schema']['schema']['_auth'] = {
                    'type': 'dict',
                    'serialize': lambda e: gen_auth(e._authstate)
                }                
                self._add_auth_schemas(val['schema']['schema'])



class AuthCollectionWrapper(SchemaCollectionWrapper):
    def __init__(self, endpoint, collection, db):
        super(AuthCollectionWrapper, self).__init__(endpoint['schema'], collection, db)
        self.endpoint = endpoint

    def find(self, spec=None, fields=None, skip=0, limit=0, sort=None, user=None):
        return AuthSchemaCursorWrapper(self.coll.find(spec, fields, skip, limit, sort), self.db, self.endpoint, user=None)

    def find_one(self, spec_or_id, fields=None, skip=0, sort=None, user=None):
        tmp = self.coll.find_one(spec_or_id, fields, skip, sort)
        add_authstates(self.endpoint, tmp, user)
        enforce_auth_read(self.endpoint, tmp)
        return tmp
    
    def process_insert(self, incoming, direct=False):
        if not direct:
            errs = enforce_datatypes(self.schema, incoming)
            if errs:
                return (None, errs)

        data = generate_prototype(self.schema)
        add_authstates(self.endpoint, data)
        if not direct:
            enforce_auth(self.endpoint, data, incoming)
            
        merge(data, incoming)
        fill_in_prototypes(self.schema, data)
        run_auto_funcs(self.schema, data)
        
        if not direct:
            errs = enforce_schema_behaviors(self.schema, data, self)
            if errs:
                return (None, errs)
            
        return (data, [])


    def process_update(self, incoming, direct=False):
        assert '_id' in incoming, "Cannot update document without _id attribute"

        if not direct:
            errs = enforce_datatypes(self.schema, incoming)
            if errs:
                return (None, errs)

        if not direct:
            data = self.find_one({"_id":incoming["_id"]})
            add_authstates(self.endpoint, data)
            enforce_auth(self.endpoint, data, incoming)
        else:
            data = DBDoc(incoming)

        if not direct:
            merge(data, incoming)
            fill_in_prototypes(self.schema, data)

        run_auto_funcs(self.schema, data)
        if not direct:
            errs = enforce_schema_behaviors(self.schema, data, self)
            if errs:
                return (None, errs)
            
        return (data, [])
    
    
    
class AuthSchemaCursorWrapper(SchemaCursorWrapper):
    def __init__(self, cursor, db, endpoint, user=None):
        SchemaCursorWrapper.__init__(self, cursor, db, endpoint['schema'])
        self.endpoint = endpoint
        self.user = user

    def __getitem__(self, index):
        tmp = SchemaCursorWrapper.__getitem__(self, index)
        add_authstates(self.endpoint, tmp, self.user)
        enforce_auth_read(self.endpoint, tmp)
        return tmp
