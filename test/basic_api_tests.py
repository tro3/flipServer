import os
from unittest import TestCase
import datetime

import mongomock
from app import create_app

import json
from pprint import pprint as p


class BasicAPITests(TestCase):
    
    def setUp(self):
        cfg = {
            'DEBUG': True,
            'CLIENT': mongomock.MongoClient(),
            'ENDPOINTS': {
                'users': {'schema': {
                    'username': {"type": "string", 'required': True},
                    'active': {"type": "boolean", 'required': True, 'default': True},
                }}
            }
        }
        self.app = create_app(**cfg)
        self.db = self.app.db
        self.client = self.app.test_client()
    

    def test_basics(self):
        resp = self.client.get('/api/users2')
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get('/api/users')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'OK',
            '_auth': True,
            '_items': [],
        })
        
        
    def test_get_list(self, ):
        self.db.users.insert([
            {'username': 'fflint'},    
            {'username': 'brubble'},    
        ])

        resp = self.client.get('/api/users')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        
        self.assertEqual(data, {
            '_status': 'OK',
            '_auth': True,
            '_items': [
                {'_id':1, '_auth':{'_edit':True, '_delete':True}, 'username': 'fflint', 'active': True},
                {'_id':2, '_auth':{'_edit':True, '_delete':True}, 'username': 'brubble', 'active': True},
            ],
        })
        

    def test_get_filtered_list(self, ):
        self.db.users.insert([
            {'username': 'fflint'},    
            {'username': 'brubble'},    
        ])

        resp = self.client.get('/api/users?q={"username":{"$lt":"c"}}')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        
        self.assertEqual(data, {
            '_status': 'OK',
            '_auth': True,
            '_items': [
                {'_id':2, '_auth':{'_edit':True, '_delete':True}, 'username': 'brubble', 'active': True},
            ],
        })


    def test_get_projected_list(self, ):
        self.db.users.insert([
            {'username': 'fflint'},    
            {'username': 'brubble'},    
        ])

        resp = self.client.get('/api/users?fields=["username"]')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'OK',
            '_auth': True,
            '_items': [
                {'_id':1, '_auth':{'_edit':True, '_delete':True}, 'username': 'fflint'},
                {'_id':2, '_auth':{'_edit':True, '_delete':True}, 'username': 'brubble'},
            ],
        })
        
        
    def test_post_list(self, ):
        data = {'username': 'fflint'}
        
        resp = self.client.post('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        
        self.assertEqual(data, {
            '_status': 'OK',
            '_item': {'_id':1, '_auth':{'_edit':True, '_delete':True}, 'username': 'fflint', 'active': True},
        })
        
        data = self.db.users.find_one(1)
        self.assertEqual(data, {'_id':1, '_active': True, 'username': 'fflint', 'active': True})        


    def test_post_multi_list(self, ):
        data = [
            {'username': 'fflint'},
            {'username': 'brubble'},
        ]
        
        resp = self.client.post('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        
        self.assertEqual(data, {
            '_status': 'OK',
            '_items': [
                {'_id':1, '_auth':{'_edit':True, '_delete':True}, 'username': 'fflint', 'active': True},
                {'_id':2, '_auth':{'_edit':True, '_delete':True}, 'username': 'brubble', 'active': True},
            ]
                
        })
        
        data = self.db.users.find_one(2)
        self.assertEqual(data, {'_id':2, '_active': True, 'username': 'brubble', 'active': True})        
        

    def test_post_error(self, ):
        data = {}
        
        resp = self.client.post('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Field errors',
            'field_errors': ['username: value is required'],
        })
        
        self.assertEqual(self.db.users.find().count(), 0)        
        

    def test_post_multi_error(self, ):
        data = [
            {'username': 'fflint'},
            {},
            {'username': 'brubble'},
        ]
        
        resp = self.client.post('/api/users',
                                data=json.dumps(data),
                                content_type = 'application/json'
                                )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Field errors',
            'field_errors': [[],['username: value is required'], []],
        })
        
        self.assertEqual(self.db.users.find().count(), 0)        
        

    def test_get_single(self, ):
        self.db.users.insert([
            {'username': 'fflint'},    
            {'username': 'brubble'},    
        ])
    
        resp = self.client.get('/api/users/2')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'OK',
            '_item': {'_id':2, '_auth':{'_edit':True, '_delete':True}, 'username': 'brubble', 'active': True},
        })
        
        
    def test_put_single(self, ):
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
            '_item': {'_id':2, '_auth':{'_edit':True, '_delete':True}, 'username': 'brubble', 'active': False},
        })
        
        data = self.db.users.find_one(2)
        self.assertEqual(data, {'_id':2, '_active': True, 'username': 'brubble', 'active': False})        


    def test_put_single_error(self, ):
        self.db.users.insert([
            {'username': 'fflint'},    
            {'username': 'brubble'},    
        ])
        
        data = {'_id':2, '_auth':{'_edit':True, '_delete':True}, 'username': None, 'active': False}
    
        resp = self.client.put('/api/users/2',
                               data=json.dumps(data),
                               content_type = 'application/json'
                               )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, {
            '_status': 'ERR',
            'message': 'Field errors',
            'field_errors': ['username: value is required'],
        })
        
        data = self.db.users.find_one(2)
        self.assertEqual(data, {'_id':2, '_active': True, 'username': 'brubble', 'active': True})        


    def test_delete_single(self, ):
        self.db.users.insert([
            {'username': 'fflint'},    
            {'username': 'brubble'},    
        ])
        
        resp = self.client.delete('/api/users/2')
        self.assertEqual(resp.status_code, 204)
        
        self.assertEqual(self.db.users.find().count(), 1)
