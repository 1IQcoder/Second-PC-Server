"""
Build command:
pyinstaller --add-data "templates;templates" --add-data "static;static" --add-data "bats;bats" flask_app.py
"""

from flask import Flask, jsonify, render_template, request, Response
from src.logger_config import setup_logger
import json, os, logging
from src.functions import SSEEvents, AccountsController, ReposController, GitController, DockerController, Executer
from src.config import BASE_DIR

accountsController = AccountsController()
reposController = ReposController()
gitController = GitController()
dockerController = DockerController()
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates")
)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/get-accounts', methods=['GET'])
def get_accounts():
    isEmpty, accs = accountsController.getAccounts()
    if isEmpty:
        return jsonify({ "msg": "the list of accounts is empty" }), 200
    return jsonify(accs), 200


@app.route('/api/new-account', methods=['GET'])
def new_account():
    try:
        accObjStr = request.args.get('account')
        accObj = json.loads(accObjStr)
    except Exception as e:
        logging.error(f"Route ('/api/new-account') error, account=({accObjStr}): {e}", exc_info=True)
        return jsonify(f"Route ('/api/new-account') error, account=({accObjStr}): {str(e)}"), 400
    accountsController.addAccount(accObj)
    return jsonify({ "msg": f"Account ({accObj['username']}) added" }), 200


@app.route('/api/delete-account', methods=['GET'])
def delete_account():
    try:
        username = request.args.get('username')
        accountsController.deleteAccount(username)
        return jsonify({ "msg": f"Account ({username}) deleted" }), 200
    except Exception as e:
        logging.exception(f"Route ('/api/delete-account') error, account=({username}): {e}")
        return jsonify({ "msg": f"Account deletion error: {str(e)}" }), 400


@app.route('/api/get-account', methods=['GET'])
def get_account():
    username = request.args.get('username', '1')
    account = accountsController.getAccount(username)
    if not account: return jsonify({ 'message': 'account not found' }), 400
    return jsonify(account), 200


@app.route('/api/get-repos', methods=['GET'])
def get_repos():
    def sse():
        repos = os.listdir(reposController.REPOS_DIR)
        print(repos)
        if not repos: yield from SSEEvents.close('Repos list empty')
        for repoName in repos:
            repoObj = reposController.getRepo(repoName)
            yield from SSEEvents.sendJson(repoObj)
        yield from SSEEvents.close('All repos loaded')

    return Response(sse(), content_type='text/event-stream')


@app.route('/api/new-repo', methods=['GET'])
def add_repo():
    try:
        repoStr = request.args.get('repo')
        repo = json.loads(repoStr)
        if not repo:
            return jsonify({ "message": "bad request, url-params(repo) is incorrect" }), 400
        reposController.addRepo(repo)
        return jsonify({ "message": "new repository has been created successfully" }), 200
    except Exception as e:
        logging.exception(f"Route ('/api/new-repo') error, repo=({repoStr}): {e}")
        return jsonify({ "message": f"Creating repository error: {str(e)}" }), 400


@app.route('/api/get-repo', methods=['GET'])
def get_repo():
    repoName = request.args.get('repo_name')
    repo = reposController.getRepo(repoName)
    if not repo: return jsonify({ 'msg': 'Repo not found' }), 400
    return jsonify(repo), 200


@app.route('/api/delete-repo', methods=['GET'])
def delete_repo():
    repoName = request.args.get('name')
    err = reposController.deleteRepo(repoName)
    if err: return jsonify({ "msg": f"Repository ({repoName}) deletion error: {err}" }), 400
    return jsonify({ "msg": f"Repository ({repoName}) has been deleted" }), 200


@app.route('/api/update-repo.log.info', methods=['GET'])
def update_repo():
    repoName = request.args.get('repo_name')
    paramsArrStr = request.args.get('update')
    paramsArr = json.loads(paramsArrStr)

    err = reposController.updateRepo(repoName, paramsArr)
    if err:
        return jsonify({ "message": f"Editing {repoName}.log.info.json error: {err}" })
    return jsonify({ "message": f"Updated values in {repoName}.log.info.json" })


@app.route('/api/full-launch', methods=['GET'])
def full_launch():
    repoName = request.args.get('repo_name')

    def launch():
        infoFile = reposController.getRepo(repoName)
        if not infoFile:
            yield from SSEEvents.log.error('Repository not found', True)
        
        # git pull
        if not infoFile['git']['isPulled']:
            yield from SSEEvents.log.info('Repo not downloaded. Downloading...')
            err = gitController.pullRepo(repoName)
            if err: yield from SSEEvents.log.error(f'Pulling repo error: {err}', True)
            reposController.updateRepo(repoName, { "git/isPulled": True })
            yield from SSEEvents.log.info('Repo has been downloaded')
        else:
            yield from SSEEvents.log.info('Repo already downloaded. Skip...')
        
        # docker build
        if not infoFile['docker']['isBuilded']:
            yield from SSEEvents.log.info('Docker image not built. Building...')
            err = dockerController.dockerBuild(repoName)
            if err: yield from SSEEvents.log.error(f'Building error: {err}', True)
            reposController.updateRepo(repoName, { "docker/isBuilded": True })
            yield from SSEEvents.log.info('Docker image has been built.')
        else:
            yield from SSEEvents.log.info('Docker image already built. Skip...')

        # docker run
        if not infoFile['docker']['isRunning']:
            yield from SSEEvents.log.info('Docker image is not running. Launching container...')
            err = dockerController.dockerRun(repoName)
            if err: yield from SSEEvents.log.error(f'Running error: {err}', True)
            reposController.updateRepo(repoName, { "docker/isRunning": True })
            yield from SSEEvents.log.info('Docker container has been launched.')
        else:
            yield from SSEEvents.log.info('Docker container already running. Skip...')
        yield from SSEEvents.log.info('Launch process completed successfully.')
        yield from SSEEvents.close()

    return Response(launch(), content_type='text/event-stream')


@app.route('/api/update-repos-state')
def update_repos_state():
    isEmpty, reposList = reposController.getRepos()
    if isEmpty: return jsonify({ 'message': 'repos list empty' }), 200
    updatedData = {}

    for key in reposList.keys():
        print(key)
        name = reposList[key]['name']
        imageName = reposList[key]['docker']['imageName']
        repoObj = {}

        repoObj['name'] = name
        repoObj['imageName'] = imageName

        success, err = Executer.run_batch('check_image.bat', imageName)
        if success:
            reposController.updateRepo(name, { 'docker/isBuilded': True })
            repoObj['isBuilded'] = True
        else:
            reposController.updateRepo(name, { 'docker/isBuilded': False })
            repoObj['isBuilded'] = False

        success, err = Executer.run_batch('check_container.bat', imageName)
        if success:
            reposController.updateRepo(name, { 'docker/isRunning': True })
            repoObj['isRunning'] = True
            repoObj['ports']['locall'] = reposList[key]['docker']['ports']['locall']
            repoObj['ports']['container'] = reposList[key]['docker']['ports']['container']
        else:
            reposController.updateRepo(name, { 'docker/isRunning': False })
            repoObj['isRunning'] = False

        updatedData[name] = repoObj
    return jsonify(updatedData), 200



def run_flask():
    app.run(debug=True, host='0.0.0.0', port=1488)

