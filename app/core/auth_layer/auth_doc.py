#!/usr/bin/env python

from schemongo.schema_layer.schema_doc import is_object, is_list_of_objects


def AuthState():
    return {
        '_create': True,
        '_read': True,            
        '_edit': True,
        '_delete': True,            
    }


def resolve_state(key, auth_cfg, auth_state, doc):
    result = auth_cfg.get(key[1:], auth_state[key])
    if callable(result):
        result = result(doc)
    return result


def add_authstates(endpoint, doc, auth_state=None, subdoc=False):
    schema = endpoint['schema']
    auth_cfg = endpoint.get('auth', {})
    auth_state = (auth_state and dict(auth_state)) or AuthState()

    if not resolve_state('_read', auth_cfg, auth_state, doc):
        return False
    
    _auth = {
        '_edit': resolve_state('_edit', auth_cfg, auth_state, doc)
    }
    if not subdoc:
        _auth['_delete'] = resolve_state('_delete', auth_cfg, auth_state, doc)
    
    auth_state.update(_auth)
    lists = {}

    for key, val in schema.items():
        if is_object(val):
            if not add_authstates(val, doc[key], auth_state, subdoc=True):
                del doc[key]
            
        if is_list_of_objects(val):
            lists[key] = resolve_state('_create', val.get('auth', {}), auth_state, doc)
            
            new_auth_state = dict(auth_state)
            new_auth_state['_create'] = lists[key]
            
            dels = []
            for item in doc[key]:
                if not add_authstates(val['schema'], item, new_auth_state):
                    dels.append(item)
            map(doc[key].remove, dels)
                
    _auth.update(lists)
    doc._authstate = _auth
    
    return True