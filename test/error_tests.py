import os
from unittest import TestCase
import datetime

import mongomock
from app import create_app

import json
from pprint import pprint as p


class ErrorTests(TestCase):
    
    def set_up(self, endp):
        cfg = {
            'DEBUG': True,
            'CLIENT': mongomock.MongoClient(),
            'ENDPOINTS': endp
        }
        self.app = create_app(**cfg)
        self.db = self.app.db
        self.client = self.app.test_client()


    def test_datatype_errs(self):
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'id': {"type": "integer", 'required': True},
                }
            }
        }
        self.set_up(cfg)
        
        data = {
            'username': 'fflint',
            'id': 'bob',
        }
        
        resp = self.client.post('/api/users',
                               data=json.dumps(data),
                               content_type = 'application/json'
                               )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Field errors',
            'field_errors': [
                "id: Could not convert 'bob' to type 'integer'"
            ]
        })

        self.db.users.insert({
            'username': 'fflint',
            'id': 345,
        })

        data = {
            '_id': 1,
            'username': 'fflint',
            'id': 'bob',
        }
        
        resp = self.client.put('/api/users/1',
                               data=json.dumps(data),
                               content_type = 'application/json'
                               )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Field errors',
            'field_errors': [
                "id: Could not convert 'bob' to type 'integer'"
            ]
        })


    def test_endpoint_malformed(self):
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)
        
        resp = self.client.get('/api/users?q={i dont get it}',
                                content_type = 'application/json'
                                )        
        self.assertEqual(resp.status_code, 400)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Malformed data',
        })


        data = {'username': 'fflint'}        
        resp = self.client.post('/api/users',
                                data="{i dont get this, either}",
                                content_type = 'application/json'
                                )
        self.assertEqual(resp.status_code, 400)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Malformed data',
        })


    def test_endpoint_existing(self):
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)
        
        data = {'_id':1, 'username': 'fflint'}        
        resp = self.client.post('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        self.assertEqual(resp.status_code, 400)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Cannot POST with _id',
        })


    def test_endpoint_wrong_cmd(self):
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)
        
        data = {'_id':1, 'username': 'fflint'}        
        resp = self.client.put('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        self.assertEqual(resp.status_code, 405)        


    def test_item_notfound(self):
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)
        
        resp = self.client.get('/api/users/10',
                               )
        self.assertEqual(resp.status_code, 404)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Item not found',
        })


    def test_item_fields_malformed(self):
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)
        
        self.db.users.insert({'username':'fflint'})
        
        resp = self.client.get('/api/users/1?fields=[better]')
        self.assertEqual(resp.status_code, 400)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Malformed data',
        })


    def test_item_read_auth(self):
        cfg = {
            'users': {
                'auth': {
                    'read': False,
                },
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)
        
        self.db.users.insert({'username':'fflint'})
        
        resp = self.client.get('/api/users/1')
        self.assertEqual(resp.status_code, 403)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Unauthorized',
        })


    def test_item_put_malformed(self):
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)
        self.db.users.insert({'username':'fflint'})
        
        data = {'username': 'fflint'}        
        resp = self.client.put('/api/users/1',
                                data="{i dont get this, either}",
                                content_type = 'application/json'
                                )
        self.assertEqual(resp.status_code, 400)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Malformed data',
        })


    def test_item_wrong_id(self):
        cfg = {
            'users': {
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)
        self.db.users.insert({'username':'fflint'})
        
        data = {'_id':2, 'username': 'fflint'}        
        resp = self.client.put('/api/users/1',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        self.assertEqual(resp.status_code, 400)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Incorrect ID',
        })


    def test_delete_auth(self):
        enable = False
        cfg = {
            'users': {
                'auth': {
                    'delete': lambda x: enable 
                },
                'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }
            }
        }
        self.set_up(cfg)
        self.db.users.insert({'username':'fflint'})
        
        resp = self.client.delete('/api/users/1')
        self.assertEqual(resp.status_code, 403)        
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Unauthorized',
        })
        self.assertEqual(self.db.users.find().count(), 1)

        enable = True
        resp = self.client.delete('/api/users/1')
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(self.db.users.find().count(), 0)
