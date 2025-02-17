"""
Build command:
pyinstaller --add-data "templates;templates" --add-data "static;static" --add-data "bats;bats" flask_app.py
"""

from flask import Flask, jsonify, render_template, request, Response
import os, json
import logging as log
from src.functions import SSEEvents, AccountsController, ReposController, Executer, CloudflareController, User, Repo
from src.config import BASE_DIR

accountsController = AccountsController()
reposController = ReposController()
flareController = CloudflareController()
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates")
)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/user/<username>/project/create', methods=['POST'])
def create_project(username):
    if not request.json:
        return jsonify({'message': 'Invalid JSON data'}), 400

    data = request.json
    repoUrl = data['repo']['url']
    branch = data['repo']['branch']
    ghAccess_token = data['repo']['access_token']
    ports = data['repo']['ports']

    try:
        user = User(username)
        repo = user.newProject(repoUrl, branch=branch, ghAccess_token=ghAccess_token, ports=ports)
    except Exception as e: 
        log.error(e, exc_info=True)
        return jsonify({ 'message': str(e) }), 400
    return jsonify({ 'message': 'success', 'hash': repo.getHash() }), 200


@app.route('/api/user/<username>/project/<hash>/launch')
def repo_launch(username, hash):
    def sse_func():
        user = User(username)
        try: repo = user.loadProject(hash)
        except Exception as e:
            yield from SSEEvents.fatal(str(e))
            return log.error(e, exc_info=True)

        yield from SSEEvents.info("Downloading repository")
        try: repo.download()
        except Exception as e:
            yield from SSEEvents.fatal(str(e))
            return log.error(e, exc_info=True)
        yield from SSEEvents.info("Repository downloaded")

        yield from SSEEvents.info("Building docker image")
        try: repo.build()
        except Exception as e:
            yield from SSEEvents.fatal(str(e))
            return log.error(e, exc_info=True)
        yield from SSEEvents.info("Docker container of repository builded")

        yield from SSEEvents.info("Running docker container")
        try: repo.run()
        except Exception as e:
            yield from SSEEvents.fatal(str(e)) 
            return log.error(e, exc_info=True)
        yield from SSEEvents.info("Docker container is running locally")

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

