from flask import jsonify, request, Response, Blueprint
from src.core import User, ProjectConfig, Project, ProjectFactory, CFManager, DockerApp, GitHubRepo, TunnelBuilder, Directory
from src.utils import SSEEvents
import logging as log

api_bp = Blueprint('api', __name__)

@api_bp.route('/user/<username>/project/create', methods=['POST'])
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


@api_bp.route('/user/<username>/project/<project_name>/launch')
def project_launch(username, project_name):
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


@api_bp.route('/user/<username>/project/<hash>/delete', methods=['DELETE'])
def delete_project(username, hash):
    try:
        user = User(username)
        projectName = user.deleteProject(hash)
    except Exception as e:
        return jsonify({ 'message': str(e) }), 400
    return jsonify({ 'message': f'Project ({projectName}) deleted' }), 200


@api_bp.route('/user/<username>/get-projects', methods=['GET'])
def get_projects(username):
    user = User(username)
    projects = user.getProjects()
    if not projects: return jsonify({ 'message': 'You have not any projects yet' }), 200
    return jsonify({ 'projects': projects }), 200