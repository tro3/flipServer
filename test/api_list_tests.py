import os
from unittest import TestCase
import datetime

import mongomock
from app import create_app

import json
from pprint import pprint as p


class APIBasicListTests(TestCase):
    
    def setUp(self):
        cfg = {
            'DEBUG': True,
            'CLIENT': mongomock.MongoClient(),
            'ENDPOINTS': {
                'users': {'schema': {'username': {"type": "string"}}}
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
        ], direct=True)

        resp = self.client.get('/api/users')
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
        

    def test_get_filtered_list(self, ):
        self.db.users.insert([
            {'username': 'fflint'},    
            {'username': 'brubble'},    
        ], direct=True)

        resp = self.client.get('/api/users?q={"username":{"$lt":"c"}}')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        
        self.assertEqual(data, {
            '_status': 'OK',
            '_auth': True,
            '_items': [
                {'_id':2, '_auth':{'_edit':True, '_delete':True}, 'username': 'brubble'},
            ],
        })
        
        
    
    #def test_post_list(self, ):
    #    data = {'username': 'fflint'}
    #    
    #    
    #    resp = self.client.post('/api/users',
    #                            data=json.dumps({"username":"fflint"}),
    #                            content_type = 'application/json'
    #                            )
    #    self.assertEqual(resp.status_code, 201)
    #    data = json.loads(resp.data)
    #    p(data)
    #    
    #    self.assertEqual(data, {
    #        '_status': 'OK',
    #        '_item': {'_id':1, '_auth':{'_edit':True, '_delete':True}, 'username': 'fflint'},
    #    })
    #    
    #    data = self.db.users.find_one(1)
    #    self.assertEqual(data, {'_id':1, 'username': 'fflint'})        
        
