import os
from unittest import TestCase
import datetime

import mongomock
from app.core import auth_layer
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