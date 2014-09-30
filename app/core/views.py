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


# Move to schemongo
from schemongo.schema_layer.serialization import get_serial_dict




def api_list_view_factory(db, collection_name):
    
    def view_fcn():
        endpoint = db.endpoints[collection_name]
        schema = endpoint['schema'] #Temp
        
        if request.method == 'GET':
            if not resolve_auth('read', endpoint):
                return UNAUTHORIZED

            try:
                spec = json.loads(request.args.get('q', "{}"))
                fields = json.loads(request.args.get('fields', 'null'))
            except:
                return MALFORMED
            
            data = db[collection_name].find(spec, fields)

            resp = {'_status':'OK', '_items':[get_serial_dict(schema, x) for x in data], '_auth': resolve_auth('create', endpoint)}
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
                items = [get_serial_dict(schema, db[collection_name].find_one(x)) for x in ids]
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






def api_item_view_factory(app, collection_name):
    
    def view_fcn(id):
        import backend

        endpoint, schema = authenticate_endpoint(app, collection_name)
        if endpoint == 'UNAUTHORIZED':
            return UNAUTHORIZED

        if not app.mongo.db[collection_name].find({"_id": id}).count():
            return NOT_FOUND

        data = app.mongo.db[collection_name].find_one({"_id": id})
        data = DBDocument(data, endpoint)

        try:
            projection = json.loads(request.args.get('fields', 'null'))
        except:
            return MALFORMED


        if request.method == 'GET':
            if not data._auth_state.read:
                return UNAUTHORIZED
            return Response(dumps(data, app), content_type='application/json')
        

        elif request.method == 'PUT':
            try:
                incoming = json.loads(request.data)
            except:
                return MALFORMED
            
            if '_id' in incoming and incoming['_id'] != id:
                return WRONG_ID
            incoming.update({'_id':id})
            
            data.update(incoming)
            data.pre_save()

            if data.errors:
                resp = {'_status':'ERR', 'message': 'Field errors'}
                resp['field_errors'] = data.errors
                return Response(json.dumps(resp), content_type='application/json')
            else:
                backend.update(collection_name, request.user, data.dump_to_db())
                resp = {'_status':'OK'}
                data = backend.find_one(collection_name, {"_id": id})
                data = DBDocument(data, endpoint)
                resp.update(data)
                return Response(dumps(resp, app), 
                                status = 200,
                                content_type='application/json')

        elif request.method == 'DELETE':
            if not data._auth_state.delete:
                return UNAUTHORIZED
            backend.remove(collection_name, request.user, {"_id": id})
            return Response(status=204)
        
        else:
            return NOT_ALLOWED
 
    return view_fcn
