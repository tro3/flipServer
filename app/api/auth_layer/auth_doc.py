#!/usr/bin/env python

from schemongo.schema_layer.schema_doc import is_object, is_list_of_objects, DBDoc, generate_prototype


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
        try:
            result = result(doc)
        except TypeError:             # auth.read() can have zero or one args - either
            result = result()         # case applies here
    return result


def add_authstates(endpoint, doc, auth_state=None, subdoc=False):
    schema = endpoint['schema']
    auth_cfg = endpoint.get('auth', {})
    auth_state = (auth_state and dict(auth_state)) or AuthState()

    auth_state['_read'] = resolve_state('_read', auth_cfg, auth_state, doc)
    auth_state['_edit'] = resolve_state('_edit', auth_cfg, auth_state, doc)
    auth_state['_delete'] = resolve_state('_delete', auth_cfg, auth_state, doc)    
    lists = {}

    for key, val in schema.items():
        if is_object(val) and key in doc:
            add_authstates(val, doc[key], auth_state, subdoc=True)
            
        if is_list_of_objects(val):
            lists[key] = resolve_state('_create', val['schema'].get('auth', {}), auth_state, doc)
            
            new_auth_state = dict(auth_state)
            new_auth_state['_create'] = lists[key]
            
            if key in doc:
                for item in doc[key]:
                    add_authstates(val['schema'], item, new_auth_state)
                
    auth_state.update(lists)
    doc._authstate = auth_state
    


def get_by_id(list, id):
    for item in list:
        if item['_id'] == id:
            return item
    

def enforce_auth_read(endpoint, doc, data=None):
    schema = endpoint['schema']
    data = data or doc._projection
    for key, val in data.items():
        if key in schema and is_object(schema[key]):
            if not doc[key]._authstate['_read']:
                data.pop(key)
            else:
                enforce_auth_read(schema[key], doc[key], val)
        if key in schema and is_list_of_objects(schema[key]):
            for item in val[:]:
                if not get_by_id(doc[key], item['_id'])._authstate['_read']:
                    val.remove(item)
                else:
                    enforce_auth_read(schema[key]['schema'], get_by_id(doc[key], item['_id']), item)



def enforce_auth(endpoint, doc, incoming):
    schema = endpoint['schema']

    for key, val in schema.items():        
        if key in incoming:
            
            if is_object(val):

                if not doc[key]._authstate['_edit'] and key in incoming:
                    remove_data(val['schema'], incoming[key])
                enforce_auth(val, doc[key], incoming[key])
            
            elif is_list_of_objects(val):

                # Check for added items
                if not doc._authstate[key]:
                    incoming[key] = filter(lambda x: x.get('_id', False), incoming[key])
                    
                # Check for edited or deleted items
                ids = [x.get('_id',0) for x in incoming[key]]
                for i,item in enumerate(doc[key]):
                    if item._id in ids and not item._authstate['_edit']:
                        remove_data(val['schema']['schema'], incoming[key][ids.index(item._id)])
                    
                    if item._id not in ids and not item._authstate['_delete']:
                        incoming[key].insert(i, {'_id':item._id})
                        
                # Enforce on remaining items
                ids = [x._id for x in doc[key]]
                for item in incoming[key]:
                    if not item.get('_id',0):
                        sdoc = generate_prototype(val['schema']['schema'])
                        new_state = dict(doc._authstate)
                        new_state['_create'] = True
                        add_authstates(val['schema'], sdoc, new_state)
                    else:
                        sdoc = doc[key][ids.index(item['_id'])]
                    enforce_auth(val['schema'], sdoc, item)
                
                
def remove_data(schema, incoming):
    for key in incoming.keys():
        if key != '_id':
            if key in schema and is_object(schema[key]) or is_list_of_objects(schema[key]):
                pass
            else:
                incoming.pop(key)
        

