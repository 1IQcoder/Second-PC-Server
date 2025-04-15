import json, os, requests, shutil, random
import logging as log
from .utils import ApiResponseError, ExecuterError, Executer, JsonEditor, AppDir
from typing import TypedDict
from typing import Self, Type


class GitHubRepo:
    page_url: str
    branch: str

    url: str                # api url
    private: bool
    default_branch: str
    owner: str              # 1IQcoder
    name: str               # Second-PC-Server
    full_name: str          # 1IQcoder/Second-PC-Server
    commit: str             # sha of downloaded commit
    api_headers: dict       # Authorization headers for GitHub API
    
    def _getRepoData(self, url: str) -> dict:
        req_url = url.replace("https://github.com/", "https://api.github.com/repos/").removesuffix(".git")
        log.info(f'Checking repository URL: {req_url}')
        res = requests.get(req_url, headers=self.api_headers)
        res_data = res.json()
        if res.status_code != 200:
            if res.status_code == 404:
                raise ValueError("Repository not found")
            if res.status_code == 401:
                raise ValueError("Bad credentials, GitHub access_token is bad")
            raise ApiResponseError(res_data['message'], req_url, status_code=res.status_code)
        log.info('Repository URL is valid.')
        return res_data

    def _setRepoData(self, res_data: dict):
        self.url = res_data['url']
        self.private = res_data['private']
        self.default_branch = res_data['default_branch']
        self.owner = res_data['owner']['login']
        self.name = res_data['name']
        self.full_name = res_data['full_name']

    def _getRepoBranch(self, branch) -> str:
        if branch == 'default':
            self.branch = self.default_branch
            del self.default_branch
            return True
        req_url = f'{self.url}/branches/{branch}'
        res = requests.get(req_url, headers=self.api_headers)
        if res.status_code != 200:
            if res.status_code == 404:
                raise ValueError("Repository dont exists branch with name "+branch)
            raise ApiResponseError(res)
        return branch

    def _isDkfileExists(self):
        req_url = f'{self.url}/git/trees/{self.branch}?recursive=1'
        log.info(f'Checking Dockerfile existence in repository: {req_url}')
        res = requests.get(req_url, headers=self.api_headers)
        if res.status_code != 200:
            log.error(f'Failed to fetch repository tree: {res.status_code}')
            raise ApiResponseError(res)
        fileTree = res.json()['tree']
        for file in fileTree:
            path = file['path']
            if path.endswith('Dockerfile'):
                dk_file_path = path
                log.info(f'Found Dockerfile at {dk_file_path}')
                return dk_file_path
        log.warning('Dockerfile not found in repository.')
        return False

    def pull(self, dir_path):
        def _download(file_list, output_dir):
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            for file in file_list:
                if file['type'] == 'file':
                    file_name = file['name']
                    download_url = file['download_url']

                    if download_url:
                        # print(f"Downloading {file_name}...")
                        response = requests.get(download_url, headers=self.api_headers)
                        if response.status_code == 200:
                            with open(os.path.join(output_dir, file_name), 'wb') as f:
                                f.write(response.content)
                            # print(f"File {file_name} downloaded.")
                        else:
                            print(f"Failed to download {file_name}. HTTP {response.status_code}")
                    # else: print(f"No download URL for {file_name}. Skipping.")

                elif file['type'] == 'dir':
                    dir_name = file['name']
                    dir_url = file['url']
                    # print(f"Entering directory {dir_name}...")
                    response = requests.get(dir_url, headers=self.api_headers)
                    if response.status_code == 200:
                        sub_files = response.json()
                        sub_dir = os.path.join(output_dir, dir_name)
                        _download(sub_files, sub_dir)
                    else:
                        log.error(f"Failed to access directory {dir_name}. HTTP {response.status_code}")

        req_url = f'{self.url}/contents/?ref={self.branch}'
        log.info(f'Downloading repository contents from {req_url}')
        res = requests.get(req_url, headers=self.api_headers)
        if res.status_code != 200:
            log.error(f'Failed to fetch repository contents: {res.json()["message"]}')
            raise ApiResponseError(res)
        files = res.json()
        src_path = os.path.join(dir_path, 'src')
        _download(files, src_path)

    def __init__(self, url: str, access_token: str, branch: str = 'default'):
        self.page_url = url
        self.api_headers = { "Authorization": f"token {access_token}" }

        data = self._getRepoData(url)
        self._setRepoData(data)
        self.branch = self._getRepoBranch(branch)


class DockerApp:
    name: str                       # unique name
    port: int                       # port on which app works
    repo: "GitHubRepo"

    pc_port: int                    # localhost:port on which app available
    dk_file_path: str               # file path relative to repository root
    dir_path: str                   # directory that includes app's info.json

    @classmethod
    def load(cls, app_name: str):
        path = os.path.join(AppDir.APPS_DIR, app_name, 'info.json')
        if not os.path.exists(path):
            raise ValueError(f"App with name ({app_name}) not found")
        
        info_data = JsonEditor.read(path)
        app = cls.__new__(cls)
        attrs = info_data['attrs']

        def set_attributes(obj, attr_data, cls_type):
            for attr, value in attr_data.items():
                if attr in cls_type.__annotations__:
                    expected_type = cls_type.__annotations__[attr]
                    if isinstance(value, dict) and hasattr(expected_type, "__annotations__"):
                        nested_obj = expected_type.__new__(expected_type)
                        set_attributes(nested_obj, value, expected_type)
                        setattr(obj, attr, nested_obj)
                    else:
                        setattr(obj, attr, value)

        set_attributes(app, attrs, cls)
        return app

    @classmethod
    def to_wsl_path(cls, win_path: str):
        drive, path = win_path.split(":", 1)
        wsl_path = f"/mnt/{drive.lower()}{path.replace('\\', '/')}"
        return wsl_path

    def _set_pcport(self):
        def is_port_free(port) -> bool:
            res = Executer.run_cmd(f'netstat -an | findstr "127.0.0.1:{port}"')
            if res.returncode != 1: return False
            else: return True

        def generate_port(attempts) -> int:
            if attempts < 1: raise ValueError("Failed to generate port for localhost")
            port = random.randint(1025, 49150)
            if not is_port_free(port): return generate_port(attempts-1)
            return port

        if is_port_free(self.port):
            self.pc_port = self.port
        else:
            port = generate_port(3)
            self.pc_port = port

    def _del_image(self):
        res = Executer.run_cmd(f'wsl docker image prune -f')
        if res.returncode != 0:
            log.error(f'Failed to delete <none> docker images: {res.stderr}')
        res = Executer.run_cmd(f'wsl docker rmi --force {self.name}:latest')
        if res.returncode != 0:
            log.error(f'Failed to delete old Docker image: {res.stderr}')

    def _del_container(self):
        res = Executer.run_cmd(f'wsl docker stop {self.name}')
        if res.returncode != 0:
            log.warning(f'Docker stop container error: {res.stderr}', exc_info=True)
        res = Executer.run_cmd(f'wsl docker rm {self.name}')
        if res.returncode != 0:
            log.warning(f'Docker remove container error: {res.stderr}', exc_info=True)

    def __init__(self, name: str, port: int, repo: "GitHubRepo"):
        self.name = name
        self.port = port
        self.repo = repo
        path = repo._isDkfileExists()
        if not path: raise ValueError("Dockerfile not found")
        self.dk_file_path = path
        self.dir_path = AppDir.new_app_dir(name)

    def __del__(self):
        # Saving project data before destruction
        if hasattr(self, 'isDeleted') or not hasattr(self, 'name'): return
        data_obj = {}
        attrs = {}
        def save_obj(obj, obj_key=None):
            for key, value in obj.__dict__.items():
                if hasattr(value, '__dict__'):
                    save_obj(value, obj_key=key)
                else:
                    if obj_key: attrs.setdefault(obj_key, {})[key] = value
                    else: attrs[key] = value

        save_obj(self)
        data_obj.update({ 'app': attrs })
        path = os.path.join(self.dir_path, 'info.json')
        JsonEditor.overwrite(path, data_obj)

    def build(self):
        self._del_image()
        log.info(f'Starting Docker image build for {self.name}')
        dkfile_full_path = os.path.join(self.dir_path, 'src', self.dk_file_path)

        run_command = f'wsl docker build -t {self.name}:latest -f {self.to_wsl_path(dkfile_full_path)} {self.to_wsl_path(self.dir_path)}/src --no-cache'
        res = Executer.run_cmd(run_command)
        res.check_returncode()
        log.info(f'Docker image {self.name} built successfully.')

    def run(self):
        self._del_container()
        log.info(f'Starting container for {self.name}')
        run_command = f'wsl docker run --name {self.name} -d -p {self.pc_port}:{self.port} {self.name}:latest'
        res = Executer.run_cmd(run_command)
        if res.returncode != 0:
            log.error(f'Failed to start Docker container: {res.stderr}')
            raise ExecuterError(res)
        log.info(f'Container {self.name} started successfully.')

    def launch(self) -> int:
        """
        Build & Run
        """
        self.repo.pull(self.dir_path)
        self._set_pcport()
        self.build()
        self.run()
        return self.pc_port

