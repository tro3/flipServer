import os.path as path
import json
from PIL import Image
from StringIO import StringIO
from flask import Flask, render_template, request, abort, Response, Blueprint, redirect
import api


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
    
    
    app.db = api.auth_layer.init(config.get('CLIENT', None))

    bp = api.create_api(app)
    app.register_blueprint(bp)

    
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
    def index():
        return redirect('/home/')
    app.add_url_rule('/home/', 'home_index', api.create_index_server(app, 'home'))
    
    
    return app

