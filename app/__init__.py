import os.path as path
import json
from PIL import Image
from StringIO import StringIO
from flask import Flask, render_template, request, abort, Response, Blueprint
from core import auth_layer, views

class AngularFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        variable_start_string='%%',
        variable_end_string='%%',
    ))


app = None

def get_app():
    return app

def create_app(**config):
    global app
    app = AngularFlask(__name__)
    app.config.update(config)
    app.db = auth_layer.init(config.get('CLIENT', None))
    

    @app.before_request
    def add_user():
        pass
        #if 'REMOTE_USER' not in request.environ:
        #    if app.config['MONGO_DBNAME'] == 'e2e_test' or app.config['DEBUG']:
        #        if path.exists('test_user.txt'):
        #            request.user = app.mongo.db.users.find_one({'username':open('test_user.txt').read().strip()})
        #        else:
        #            request.user = app.mongo.db.users.find_one({'_id':1})
        #        return
        #    else:
        #        abort(403)
        #username = request.environ['REMOTE_USER'].split('\\')[1]
        #request.user = app.mongo.db.users.find_one({'username':username})
        #if request.user is None:
        #    abort(403)

    
    #@app.errorhandler(404)
    #def not_found(error):
    #    return render_template('404.html'), 404
    #
    #@app.route('/')
    #def homepage():
    #    return render_template('index.html')
        
    
    #IMG_UPLOAD_DIR = 'app/static/uploads/images/'
    #
    #@app.route('/image_upload', methods=['POST'])
    #def upload_image():
    #    if 'file' in request.files:
    #        try:
    #            img = Image.open(request.files['file'])
    #            png = StringIO()
    #            img.save(png, 'png')
    #            #thmb = StringIO()
    #            #img.thumbnail((64,64), Image.ANTIALIAS)
    #            #img.save(thmb, 'png')
    #        except:
    #            return Response('Could not convert file to PNG format', status=500)
    #    else:
    #        png = None
    #        
    #    if not png:
    #        return Response('No file attached', status=500)
    #        
    #    ind = int(open(path.join(IMG_UPLOAD_DIR, 'ind.txt')).read())
    #    fname = 'img%i.png' % (ind)
    #    open(path.join(IMG_UPLOAD_DIR, fname), 'wb').write(png.getvalue())
    #    open(path.join(IMG_UPLOAD_DIR, 'ind.txt'), 'w').write(str(ind+1))
    #    #rev = NoteImage(session=kwords['session'])
    #    #rev.image.save(fname,
    #    #               ContentFile(png.getvalue()),
    #    #               save=False)
    #    #rev.thumb.save(fname,
    #    #               ContentFile(thmb.getvalue()),
    #    #               save=False)
    #    #rev.save()
    #    return Response(
    #        json.dumps({
    #            'name': IMG_UPLOAD_DIR[3:] + fname,
    #            #'type':'f',
    #            #'size': rev.image.size
    #            }),
    #        content_type = 'application/json'
    #        )        
        
    #collections = autodiscover(app)
    #autoregister(app, collections)

    app.api = Blueprint('api', 'api', url_prefix='/api')

    for name, endp in config.get('ENDPOINTS', {}).items():
        create_endpoint(name, endp)
    
    app.register_blueprint(app.api)
    
    return app


def create_endpoint(name, endpoint):
    global app

    app.db.register_endpoint(name, endpoint)     
    app.api.add_url_rule('/%s' % name, '%s_api_list' % name,
                         views.api_list_view_factory(app.db, name),
                         methods=['GET', 'POST'])    
    app.api.add_url_rule('/%s/<int:id>' % name, '%s_api_item' % name,
                         views.api_item_view_factory(app.db, name),
                         methods=['GET', 'PUT', 'DELETE'])
