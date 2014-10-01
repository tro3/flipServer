from flask import abort, request, Response, json
from jinja2.exceptions import TemplateNotFound



UNAUTHORIZED = Response(
    json.dumps({'_status':'ERR', 'message': 'Unauthorized'}),
    status = 403,
    content_type = 'application/json'
)

MALFORMED = Response(
    json.dumps({'_status':'ERR', 'message': 'Malformed data'}),
    status = 400,
    content_type = 'application/json'
)

WRONG_ID = Response(
    json.dumps({'_status':'ERR', 'message': 'Incorrect ID'}),
    status = 400,
    content_type = 'application/json'
)

EXISTING = Response(
    json.dumps({'_status':'ERR', 'message': 'Cannot POST with _id'}),
    status = 400,
    content_type = 'application/json'
)

NOT_FOUND = Response(
    json.dumps({'_status':'ERR', 'message': 'Item not found'}),
    status = 404,
    content_type = 'application/json'
)

NOT_ALLOWED = Response(
    json.dumps({'_status':'ERR', 'message': 'Not allowed'}),
    status = 405,
    content_type = 'application/json'
)



def resolve_auth(key, endpoint):
    auth = endpoint.get('auth', {})
    auth = auth.get(key, True)
    if callable(auth):
        auth = auth()
    return auth



def api_list_view_factory(db, collection_name):
    
    def view_fcn():
        endpoint = db.endpoints[collection_name]
        
        if request.method == 'GET':
            if not resolve_auth('read', endpoint):
                return UNAUTHORIZED

            try:
                spec = json.loads(request.args.get('q', "{}"))
                fields = json.loads(request.args.get('fields', 'null'))
            except:
                return MALFORMED
            
            data = db[collection_name].find_and_serial_dict(spec, fields)

            resp = {'_status':'OK', '_items':data, '_auth': resolve_auth('create', endpoint)}
            return Response(json.dumps(resp), content_type='application/json')


        elif request.method == 'POST':
            try:
                incoming = json.loads(request.data)
            except:
                return MALFORMED

            if '_id' in incoming:
                return EXISTING        

            if not resolve_auth('create', endpoint):
                return UNAUTHORIZED

            ids, errs = db[collection_name].insert(incoming)
            
            if errs:
                resp = {'_status':'ERR', 'message': 'Field errors'}
                resp['field_errors'] = errs
                return Response(json.dumps(resp), content_type='application/json')
            else:

                resp = {'_status':'OK'}
                items = [db[collection_name].find_one_and_serial_dict(x) for x in ids]
                if len(items) == 1:
                    resp['_item'] = items[0]
                else:
                    resp['_items'] = items
                return Response(json.dumps(resp), 
                                status = 201,
                                content_type='application/json')
                
        else:
            return NOT_ALLOWED

    return view_fcn



def api_item_view_factory(db, collection_name):
    
    def view_fcn(id):
        endpoint = db.endpoints[collection_name]

        if not db[collection_name].find({"_id": id}).count():
            return NOT_FOUND

        if request.method == 'GET':            
            try:
                fields = json.loads(request.args.get('fields', 'null'))
            except:
                return MALFORMED

            data = db[collection_name].find_one({'_id':id}, fields)
            
            if not data._authstate['_read']:
                return UNAUTHORIZED
            
            resp = {'_status':'OK', '_item':db[collection_name].get_serial_dict(data)}
            return Response(json.dumps(resp), content_type='application/json')


        elif request.method == 'PUT':
            try:
                incoming = json.loads(request.data)
            except:
                return MALFORMED
            
            if '_id' in incoming and incoming['_id'] != id:
                return WRONG_ID
            incoming.update({'_id':id})
            
            errs = db[collection_name].update(incoming)

            if errs:
                resp = {'_status':'ERR', 'message': 'Field errors'}
                resp['field_errors'] = errs
                return Response(json.dumps(resp), content_type='application/json')
            else:
                resp = {'_status':'OK',
                        '_item': db[collection_name].find_one_and_serial_dict(id)
                       }
                return Response(json.dumps(resp), 
                                status = 200,
                                content_type='application/json')

        elif request.method == 'DELETE':
            data = db[collection_name].find_one({'_id':id})
            if not data._authstate['_delete']:
                return UNAUTHORIZED
            
            db[collection_name].remove({"_id": id})
            return Response(status=204)
        
        else:
            return NOT_ALLOWED
 
    return view_fcn
