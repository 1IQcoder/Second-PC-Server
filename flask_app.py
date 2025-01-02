from flask import Flask, jsonify, render_template, request
import json
import logging as log
from functions import JsonEditor, AccountsController, ReposController, GitController, DockerController

accountsController = AccountsController()
reposController = ReposController()
gitController = GitController()
dockerController = DockerController()
app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/get-accounts', methods=['GET'])
def get_accounts():
    isEmpty, accs = accountsController.getAccounts()
    if isEmpty:
        return jsonify({ "message": "the list of accounts is empty" }), 400
    return jsonify(accs), 200


@app.route('/api/new-account', methods=['GET'])
def new_account():
    try:
        accObjStr = request.args.get('account')
        accObj = json.loads(accObjStr)
    except Exception as e:
        log.error(f"Route ('/api/new-account') error, account=({accObjStr}): {e}", exc_info=True)
        return jsonify(f"Route ('/api/new-account') error, account=({accObjStr}): {str(e)}"), 400
    accountsController.addAccount(accObj)
    return jsonify({ "message": f"New account added. account=({accObjStr})" }), 200


@app.route('/api/delete-account', methods=['GET'])
def delete_account():
    try:
        username = request.args.get('username')
        accountsController.deleteAccount(username)
        return jsonify({ "message": f"account ({username}) deleted" }), 200
    except Exception as e:
        log.exception(f"Route ('/api/delete-account') error, account=({username}): {e}")
        return jsonify({ "message": f"account deletion error: {str(e)}" }), 400


@app.route('/api/get-repos', methods=['GET'])
def get_repos():
    isEmpty, reposList = reposController.getRepos()
    if isEmpty:
        return jsonify({ "message": "the list of repositories is empty" }), 200
    return jsonify(reposList), 200


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
        log.exception(f"Route ('/api/new-repo') error, repo=({repoStr}): {e}")
        return jsonify({ "message": f"Creating repository error: {str(e)}" }), 400


@app.route('/api/delete-repo', methods=['GET'])
def delete_repo():
    repoName = request.args.get('name')
    err = reposController.deleteRepo(repoName)
    if err:
        return jsonify({ "message": f"Repository deletion error: {err}" }), 400
    return jsonify({ "message": f"repository ({repoName}) has been deleted" }), 200


@app.route('/api/update-repo-info', methods=['GET'])
def update_repo():
    repoName = request.args.get('repo_name')
    paramsArrStr = request.args.get('update')
    paramsArr = json.loads(paramsArrStr)

    err = reposController.updateRepo(repoName, paramsArr)
    if err:
        return jsonify({ "message": f"Editing {repoName}/info.json error: {err}" })
    return jsonify({ "message": f"Updated values in {repoName}/info.json" })


@app.route('/api/git-pull', methods=['GET'])
def git_pull():
    repoName = request.args.get('name')
    err = gitController.pullRepo(repoName)
    if err:
        return jsonify({ "message": f"Pulling repository error, repoName=({repoName}): {err}" }), 400
    return jsonify({ "message": f"Repository updated ({repoName})"}), 200


@app.route('/api/docker-build', methods=['GET'])
def docker_build():
    repoName = request.args.get('repo_name')
    err = dockerController.dockerBuild(repoName)
    if err:
        return jsonify({ "message": f"Docker building error, repoName=({repoName}): {err}" }), 400
    return jsonify({ "message": f"docker image ({repoName}) created" }), 200


@app.route('/api/docker-run', methods=['GET'])
def docker_run():
    repoName = request.args.get('repo_name')
    err = dockerController.dockerRun(repoName)
    if err:
        return jsonify({ "message": f"Runing image error, repoName=({repoName}): {err}" }), 400
    return jsonify({ "message": f"Image is running, repoName=({repoName})" }), 200


@app.route('/api/full-launch', methods=['GET'])
def full_launch():
    repoName = request.args.get('repo_name')
    
    isExsists, infoFile = reposController.getRepo(repoName)
    if not isExsists:
        return "Repository not found"
    
    # git pull
    if not infoFile['git']['isPulled']:
        err = gitController.pullRepo(repoName)
        if err: return err
        reposController.updateRepo(repoName, { "git/isPulled": True })
    
    # docker build
    if not infoFile['docker']['isBuilded']:
        err = dockerController.dockerBuild(repoName)
        if err: return err
        reposController.updateRepo(repoName, { "docker/isBuilded": True })

    # docker run
    if not infoFile['docker']['isRunning']:
        err = dockerController.dockerRun(repoName)
        if err: return err
        reposController.updateRepo(repoName, { "docker/isRunning": True })

    return jsonify({ "message": "ok" }), 200


def run_flask():
    app.run(debug=True, host='0.0.0.0', port=3000, use_reloader=False)

run_flask()