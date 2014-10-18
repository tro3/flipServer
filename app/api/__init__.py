from flask import Blueprint
import views
import auth_layer


def create_api(app):
    api = Blueprint('api', 'api')
    setup_endpoints(app, api)
    return api


def setup_endpoints(app, api):
    for name, endp in app.config.get('ENDPOINTS', {}).items():
        app.add_url_rule('/%s/' % name, '%s_index' % name, create_index_server(app, name))
        create_endpoint(app, api, name, endp)


def create_endpoint(app, api, name, endpoint):
    app.db.register_endpoint(name, endpoint)     
    api.add_url_rule('/%s' % name, '%s_api_list' % name,
                         views.api_list_view_factory(app.db, name),
                         methods=['GET', 'POST'])    
    api.add_url_rule('/%s/<int:id>' % name, '%s_api_item' % name,
                         views.api_item_view_factory(app.db, name),
                         methods=['GET', 'PUT', 'DELETE'])


def create_index_server(app, name):
    def serve():
        return app.send_static_file('%s/index.html' % name)
    return serve
