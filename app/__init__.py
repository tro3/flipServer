import os.path as path
import json
from PIL import Image
from StringIO import StringIO
from flask import Flask, render_template, request, abort, Response, Blueprint, redirect
from core import auth_layer, views

class AngularFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        variable_start_string='%%',
        variable_end_string='%%',
    ))


app = None


def create_app(**config):
    global app
    app = AngularFlask(__name__, static_folder='static', static_url_path='')
    try:
        import endpoints
        app.config['ENDPOINTS'] = endpoints.ENDPOINTS
    except:
        pass
    app.config.update(config)
    app.db = auth_layer.init(config.get('CLIENT', None))
    

    @app.before_request
    def add_user():
        if not app.config.get('REQUIRE_USER', False):
            return
        if 'REMOTE_USER' in request.environ:
            username = request.environ['REMOTE_USER'].split('\\')[1]
        elif 'TEST_USER' in app.config:
            username = request.environ['TEST_USER']
        else:
            abort(403)
        request.user = app.db.users.find_one({'username':username})
        if request.user is None:
            abort(403)


    #@app.errorhandler(404)
    #def not_found(error):
    #    return render_template('404.html'), 404

    
    @app.route('/')
    def homepage():
        return redirect('/home/')
    app.add_url_rule('/home/', 'home_index', create_index_server('home'))
    
    
    app.api = Blueprint('api', 'api', url_prefix='/api')

    for name, endp in app.config.get('ENDPOINTS', {}).items():
        app.add_url_rule('/%s/' % name, '%s_index' % name, create_index_server(name))
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


def create_index_server(name):
    global app

    def serve():
        return app.send_static_file('%s/index.html' % name)
    return serve
