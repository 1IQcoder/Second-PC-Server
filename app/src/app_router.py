from flask import jsonify, render_template, request, Blueprint
import requests
import logging as log
from src.core import GitHubRepo, TunnelBuilder, CloudflareController, DockerApp

cf_bp = Blueprint('cf', __name__)
dk_bp = Blueprint('dk', __name__)

# Docker routes
@dk_bp.route('/')
def dk():
    return render_template('dk.html')

@dk_bp.route('/dk/launch', methods=['POST'])
def docker_launch():
    data: dict = request.json

    try:
        repo = GitHubRepo(
            url = data['url'],
            access_token = data['token'],
            branch = data.get('branch', 'default')
        )

        app = DockerApp(
            name = data['name'],
            port = data['port'],
            repo = repo
        )

        pc_port = app.launch()
    except Exception as e:
        return jsonify({ 'message': str(e) }), 400
    return jsonify({ 'message': f'app running on: http://localhost:{pc_port}' })


# Cloudflare routes
@cf_bp.route('/')
def cf():
    return render_template('cf.html')

@cf_bp.route('/config')
def config_page():
    return render_template('config.html')

@cf_bp.route('/load-zones', methods=['GET'])
def load_zones():
    try:
        token = request.args.get('api_token')
        headers = {
                'Content-type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        res = requests.get('https://api.cloudflare.com/client/v4/zones', headers=headers)
        res.raise_for_status()
        res_data = res.json()

        if not res_data['success']: return jsonify({'message': res_data['errors']}), 400
        zones = res_data['result']
        return jsonify({ 'zones': zones}), 200
    except Exception as e:
        return jsonify({ 'message': str(e) }), 400

@cf_bp.route('/set-config', methods=['POST'])
def set_config():
    data: dict = request.json

    params = {
        'api_token': data['api_token'],
        'zone_name': data['zone_name']
    }
    tunnel_name = data.get('tunnel_name', False)
    if tunnel_name:
        params['tunnel_name'] = tunnel_name

    try: res = CloudflareController.set_config(**params)
    except Exception as e:
        log.error(e, exc_info=True)
        return jsonify({ 'message': str(e) }), 400
    return jsonify(res), 200

@cf_bp.route('/route', methods=['POST'])
def cf_route():
    data: dict = request.json
    try:
        app_name = data['name']
        app = DockerApp.load(app_name)
        tunnelBuilder = TunnelBuilder(app)
        adress = tunnelBuilder.tunneling()
        return jsonify({ 'adress': adress }), 200
    except Exception as e:
        return jsonify({ 'message': str(e) }), 400




