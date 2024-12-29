from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os, json, requests, subprocess
from functions import JsonEditor, run_command
from git import Repo, InvalidGitRepositoryError

CURRENT_DIR = os.getcwd()
REPOS_DIR = os.path.join(CURRENT_DIR, 'repos')
app = Flask(__name__)
CORS(app)

if not os.path.exists(os.path.join(CURRENT_DIR, 'repos')):
    os.makedirs(REPOS_DIR)

def get_repos_info():
    data = []
    for repo in os.listdir(os.path.join(CURRENT_DIR, 'repos')):
        repo_path = os.path.join(CURRENT_DIR, 'repos', repo)
        info_path = os.path.join(repo_path, 'info.json')

        if not os.path.isdir(repo_path) or not os.path.exists(info_path):
            continue

        with open(info_path, 'r') as file:
            repo_info = json.load(file)
            data.append(repo_info)
    return data

# print(get_repos_info())

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/new-account', methods=['GET'])
def add_account():
    jsonFilePath = os.path.join(CURRENT_DIR, 'accounts.json')
    try:
        username = request.args.get('username')
        file_data = JsonEditor.read(jsonFilePath)

        data = {
            'username': username,
            'name': request.args.get('name'),
            'access_token': request.args.get('access_token')
        }

        file_data.update({ username: data })
        JsonEditor.overwrite(jsonFilePath, file_data)
    except Exception as err:
        return jsonify({ "message": f"account creation error: {err}" }), 400
    
    return jsonify({ "message": f"account ({username}) successfully saved" }), 200


@app.route('/api/get-accounts', methods=['GET'])
def get_accounts():
    try:
        jsonFilePath = os.path.join(CURRENT_DIR, 'accounts.json')
        file_data = JsonEditor.read(jsonFilePath)
        if not file_data:
            return jsonify({ "message": "the list of accounts is empty" }), 400
        return jsonify(file_data), 200
    except Exception as err:
        return jsonify({ "message": f"account loading error: {err}" })


@app.route('/api/delete-account', methods=['GET'])
def delete_account():
    jsonFilePath = os.path.join(CURRENT_DIR, 'accounts.json')
    username = request.args.get('username')
    try:
        file_data = JsonEditor.read(jsonFilePath)
        del file_data[username]
        JsonEditor.overwrite(jsonFilePath, file_data)
        
    except Exception as err:
        return jsonify({ "message": f"account deletion error: {err}" }), 400
    
    return jsonify({ "message": f"account ({username}) deleted" }), 200


@app.route('/api/new-repo', methods=['GET'])
def new_repo():
    repoStr = request.args.get('repo')
    repo = json.loads(repoStr)
    if not repo:
        return jsonify({ "message": "bad request, url-params(repo) is incorrect" }), 400
    os.mkdir(os.path.join(CURRENT_DIR, 'repos', repo['name']))
    pathToInfo = os.path.join(CURRENT_DIR, 'repos', repo['name'], 'info.json')
    JsonEditor.overwrite(pathToInfo, repo)
    return jsonify({ "message": "new repository has been created successfully" }), 200
        

@app.route('/api/git-pull', methods=['GET'])
def git_pull():
    repo_name = request.args.get('name')

    repoDirPath = os.path.join(CURRENT_DIR, 'repos', repo_name)
    repoSrcPath = os.path.join(repoDirPath, 'src')
    infoJsonPath = os.path.join(repoDirPath, 'info.json')

    repo = JsonEditor.read(infoJsonPath)

    repo_url = repo['url']
    branch = repo['branchName']

    if not repo:
        return jsonify({"message": "pulling repository error: load info.json error"}), 400

    try:
        commitHash  = ''
        if os.path.exists(repoSrcPath):
            repo = Repo(repoSrcPath)
            print(f"Обновление репозитория {repo_url}...")
            origin = repo.remotes.origin
            origin.pull(branch)
            commitHash = repo.head.commit.hexsha
        else:
            print(f"Клонирование {repo_url}...")
            Repo.clone_from(repo_url, repoSrcPath, branch=branch)
            repo = Repo(repoSrcPath)
            commitHash = repo.head.commit.hexsha
    except Exception as err:
        return jsonify({ "message": f"pulling repository error: {err}" }), 400

    # info.json
    info_data = JsonEditor.read(infoJsonPath)
    info_data['git']['commitHash'] = commitHash
    JsonEditor.overwrite(infoJsonPath, info_data)

    return jsonify({"status": "success", "message": f"Repository updated in {repoDirPath}."}), 200


@app.route('/api/get-repos', methods=['GET'])
def get_repos():
    data = get_repos_info()
    if not data:
        return jsonify({ "message": "the list of repositories is empty" }), 200
    return jsonify(data), 200


@app.route('/api/delete-repo', methods=['GET'])
def delete_repo():
    repo_name = request.args.get('name')

    if not repo_name:
        return jsonify({ "message": "repository deletion error: invalid repository name" }), 400
    
    bat_file_path = os.path.join(CURRENT_DIR, 'bats', 'delete_repo.bat')
    folder_to_delete = os.path.join(CURRENT_DIR, 'repos', repo_name)

    if not os.path.exists(folder_to_delete):
        return jsonify({ "message": f"repository deletion error: repository with name {repo_name} not found" }), 400

    try:
        result = subprocess.run(
            [bat_file_path, folder_to_delete],
            check=True,
            text=True,
            capture_output=True,
        )
        print("delete_repo.bat: ", result.stdout)
    except subprocess.CalledProcessError as e:
        return jsonify({ "message": f"repository deletion error: code ({e.returncode}): {e.stderr}" }), 400
    
    if not os.path.exists(folder_to_delete):
        return jsonify({ "message": f"repository ({repo_name}) has been deleted" }), 200
    else: return jsonify({ "message": f"repository deletion error" }), 400


@app.route('/api/docker-build', methods=['GET'])
def docker_build():
    repoName = request.args.get('repo_name')
    infoJsonPath = os.path.join(CURRENT_DIR, 'repos', repoName, 'info.json')
    infoJson = JsonEditor.read(infoJsonPath)
    rootPath = os.path.join(CURRENT_DIR, 'repos', repoName, 'src', infoJson['docker']['rootPath'])

    if not os.path.exists(os.path.join(rootPath, 'Dockerfile')):
        return jsonify({ "message": f"Dockerfile not be found in {rootPath}" }), 400

    buildCommand = infoJson['docker']['buildCommand'] + ' ' + rootPath
    print(buildCommand)

    status, output = run_command(buildCommand)

    if not status:
        return jsonify({ "message": f"docker building error: {output}" }), 400

    infoJson['docker']['containerStatus'] = 'offline'
    infoJson['docker']['isBuilded'] = True
    JsonEditor.overwrite(infoJsonPath, infoJson)

    return jsonify({ "message": f"docker image ({repoName}) created" }), 200


@app.route('/api/docker-run', methods=['GET'])
def docker_run():
    repoName = request.args.get('repo_name')
    infoJsonPath = os.path.join(CURRENT_DIR, 'repos', repoName, 'info.json')
    infoJson = JsonEditor.read(infoJsonPath)
    imageName = infoJson['docker']['imageName']

    status, output = run_command(f'docker image inspect {imageName}')
    if not status:
        return jsonify({ "message": f"docker running error: docker image ({imageName}) not created" }), 400
    status, output = run_command(infoJson['docker']['runCommand'])
    if not status:
        return jsonify({ "message": f"image running error: command failed | code-{status} {output}" }), 400
    return jsonify({ "message": f"image ({imageName}) is running" }), 200


@app.route('/api/update-repo-info', methods=['GET'])
def update_repo_info():
    repoName = request.args.get('repo_name')
    paramsArr = request.args.get('update')
    parsed_data = json.loads(paramsArr)
    print(parsed_data)

    infoJsonPath = os.path.join(CURRENT_DIR, 'repos', repoName, 'info.json')
    infoJson = JsonEditor.read(infoJsonPath)

    def set_value_by_path(dictionary, keys, value):
        current = dictionary
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    for key, value in parsed_data.items():
        subkeys = key.split('/')
        set_value_by_path(infoJson, subkeys, value)
        

    JsonEditor.overwrite(infoJsonPath, infoJson)

    return jsonify({ "message": "ok" })


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=3000)
