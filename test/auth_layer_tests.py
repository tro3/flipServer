import os
from unittest import TestCase
import datetime

import mongomock
from app.api import auth_layer
from schemongo.db_layer.db_doc import DBDoc

import json
from pprint import pprint as p


class AuthLayerTests(TestCase):
    
    def setUp(self):
        self.db = auth_layer.init(mongomock.MongoClient())
        self.db.register_endpoint('users', {
            'schema': {'username': {"type": "string"}}
        })

        data = [
            {'_id':1, 'username': 'bob'}
        ]
        ids, errs = self.db.users.insert(data)
        self.assertIsNone(errs)
        
        self.user = data[0]
    

    def test_basics(self):
        self.db.register_endpoint('test', {
            'schema': {
                "name": {"type": "string"},
                "subdoc": {"type": "dict", "schema": {
                    "data": {"type":"integer"}
                }},
                "hash": {"type": "dict"},
                "num_list": {"type": "list", "schema": {"type": "integer"}},
                "doclist": {"type": "list", "schema": {"type": "dict", "schema": {
                    "name": {"type":"string"}
                }}},
            }
        })


        data = {
            "name": "Bob",
            "subdoc": {
                "data": 4
            },
            "hash": {4:5},
            "num_list": [4,5],
            "doclist": [{"name": "Fred"}]
        }
        ids, errs = self.db.test.insert(data, self.user)
        self.assertIsNone(errs)
        
        data = self.db.test.find_one({"name":"Bob"})
        self.assertEqual(type(data), DBDoc)
        self.assertEqual(data, {
            "_id": 1,
            "_active": True,
            "name": "Bob",
            "subdoc": {
                "_id": 1,
                "data": 4
            },
            "hash": {"_id": 1, 4:5},
            "num_list": [4,5],
            "doclist": [{"_id": 1, "name": "Fred"}]
        })

        errs = self.db.test.update({"_id":1, "name":"Bob2"})
        self.assertIsNone(errs)
        data = json.loads(self.db.test.find_one_and_serialize({"_id":1}))
        self.assertEqual(data, {
            "_id": 1,
            "_auth": {
                "_edit": True,
                "_delete": True,
                "doclist": True
            },
            "name": "Bob2",
            "subdoc": {
                "_id": 1,
                "_auth": {
                    "_edit": True,
                },
                "data": 4
            },
            "hash": {"_id": 1, '4':5},
            "num_list": [4,5],
            "doclist": [
                {
                    "_id": 1,
                    "_auth": {
                        "_edit": True,
                        "_delete": True
                    },
                    "name": "Fred"
                }
            ]
        })


    def test_readonly(self):
        self.db.register_endpoint('test', {
            'schema': {
                "name": {"type": "string"},
                "subdoc": {"type": "dict",
                    "auth": {
                        "read": False    
                    },
                    "schema": {
                        "data": {"type":"integer"}
                    }
                },
                "doclist": {"type": "list", "schema": {"type": "dict",
                    "auth": {
                        "read": lambda element: element.name == "Fred"    
                    },
                    "schema": {
                        "name": {"type":"string"}
                    }
                }},
            }
        })

        data = {
            "name": "Bob",
            "subdoc": {
                "data": 4
            },
            "doclist": [{"name": "Fred"}, {"name": "George"}]
        }
        ids, errs = self.db.test.insert(data, self.user)
        self.assertIsNone(errs)

        data = json.loads(self.db.test.find_one_and_serialize({"_id":1}))
        self.assertEqual(data, {
            "_id": 1,
            "_auth": {
                "_edit": True,
                "_delete": True,
                "doclist": True
            },
            "name": "Bob",
            "doclist": [
                {
                    "_id": 1,
                    "_auth": {
                        "_edit": True,
                        "_delete": True
                    },
                    "name": "Fred"
                }
            ]
        })


    def test_find(self):
        self.db.register_endpoint('test', {
            'schema': {
                "name": {"type": "string"},
                "user": {
                    "type": "reference",
                    "collection": "users",
                    "fields": ['username']
                },
                "subdoc": {"type": "dict", "schema": {
                    "data": {"type":"integer"}
                }},
                "doclist": {"type": "list", "schema": {"type": "dict", "schema": {
                    "name": {"type":"string"}
                }}},
            }
        })


        data = {
            "name": "Bob",
            "user": {"_id": 1},
            "subdoc": {
                "data": 4
            },
            "doclist": [{"name": "Fred"}]
        }
        ids, errs = self.db.test.insert(data, self.user)
        self.assertIsNone(errs)

        data = {
            "name": "George",
            "user": {"_id": 1},
            "subdoc": {
                "data": 4
            },
            "doclist": [{"name": "Fred"}]
        }
        ids, errs = self.db.test.insert(data, self.user)
        self.assertIsNone(errs)

        data = json.loads(self.db.test.find_and_serialize({"name":"George"}))
        self.assertEqual(data, [{
            "_id": 2,
            "_auth": {
                "_edit": True,
                "_delete": True,
                "doclist": True
            },
            "name": "George",
            "user": {
                '_id':1,
                "_auth": {
                    "_edit": True,
                    "_delete": True
                },
                'username': 'bob'
            },
            "subdoc": {
                "_id": 1,
                "_auth": {
                    "_edit": True,
                },
                "data": 4
            },
            "doclist": [
                {
                    "_id": 1,
                    "_auth": {
                        "_edit": True,
                        "_delete": True
                    },
                    "name": "Fred"
                }
            ]
        }])


    def test_auth_propagation(self):
        self.db.register_endpoint('test', {
            'schema': {
                "name": {"type": "string"},
                "subdoc": {"type": "dict", "schema": {
                    "data": {"type":"integer"},
                    "ssubdoc": {"type": "dict",
                        "auth": {
                            "edit": False,
                        },
                        "schema": {
                            "data": {"type":"integer"},
                        }
                    },
                }},
                "doclist": {"type": "list", "schema": {"type": "dict",
                    "auth": {
                        "create": False,
                        "edit": lambda e: e._id == 2,
                    },
                    "schema": {
                        "name": {"type":"string"},
                        "subdoc": {"type": "dict", "schema": {
                            "data": {"type":"integer"},
                            "ssubdoc": {"type": "dict", "schema": {
                                "data": {"type":"integer"},
                            }},
                        }},
                    }
                }},
            }
        })


        data = {
            "name": "Bob",
            "subdoc": {
                "data": 4,
                "ssubdoc": {
                    "data": 4
                },
            },
            "doclist": [
                {
                    "name": "Fred",
                    "subdoc": {
                        "data": 4,
                        "ssubdoc": {
                            "data": 4
                        },
                    },
                },
                {
                    "name": "Fred",
                    "subdoc": {
                        "data": 4,
                        "ssubdoc": {
                            "data": 4
                        },
                    },
                }
            ]
        }
        ids, errs = self.db.test.insert(data, self.user, direct=True)
        self.assertIsNone(errs)

        data = json.loads(self.db.test.find_one_and_serialize(1))
        self.assertEqual(data, {
            "_id": 1,
            "_auth": {
                "_edit": True,
                "_delete": True,
                "doclist": False
            },
            "name": "Bob",
            "subdoc": {
                "_id": 1,
                "_auth": {
                    "_edit": True
                },
                "data": 4,
                "ssubdoc": {
                    "_id": 1,
                    "_auth": {
                        "_edit": False
                    },
                    "data": 4
                },
            },
            "doclist": [
                {
                    "_id": 1,
                    "_auth": {
                        "_edit": False,
                        "_delete": True,
                    },
                    "name": "Fred",
                    "subdoc": {
                        "_id": 1,
                        "_auth": {
                            "_edit": False
                        },
                        "data": 4,
                        "ssubdoc": {
                            "_id": 1,
                            "_auth": {
                                "_edit": False
                            },
                            "data": 4
                        },
                    },
                },
                {
                    "_id": 2,
                    "_auth": {
                        "_edit": True,
                        "_delete": True,
                    },
                    "name": "Fred",
                    "subdoc": {
                        "_id": 1,
                        "_auth": {
                            "_edit": True
                        },
                        "data": 4,
                        "ssubdoc": {
                            "_id": 1,
                            "_auth": {
                                "_edit": True
                            },
                            "data": 4
                        },
                    },
                }
            ]
        })



    def test_auth_incoming_edit(self):
        self.db.register_endpoint('test', {
            'schema': {
                "name": {"type": "string"},
                "subdoc": {"type": "dict", "schema": {
                    "data": {"type":"integer"},
                    "ssubdoc": {"type": "dict",
                        "auth": {
                            "edit": False,
                        },
                        "schema": {
                            "data": {"type":"integer"},
                        }
                    },
                }},
                "doclist": {"type": "list", "schema": {"type": "dict",
                    "auth": {
                        "create": False,
                        "delete": lambda e: e._id == 2,
                    },
                    "schema": {
                        "name": {"type":"string"},
                        "subdoc": {"type": "dict", "schema": {
                            "data": {"type":"integer"},
                            "ssubdoc": {"type": "dict", "schema": {
                                "data": {"type":"integer"},
                            }},
                        }},
                    }
                }},
            }
        })


        data = {
            "name": "Bob",
            "subdoc": {
                "data": 4,
                "ssubdoc": {
                    "data": 4
                },
            },
            "doclist": [
                {
                    "name": "Fred",
                    "subdoc": {
                        "data": 4,
                        "ssubdoc": {
                            "data": 4
                        },
                    },
                },
                {
                    "name": "Fred",
                    "subdoc": {
                        "data": 4,
                        "ssubdoc": {
                            "data": 4
                        },
                    },
                }
            ]
        }
        ids, errs = self.db.test.insert(data, self.user, direct=True)
        self.assertIsNone(errs)
        
        incoming = {
            "_id": 1,
            "_auth": {
                "_edit": True,
                "_delete": True,
                "doclist": False
            },
            "name": "Bob",
            "subdoc": {
                "_id": 1,
                "_auth": {
                    "_edit": True
                },
                "data": 5,
                "ssubdoc": {
                    "_id": 1,
                    "_auth": {
                        "_edit": False
                    },
                    "data": 5
                },
            },
            "doclist": [{"name":"Shouldn't be entered"}]
        }
        errs = self.db.test.update(incoming, self.user)
        self.assertIsNone(errs)

        data = json.loads(self.db.test.find_one_and_serialize(1))
        self.assertEqual(data, {
            "_id": 1,
            "_auth": {
                "_edit": True,
                "_delete": True,
                "doclist": False
            },
            "name": "Bob",
            "subdoc": {
                "_id": 1,
                "_auth": {
                    "_edit": True
                },
                "data": 5,
                "ssubdoc": {
                    "_id": 1,
                    "_auth": {
                        "_edit": False
                    },
                    "data": 4
                },
            },
            "doclist": [
                {
                    "_id": 1,
                    "_auth": {
                        "_edit": True,
                        "_delete": False,
                    },
                    "name": "Fred",
                    "subdoc": {
                        "_id": 1,
                        "_auth": {
                            "_edit": True
                        },
                        "data": 4,
                        "ssubdoc": {
                            "_id": 1,
                            "_auth": {
                                "_edit": True
                            },
                            "data": 4
                        },
                    },
                }
            ]
        })
        
        
        
    def test_reference_expansion(self):
        self.db.register_endpoint('test', {
            'schema': {
                "name": {"type": "string"},
                "contact": {
                    'type': 'reference',
                    'collection': 'users'
                },
                "contacts": {"type": "list", "schema": {
                    'type': 'reference',
                    'collection': 'users'
                }},
            }
        })

        data = {'_id':2, 'username': 'fred'}
        ids, errs = self.db.users.insert(data, self.user, direct=True)
        self.assertIsNone(errs)



        data = {
            "name": "Bob",
            "contact": 2,
            "contacts": [1,2]
        }
        ids, errs = self.db.test.insert(data, self.user, direct=True)
        self.assertIsNone(errs)

        data = json.loads(self.db.test.find_and_serialize())
        self.assertEqual(data, [
        {
            "_id": 1,
            "_auth": {
                "_edit": True,
                "_delete": True,
            },
            "name": "Bob",
            "contact": {
                "_auth": {
                    "_edit": True,
                    "_delete": True,
                },
                "_id":2,
                "username": "fred",
            },
            "contacts": [
                {
                    "_auth": {
                        "_edit": True,
                        "_delete": True,
                    },
                    "_id":1,
                    "username": "bob",
                },
                {
                    "_auth": {
                        "_edit": True,
                        "_delete": True,
                    },
                    "_id":2,
                    "username": "fred",
                }
            ]
        }])
        

        data = json.loads(self.db.test.find_one_and_serialize(1))
        self.assertEqual(data, 
        {
            "_id": 1,
            "_auth": {
                "_edit": True,
                "_delete": True,
            },
            "name": "Bob",
            "contact": {
                "_auth": {
                    "_edit": True,
                    "_delete": True,
                },
                "_id":2,
                "username": "fred",
            },
            "contacts": [
                {
                    "_auth": {
                        "_edit": True,
                        "_delete": True,
                    },
                    "_id":1,
                    "username": "bob",
                },
                {
                    "_auth": {
                        "_edit": True,
                        "_delete": True,
                    },
                    "_id":2,
                    "username": "fred",
                }
            ]
        })


    def test_deletion(self):
        self.db.register_endpoint('test', {
            'schema': {
                "name": {"type": "string"},
            }
        })


        data = [
            {"name": "Bob"},
            {"name": "Fred"},
            {"name": "George"},
        ]
        ids, errs = self.db.test.insert(data, self.user)
        self.assertIsNone(errs)
        
        self.db.test.remove({"name":"Fred"})
        data = self.db.test.find().all()
        self.assertEqual(data, [{
            "_id": 1,
            "_active": True,
            "name": "Bob",
        },{
            "_id": 3,
            "_active": True,
            "name": "George",            
        }])

        data = self.db.test.find({'_active': False}).all()
        self.assertEqual(data, [{
            "_id": 2,
            "_active": False,
            "name": "Fred",
        }])


    def test_schema_change_major(self):
        self.db.register_endpoint('users', {
            'schema': {
                "name": {"type": "string", 'required': True, 'unique': True},
            }
        })        

        ids, errs = self.db.users.insert({'name': 'James'}, self.user)
        self.assertIsNone(errs)


        self.db.register_endpoint('test', {
            'schema': {
                "name": {"type": "string"},
                "data": {"type": "integer", "required": True},
                "cap_name": {"type": "string",
                    "serialize": lambda e: e.name.upper()
                },
                "subdoc": {"type": "dict", "schema": {
                    "data": {"type":"integer"},
                    "subdoc": {"type": "dict", "schema": {
                        "data": {"type":"integer"},
                    }},
                    "doclist": {"type": "list", "schema": {"type": "dict", "schema": {
                        "name": {"type":"string"}
                    }}},            
                    "ref": {
                        'type': 'reference',
                        'collection': 'users',
                        'fields': ['name'],
                    }, 
                    "reflist": {"type": "list", "schema": {
                        'type': 'reference',
                        'collection': 'users',
                        'fields': ['name'],
                    }},            
                }},
                "list": {"type": "list"},
                "hash": {"type": "dict"},
                "num_list": {"type": "list", "schema": {"type": "integer"}},
                "doclist": {"type": "list", "schema": {"type": "dict", "schema": {
                    "data": {"type":"integer"},
                    "subdoc": {"type": "dict", "schema": {
                        "data": {"type":"integer"},
                    }},
                    "doclist": {"type": "list", "schema": {"type": "dict", "schema": {
                        "name": {"type":"string"}
                    }}},            
                    "ref": {
                        'type': 'reference',
                        'collection': 'users',
                        'fields': ['name'],
                    }, 
                    "reflist": {"type": "list", "schema": {
                        'type': 'reference',
                        'collection': 'users',
                        'fields': ['name'],
                    }},            
                }}},
                "ref": {
                    'type': 'reference',
                    'collection': 'users',
                    'fields': ['name'],
                }, 
                "reflist": {"type": "list", "schema": {
                    'type': 'reference',
                    'collection': 'users',
                    'fields': ['name'],
                }},
            }
        })

        data = {
            "name": 'fred',
            "data": 1,
            "subdoc": {
                "data": 1,
                "subdoc": {"data": 56},
                "doclist": [{"name": 'bob'}],            
                "ref": {'_id':1},
                "reflist": [{'_id':1}],    
            },
            "list": [4,'fgh'],
            "hash": {3:'bob', '4':45},
            "num_list": [5,4,3],
            "doclist": [{
                "data": 1,
                "subdoc": {"data": 56},
                "doclist": [{"name": 'bob'}],            
                "ref": {'_id':1},
                "reflist": [{'_id':1}],    
            }],
            "ref": {'_id':1},
            "reflist": [{'_id':1}],    
        }

        ids, errs = self.db.test.insert(data, self.user)
        self.assertIsNone(errs)


        self.db.register_endpoint('test', {
            'schema': {
                "name2": {"type": "string"},
                "data2": {"type": "integer", "required": True, 'default': 1},
                "cap_name2": {"type": "string",
                    "serialize": lambda e: e.name and e.name.upper()
                },
                "subdoc2": {"type": "dict", "schema": {
                    "data": {"type":"integer"},
                    "subdoc": {"type": "dict", "schema": {
                        "data": {"type":"integer"},
                    }},
                    "doclist": {"type": "list", "schema": {"type": "dict", "schema": {
                        "name": {"type":"string"}
                    }}},            
                    "ref": {
                        'type': 'reference',
                        'collection': 'users',
                        'fields': ['name'],
                    }, 
                    "reflist": {"type": "list", "schema": {
                        'type': 'reference',
                        'collection': 'users',
                        'fields': ['name'],
                    }},            
                }},
                "list2": {"type": "list"},
                "hash2": {"type": "dict"},
                "num_list2": {"type": "list", "schema": {"type": "integer"}},
                "doclist2": {"type": "list", "schema": {"type": "dict", "schema": {
                    "data": {"type":"integer"},
                    "subdoc": {"type": "dict", "schema": {
                        "data": {"type":"integer"},
                    }},
                    "doclist": {"type": "list", "schema": {"type": "dict", "schema": {
                        "name": {"type":"string"}
                    }}},            
                    "ref": {
                        'type': 'reference',
                        'collection': 'users',
                        'fields': ['name'],
                    }, 
                    "reflist": {"type": "list", "schema": {
                        'type': 'reference',
                        'collection': 'users',
                        'fields': ['name'],
                    }},            
                }}},
                "ref2": {
                    'type': 'reference',
                    'collection': 'users',
                    'fields': ['name'],
                }, 
                "reflist2": {"type": "list", "schema": {
                    'type': 'reference',
                    'collection': 'users',
                    'fields': ['name'],
                }},
            }
        })
        
        errs = self.db.test.update({'_id':1}, self.user)
        self.assertIsNone(errs)
        resp = self.db.test.find_one_and_serialize(1)
        resp = json.loads(resp)
        
        self.assertEqual(resp, {
            "_auth": {"_edit": True, "_delete": True, "doclist2": True},
            "_id": 1,
            "name2": None,
            "cap_name2": None,
            "data2": 1,
            "subdoc2": {
                "_auth": {"_edit": True, "doclist": True},
                "_id": 1,
                "data": None,
                "subdoc": {
                    "_auth": {"_edit": True},
                    "_id": 1,
                    "data": None
                },
                "doclist": [],            
                "ref": None,
                "reflist": [],    
            },
            "list2": [],
            "hash2": {"_id":1},
            "num_list2": [],
            "doclist2": [],
            "ref2": None,
            "reflist2": [],    
        })