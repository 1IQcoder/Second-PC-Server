from flask import Flask, jsonify, render_template, request, Response
import os
import logging as log
from src.core import User, ProjectConfig, Project, ProjectFactory, CFManager
from src.utils import SSEEvents
from src.config import BASE_DIR


app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates")
)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/cf-log-in', methods=['POST'])
def set_accout():
    data = request.json
    print(data)
    try: res = CFManager.add_account(data['api_token'])
    except Exception as e:
        log.error(e, exc_info=True)
        return jsonify({ 'message': str(e) }), 400
    return jsonify(res), 200


@app.route('/cf-create-tunnel', methods=['POST'])
def set_zone():
    data = request.json
    print(data['zone'])
    try: CFManager.create_tunnel()
    except Exception as e:
        log.error(e, exc_info=True)
        return jsonify({ 'message': str(e) }), 400
    CFManager.set_zone(data['zone'])
    return jsonify({ 'message': 'Cloudflare tunnel created!' }), 200


@app.route('/api/user/<username>/project/create', methods=['POST'])
def create_project(username):
    if not request.json:
        return jsonify({'message': 'Invalid JSON data'}), 400

    data = request.json
    config = ProjectConfig(
        web_url = data['repo']['url'],
        ghAccess_token = data['repo']['access_token'],
        branch = data['repo']['branch'],
        appName = data['repo']['appName'],
        appPort = data['repo']['appPort']
    )

    try:
        user = User(username)
        project = user.newProject(config)
    except Exception as e:
        log.error(e, exc_info=True)
        return jsonify({ 'message': str(e) }), 400
    return jsonify({ 'message': 'success', 'hash': project.name }), 200


@app.route('/api/user/<username>/project/<project_name>/launch')
def repo_launch(username, project_name):
    def sse_func():
        user = User(username)
        try: project = user.loadProject(project_name)
        except Exception as e:
            yield from SSEEvents.fatal(str(e))
            return log.error(e, exc_info=True)

        yield from SSEEvents.info("Downloading repository")
        try: project.download()
        except Exception as e:
            yield from SSEEvents.fatal(str(e))
            return log.error(e, exc_info=True)
        yield from SSEEvents.info("Repository downloaded")

        yield from SSEEvents.info("Building docker image")
        try: project.build()
        except Exception as e:
            yield from SSEEvents.fatal(str(e))
            return log.error(e, exc_info=True)
        yield from SSEEvents.info("Docker container of repository builded")

        yield from SSEEvents.info("Running docker container")
        try: project.run()
        except Exception as e:
            yield from SSEEvents.fatal(str(e)) 
            return log.error(e, exc_info=True)
        yield from SSEEvents.info("Docker container is running locally")

        yield from SSEEvents.info("Tunneling")
        try: project.tunnel()
        except Exception as e:
            yield from SSEEvents.fatal(str(e))
            return log.error(e, exc_info=True)
        yield from SSEEvents.info("Tunneling is done")

        yield from SSEEvents.close()
        return

    return Response(sse_func(), content_type='text/event-stream')


@app.route('/api/user/<username>/project/<hash>/delete', methods=['DELETE'])
def delete_project(username, hash):
    try:
        user = User(username)
        projectName = user.deleteProject(hash)
    except Exception as e:
        return jsonify({ 'message': str(e) }), 400
    return jsonify({ 'message': f'Project ({projectName}) deleted' }), 200


@app.route('/api/user/<username>/get-projects', methods=['GET'])
def get_projects(username):
    user = User(username)
    projects = user.getProjects()
    if not projects: return jsonify({ 'message': 'You have not any projects yet' }), 200
    return jsonify({ 'projects': projects }), 200


def run_flask():
    app.run(debug=True, host='0.0.0.0', port=1488)

