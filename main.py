from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os, json, requests, subprocess
from git import Repo, InvalidGitRepositoryError

repos_dir = './repos'
current_dir = os.getcwd()
app = Flask(__name__)
CORS(app)


def get_repos_info():
    data = []
    for repo in os.listdir(os.path.join(current_dir, 'repos')):
        repo_path = os.path.join(current_dir, 'repos', repo)
        info_path = os.path.join(repo_path, 'info.json')

        if not os.path.isdir(repo_path) or not os.path.exists(info_path):
            continue

        with open(info_path, 'r') as file:
            repo_info = json.load(file)
            data.append(repo_info)


get_repos_info()

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/git-pull', methods=['GET'])
def pull_repo():
    repo_url = request.args.get('url')
    branch = request.args.get('branch')
    repo_name = request.args.get('name')

    if not repo_url or not branch or not repo_name:
        return jsonify({"message": "invalid query params"}), 400

    repo_dir = os.path.join('./repos', repo_name)

    try:
        if not os.path.exists(repo_dir):
            os.makedirs('./repos', exist_ok=True)
            print(f"Клонирование репозитория {repo_url}...")
            Repo.clone_from(repo_url, repo_dir, branch=branch)
        else:
            print(f"Обновление репозитория {repo_url}...")
            repo = Repo(repo_dir)
            origin = repo.remotes.origin
            origin.pull(branch)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

    # info.json
    info = {
        "name": repo_name,
        "url": repo_url,
        "branch": branch
    }

    try:
        json_object = json.dumps(info, indent=4)
    
        with open(os.path.join(current_dir, 'repos', repo_name, 'info.json'), "w") as outfile:
            outfile.write(json_object)

        return jsonify({"status": "success", "message": f"Repository updated in {repo_dir}."}), 200
    except Exception as e:
        print(e)


@app.route('/api/delete-repo')
def delete_repo():
    repo_name = request.args.get('name')

    if not repo_name:
        return jsonify({ "message": "invalid repo name" }), 400
    
    bat_file_path = os.path.join(current_dir, 'bats', 'delete_repo.bat')
    folder_to_delete = os.path.join(current_dir, 'repos', repo_name)

    if not os.path.exists(folder_to_delete):
        return jsonify({ "message": f"repo with name {repo_name} not found" }), 400

    try:
        result = subprocess.run(
            [bat_file_path, folder_to_delete],
            check=True,
            text=True,
            capture_output=True,
        )
        print("delete_repo.bat: ", result.stdout)
    except subprocess.CalledProcessError as e:
        return jsonify({ "message": f"code ({e.returncode}): {e.stderr}" }), 400
    
    if not os.path.exists(folder_to_delete):
        return jsonify({ "message": f"folder {repos_dir} has been deleted" }), 200
    else: return jsonify({ "message": f"folder delete error" }), 400


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=3000)
