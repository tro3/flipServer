import os
from unittest import TestCase
import datetime

import mongomock
from app import create_app

import json
from pprint import pprint as p


class ScenarioTests(TestCase):
    
    def set_up(self, endp):
        cfg = {
            'DEBUG': True,
            'CLIENT': mongomock.MongoClient(),
            'ENDPOINTS': endp
        }
        self.app = create_app(**cfg)
        self.db = self.app.db
        self.client = self.app.test_client()
    

    def test_basic_create_auth(self):
        cfg = {
            'users': {
                'auth': {
                    'create': False    
                },
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)

        data = {'username': 'fflint'}
        
        resp = self.client.post('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        
        self.assertEqual(resp.status_code, 403)        
        self.assertEqual(self.db.users.find().count(), 0)


    def test_basic_update_auth(self):
        cfg = {
            'users': {
                'auth': {
                    'edit': False    
                },
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)
        
        self.db.users.insert([
            {'username': 'fflint'},    
            {'username': 'brubble'},    
        ])
        
        data = {'_id':2, '_auth':{'_edit':True, '_delete':True}, 'username': 'brubble', 'active': False}
    
        resp = self.client.put('/api/users/2',
                               data=json.dumps(data),
                               content_type = 'application/json'
                               )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'OK',
            '_item': {'_id':2, '_auth':{'_edit':False, '_delete':True}, 'username': 'brubble', 'active': True},
        })


    def test_schema_change(self):        
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True, 'default': 'fred'},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)

        self.db.users.insert([
            {'username2': 'fflint'},    
        ], direct=True)
                
        resp = self.client.put('/api/users/1',
                               data=json.dumps({'_id':1}),
                               content_type = 'application/json'
                               )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'OK',
            '_item': {'_id':1, '_auth':{'_edit':True, '_delete':True}, 'username': 'fred', 'active': True},
        })


    def test_list_update_delete_fcn_auth(self):
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'roles': {'type':'list', 'schema': {'type':'dict',
                        'auth': {
                            'edit': lambda x: x.active,    
                            'delete': lambda x: x.active    
                        },
                        'schema': {
                            'name': {"type": "string", 'required': True},                        
                            'active': {"type": "boolean", 'required': True, 'default': True},
                        }
                    }}
                }
            }
        }
        self.set_up(cfg)
        
        self.db.users.insert({'username': 'fflint', 'roles': [
            {'name': 'accountant', 'active': True},
            {'name': 'mailman', 'active': False},
        ]},    
        direct=True)
        
        data = {
            '_id': 1,
            'username': 'fflint',
            'roles': [
                {'_id':1, 'name': 'accountant2', 'active': True},
                {'_id':2, 'name': 'mailman2', 'active': False},
            ],
        }
        
        resp = self.client.put('/api/users/1',
                               data=json.dumps(data),
                               content_type = 'application/json'
                               )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'OK',
            '_item': {
                '_id': 1,
                '_auth':{'_edit':True, '_delete':True, 'roles':True},
                'username': 'fflint',
                'roles': [
                    {
                        '_id': 1,
                        '_auth':{'_edit':True, '_delete':True},
                        'name': 'accountant2',
                        'active': True
                    },{
                        '_id': 2,
                        '_auth':{'_edit':False, '_delete':False},
                        'name': 'mailman',
                        'active': False
                    },
                ],
            }
        })


        data = {
            '_id': 1,
            'username': 'fflint',
            'roles': [],
        }
        
        resp = self.client.put('/api/users/1',
                               data=json.dumps(data),
                               content_type = 'application/json'
                               )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'OK',
            '_item': {
                '_id': 1,
                '_auth':{'_edit':True, '_delete':True, 'roles':True},
                'username': 'fflint',
                'roles': [
                    {
                        '_id': 2,
                        '_auth':{'_edit':False, '_delete':False},
                        'name': 'mailman',
                        'active': False
                    },
                ],
            }
        })



    def test_endpoint_callable_auth(self):
        enable = False
        cfg = {
            'users': {
                'auth': {
                    'create': lambda: enable    
                },
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)

        data = {'username': 'fflint'}
        
        resp = self.client.post('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        
        self.assertEqual(resp.status_code, 403)        
        self.assertEqual(self.db.users.find().count(), 0)

        enable = True
        resp = self.client.post('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        
        self.assertEqual(resp.status_code, 201)        
        self.assertEqual(self.db.users.find().count(), 1)


    def test_endpoint_read_auth(self):
        cfg = {
            'users': {
                'auth': {
                    'read': False    
                },
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)

        data = {'username': 'fflint'}
        
        resp = self.client.get('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        
        self.assertEqual(resp.status_code, 403)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Unauthorized',
        })


    def test_null_id_post(self):
        cfg = {
            'users': {
                'auth': {
                    'read': False    
                },
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)

        data = {'_id': None, 'username': 'fflint'}
        
        resp = self.client.post('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        
        self.assertEqual(resp.status_code, 201)        
        data = json.loads(resp.data)
        self.assertEqual(self.db.users.find().count(), 1)


    def test_nonreference(self):
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            },
            'contacts': {
                'schema': {
                    'contact_name': {"type": "string", 'required': True},
                    'users': {"type": "list", 'schema': {
                        'type': 'reference',
                        'collection': 'users'
                    }},
                }
            }
        }
        self.set_up(cfg)

        data = {'username': 'fflint'}
        
        resp = self.client.post('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        
        self.assertEqual(resp.status_code, 201)        


        data = {'contact_name': 'Barney', 'users': [{'_id':2}]}
        
        resp = self.client.post('/api/contacts',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        
        self.assertEqual(resp.status_code, 201)        

        resp = self.client.get('/api/contacts',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'OK',
            '_auth': True,
            '_items': [
                {
                    '_id': 1,
                    '_auth': {'_edit':True, '_delete':True},
                    'contact_name': 'Barney',
                    'users': [{'_err': 'reference not found'}]
                }
            ]
        })


    def test_auth_wprojections(self):
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)

        data = {'username': 'fflint'}
        
        resp = self.client.post('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )        
        self.assertEqual(resp.status_code, 201)        

        resp = self.client.get('/api/users/1',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        
        self.assertEqual(resp.status_code, 200)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'OK',
            '_item':
                {
                    '_id': 1,
                    '_auth': {'_edit':True, '_delete':True},
                    'username': 'fflint',
                    'active': True
                }
        })

        resp = self.client.get('/api/users/1?fields={"username":1}',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        
        self.assertEqual(resp.status_code, 200)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'OK',
            '_item':
                {
                    '_id': 1,
                    '_auth': {'_edit':True, '_delete':True},
                    'username': 'fflint',
                }
        })
