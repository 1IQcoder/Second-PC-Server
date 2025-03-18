import json, os, requests, shutil, random
import logging as log
from src.config import BASE_DIR
from src.utils import ApiResponseError, ExecuterError, Executer, JsonEditor
from typing import TypedDict
# BASE_DIR = r'D:\\sklad\\txt\\SecondPC-server\\app'


class BaseController:
    CURRENT_DIR = BASE_DIR
    DB_DIR = os.path.join(CURRENT_DIR, 'db')
    REPOS_DIR = os.path.join(CURRENT_DIR, 'db', 'repos')
    ACCOUNTS_JSON_PATH = os.path.join(CURRENT_DIR, 'db', 'accounts.json')
    DELETE_REPO_BAT = os.path.join(CURRENT_DIR, 'bats', 'delete_repo.bat')
    USERS_FILE_PATH = os.path.join(DB_DIR, 'users.json')

class Directory:
    CURRENT_DIR = BASE_DIR
    DB_DIR = os.path.join(CURRENT_DIR, 'db')
    APPS_DIR = os.path.join(DB_DIR, 'apps')
    CF_CONFIG = os.path.join(DB_DIR, 'cloudflare.json')             # Cloudflare config (account data, zones list, tunnels data)

    @classmethod
    def new_app_dir(cls, app_name: str):
        if not os.path.isdir(cls.APPS_DIR): os.mkdir(cls.APPS_DIR)
        path = os.path.join(cls.APPS_DIR, app_name)
        if not os.path.isdir(path): os.mkdir(path)
        return path
    
    @classmethod
    def cf_config(cls) -> dict:
        if not os.path.exists(cls.CF_CONFIG): JsonEditor.overwrite(cls.CF_CONFIG, {})
        config = JsonEditor.read(cls.CF_CONFIG)
        return config
    
    @classmethod
    def is_cf_ready(cls) -> bool:
        """
        Checks the cloudflare.json file for account and tunnel info
        """
        config = cls.cf_config()
        if not config.get('account', False) or not config.get('tunnel', False):
            return False
        return True


class GHRepoManager:
    url: str
    private: bool
    default_branch: str
    owner: str              # 1IQcoder
    name: str               # Second-PC-Server
    full_name: str          # 1IQcoder/Second-PC-Server
    branch: str
    commit: str             # sha of downloaded commit
    api_headers: dict       # Authorization headers for GitHub API

    def _getRepoData(self, url: str) -> dict:
        req_url = url.replace("https://github.com/", "https://api.github.com/repos/").removesuffix(".git")
        log.info(f'Checking repository URL: {req_url}')
        res = requests.get(req_url, headers=self.api_headers)
        resData = res.json()
        if res.status_code != 200:
            if res.status_code == 404:
                raise ValueError("Repository not found")
            if res.status_code == 401:
                raise ValueError("Bad credentials, GitHub access_token is bad")
            raise ApiResponseError(resData['message'], req_url, status_code=res.status_code)
        log.info('Repository URL is valid.')
        return resData

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

    def git_pull(self, file_list, output_dir):
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
                    self.git_pull(sub_files, sub_dir)
                else:
                    print(f"Failed to access directory {dir_name}. HTTP {response.status_code}")

    def __init__(self, url, branch, git_hub_api_token):
        self.url = url
        self.api_headers = { "Authorization": f"token {git_hub_api_token}" }

        data = self._getRepoData(url)
        self._setRepoData(data)
        self.branch = self._getRepoBranch(branch)


class DockerManager:
    # launch docker in wsl
    Executer.run_cmd('wsl bash -c "nohup sudo dockerd > /dev/null 2>&1 &"').check_returncode()

    name: str                       # invalidobject.second-pc-server.branch
    dk_file_path: str               # file path relative to repository root
    port: int                       # port on which app works

    @staticmethod
    def to_wsl_path(win_path: str):
        drive, path = win_path.split(":", 1)
        wsl_path = f"/mnt/{drive.lower()}{path.replace('\\', '/')}"
        return wsl_path

    def delImage(self):
        res = Executer.run_cmd(f'wsl docker image prune -f')
        if res.returncode != 0:
            log.error(f'Failed to delete <none> docker images: {res.stderr}')
        res = Executer.run_cmd(f'wsl docker rmi --force {self.name}:latest')
        if res.returncode != 0:
            log.error(f'Failed to delete old Docker image: {res.stderr}')

    def delContainer(self):
        res = Executer.run_cmd(f'wsl docker stop {self.name}')
        if res.returncode != 0:
            log.warning(f'Docker stop container error: {res.stderr}', exc_info=True)
        res = Executer.run_cmd(f'wsl docker rm {self.name}')
        if res.returncode != 0:
            log.warning(f'Docker remove container error: {res.stderr}', exc_info=True)

    def is_dkfile_exists(self, repo: GHRepoManager) -> str:
        req_url = f'{repo.url}/git/trees/{repo.branch}?recursive=1'
        log.info(f'Checking Dockerfile existence in repository: {req_url}')
        res = requests.get(req_url, headers=repo.api_headers)
        if res.status_code != 200:
            log.error(f'Failed to fetch repository tree: {res.status_code}')
            raise ApiResponseError(res)
        fileTree = res.json()['tree']
        for file in fileTree:
            path = file['path']
            if path.endswith('Dockerfile'):
                self.dk_file_path = path
                log.info(f'Found Dockerfile at {self.dk_file_path}')
                return file['path']
        log.warning('Dockerfile not found in repository.')
        return False

    def __init__(self, appName: str, app_port: int, repo: GHRepoManager):
        self.name = appName.lower()
        self.port = app_port
        path = self.is_dkfile_exists(repo)
        if not path: raise ValueError("Dockerfile not found")
        self.dk_file_path = path


class CFManager:
    """
    CloudFlare manager\n
    Control DNS records and tunnel routing
    """
    CONFIG_PATH = os.path.join(BaseController.CURRENT_DIR, 'db', 'cloudflare.json')
    if not os.path.exists(CONFIG_PATH):
        JsonEditor.overwrite(CONFIG_PATH, {})

    @staticmethod
    def add_account(api_token: str, zone_name: str):
        config = JsonEditor.read(CFManager.CONFIG_PATH)
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        res = requests.get('https://api.cloudflare.com/client/v4/accounts', headers=headers)
        if res.status_code != 200: raise Exception(res.text)
        account = res.json()['result'][0]
        config['account'] = {
            'id': account['id'],
            'name': account['name'],
            'api_token': api_token
        }
        res = requests.get('https://api.cloudflare.com/client/v4/zones', headers=headers)
        if res.status_code != 200: raise Exception(res.text)
        zones = res.json()['result']
        if len(zones) < 1: raise Exception("This cloudflare account have not any zones")
        config['zones'] = {}
        for zone in zones:
            config['zones'][zone['name']] = {
                'name': zone['name'],
                'status': zone['status'],
                'id': zone['id']
            }
        if not zone_name in config['zones']: raise ValueError('zone name is incorrect')
        if not config.get('tunnel', False): config['tunnel'] = {}
        config['tunnel']['zone'] = zone_name
        JsonEditor.overwrite(CFManager.CONFIG_PATH, config)
        return config

    @staticmethod
    def create_tunnel(tunnel_name: str = 'scps_tunnel'):
        config = JsonEditor.read(CFManager.CONFIG_PATH)
        headers = {"Authorization": f"Bearer {config['account']['api_token']}", "Content-Type": "application/json"}
        data = {
            "name": tunnel_name,
            "config_src": "cloudflare"
        }
        res = requests.post(f'https://api.cloudflare.com/client/v4/accounts/{config["account"]["id"]}/cfd_tunnel',
            headers=headers,
            json=data)
        res.raise_for_status()
        res_data = res.json()
        if not res_data['success']: raise Exception(res_data['errors'])
        if not config.get('tunnel'): config['tunnel'] = {}
        config['tunnel']['id'] = res_data['result']['id']
        JsonEditor.overwrite(CFManager.CONFIG_PATH, config)

    name: str
    zone: str
    headers: dict

    def __init__(self, app_name: str):
        self.name = app_name
        config = JsonEditor.read(self.CONFIG_PATH)
        self.headers = {"Authorization": f"Bearer {config['account']['api_token']}", "Content-Type": "application/json"}
        self.zone = config['tunnel']['zone']['name']

    def _set_route(self, local_port: int):
        config = JsonEditor.read(self.CONFIG_PATH)
        headers = {"Authorization": f"Bearer {config['account']['api_token']}", "Content-Type": "application/json"}
        zone_name = config['tunnel']['zone']['name']
        account_id = config['account']['id']
        tunnel_id = config['tunnel']['id']

        new_route = {
            "hostname": f"{self.name}.{zone_name}",
            "service": f"http://172.24.240.192:{local_port}"
        }
        if not config['tunnel'].get('ingress'): config['tunnel']['ingress'] = [{ "service": "http_status:404" }]
        config['tunnel']['ingress'].insert(0, new_route)
        data = {
            "config": {
                "ingress": config['tunnel']['ingress']
            }
        }
        print(data)
        res = requests.put(f'https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations',
            headers=headers,
            json=data)
        res.raise_for_status()
        JsonEditor.overwrite(self.CONFIG_PATH, config)

    def create_route(self, local_port: int):
        config = JsonEditor.read(self.CONFIG_PATH)
        if not config.get('tunnel'): raise Exception('Create new tunnel before creatig route')
        data = {
            "type": "CNAME",
            "proxied": True,
            "name": f"{self.name}.{self.zone}",
            "content": f"{config['tunnel']['id']}.cfargotunnel.com"
        }
        zone_id = config['tunnel']['zone']['id']
        res = requests.post(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records',
            headers=self.headers,
            json=data)
        
        # res_data = res.json()
        # if not res_data['success']: raise Exception(res_data['errors'])
        if not config.get('dns_records'): config['dns_records'] = []
        config['dns_records'].append(data['name'])

        JsonEditor.overwrite(self.CONFIG_PATH, config)
        self._set_route(local_port)


class ProjectConfig:
    def __init__(self, web_url: str = None, ghAccess_token: str = None, branch: str = 'default',
                 appName: str = None, appPort: int = None, user=None):
        self.web_url = web_url
        self.ghAccess_token = ghAccess_token
        self.branch = branch
        self.appName = appName
        self.appPort = appPort
        self.user = user


class Project(BaseController):
    """
    #### Can be initialized with: `url` or repository. Example: https://api.github.com/repos/1IQcoder/Second-PC-Server
    #### Can be loaded with `hash` of already initialized repository
    """
    name: str
    project_owner: str           # InvalidObject (discord username)
    dir_path: str
    local_port: int              # automatics generated

    repo: GHRepoManager
    docker: DockerManager
    cloudflare: CFManager

    def _generate_pcport(self, attempts):
            if attempts < 1: raise ValueError("Failed to generate port for localhost")
            port = random.randint(1025, 49150)
            res = Executer.run_cmd(f'netstat -an | findstr "127.0.0.1:{port}"')
            if res.returncode != 1: return self._generate_pcport(attempts-1)
            self.local_port = port

    def __init__(self, config: ProjectConfig, repo: GHRepoManager, docker: DockerManager, cloudflare: CFManager, user: "User" = None):
        self.project_owner = user.username if user else ''
        self.name = config.appName
        self.repo = repo
        self.docker = docker
        self.cloudflare = cloudflare
        self.dir_path = os.path.join(BaseController.DB_DIR, 'repos', self.project_owner, self.name)
        self._generate_pcport(3)

        if os.path.exists(self.dir_path): shutil.rmtree(self.dir_path)
        os.mkdir(self.dir_path)

    @classmethod
    def load_project(cls, project_name: str, user: "User" = None):
        path = os.path.join(BaseController.DB_DIR, 'repos', user.username if user else '', project_name, 'info.json')
        if not os.path.exists(path):
            raise ValueError(f"Repository with name ({project_name}) not found")
        
        info_data = JsonEditor.read(path)
        project = cls.__new__(cls)
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

        set_attributes(project, attrs, cls)
        project._generate_pcport(3)
        return project

    def __del__(self):
        # Saving project data before destruction
        if hasattr(self, 'isDeleted') or not hasattr(self, 'name'): return
        dataObj = {
            'docker': {
                'imageName': self.name,
                'rootPath': self.docker.dk_file_path,
                'buildCommand': f'docker build -t {self.name}:latest {self.name} --no-cache',
                'containerStatus': 'offline',
                'runCommand': f'docker run --name {self.name} -d -p {self.docker.port}:${self.local_port} ${self.name}:latest'
            }
        }
        attrs = {}
        def save_obj(obj, obj_key=None):
            for key, value in obj.__dict__.items():
                if hasattr(value, '__dict__'):
                    save_obj(value, obj_key=key)
                else:
                    if obj_key: attrs.setdefault(obj_key, {})[key] = value
                    else: attrs[key] = value

        save_obj(self)
        dataObj.update({ 'attrs': attrs })
        path = os.path.join(self.dir_path, 'info.json')
        JsonEditor.overwrite(path, dataObj)

    def download(self):
        req_url = f'{self.repo.url}/contents/?ref={self.repo.branch}'
        log.info(f'Downloading repository contents from {req_url}')
        res = requests.get(req_url, headers=self.repo.api_headers)
        if res.status_code != 200:
            log.error(f'Failed to fetch repository contents: {res.json()["message"]}')
            raise ApiResponseError(res)
        files = res.json()
        src_path = os.path.join(self.dir_path, 'src')
        self.repo.git_pull(files, src_path)
        log.info(f'Repository {self.name} downloaded successfully.')
        res = requests.get(f'{self.repo.url}/commits/{self.repo.branch}', headers=self.repo.api_headers)
        if res.status_code != 200: log.error('Downloaded commit sha is not set')
        self.repo.commit = res.json()['sha']

    def delete(self):
        log.info(f'Removing project ({self.name}) from docker')
        self.docker.delContainer()
        self.docker.delImage()
        log.info(f'Deleting project ({self.name})...')
        shutil.rmtree(self.dir_path, True)
        self.isDeleted = True # for __del__ method
        log.info(f'Project ({self.name}) deleted.')

    def build(self):
        self.docker.delImage()
        log.info(f'Starting Docker image build for {self.docker.name}')
        dkfile_full_path = os.path.join(self.dir_path, 'src', self.docker.dk_file_path)

        run_command = f'wsl docker build -t {self.docker.name}:latest -f {DockerManager.to_wsl_path(dkfile_full_path)} {DockerManager.to_wsl_path(self.dir_path)}/src --no-cache'
        res = Executer.run_cmd(run_command)
        if res.returncode != 0:
            log.error(f'Failed to build Docker image: {res.stderr}')
            raise ExecuterError(res)
        log.info(f'Docker image {self.docker.name} built successfully.')

    def run(self):
        self.docker.delContainer()
        log.info(f'Starting container for {self.name}')
        run_command = f'wsl docker run --name {self.docker.name} -d -p {self.local_port}:{self.docker.port} {self.docker.name}:latest'
        res = Executer.run_cmd(run_command)
        if res.returncode != 0:
            log.error(f'Failed to start Docker container: {res.stderr}')
            raise ExecuterError(res)
        log.info(f'Container {self.name} started successfully.')

    def tunnel(self):
        self.cloudflare.create_route(self.local_port)


class ProjectFactory:
    @staticmethod
    def create(init_method: str | ProjectConfig, user=None):
        if type(init_method) == str:
            return Project.load_project(init_method, user=user)
        
        elif isinstance(init_method, ProjectConfig):
            config = init_method
            repo = GHRepoManager(config.web_url, config.branch, config.ghAccess_token)
            docker = DockerManager(config.appName, config.appPort, repo)
            cloudflare = CFManager(config.appName)
            return Project(config, repo, docker, cloudflare, user=user)
        
        else: raise ValueError("ProjectFactory: incorrect initialization parameters")


class User(BaseController):
    USERS_FILE_PATH = BaseController.USERS_FILE_PATH
    if not os.path.exists(BaseController.USERS_FILE_PATH):
        JsonEditor.overwrite(BaseController.USERS_FILE_PATH, {})

    username: str
    userObj: dict
    userFolderPath: str

    def __init__(self, username: str):
        self.username = username
        self.userFolderPath = os.path.join(self.DB_DIR, 'repos', username)
        if not os.path.exists(self.userFolderPath): os.mkdir(self.userFolderPath)
        fileData = None
        if os.path.exists(User.USERS_FILE_PATH):
            fileData = JsonEditor.read(self.USERS_FILE_PATH)
        if fileData and (username in fileData.keys()):
            self.userObj = fileData[username]
        else:
            self.userObj = {
                'username': username,
                'projects': {}
            }

    def __del__(self):
        # save user data to json file
        fileData = {}
        if os.path.exists(User.USERS_FILE_PATH):
            fileData = JsonEditor.read(self.USERS_FILE_PATH)
        fileData[self.username] = self.userObj
        JsonEditor.overwrite(self.USERS_FILE_PATH, fileData)
        if len(os.listdir(self.userFolderPath)) < 1:
            os.rmdir(self.userFolderPath)

    def newProject(self, config: ProjectConfig) -> Project:
        """
        Returns created project
        """
        project = ProjectFactory.create(config, user=self)
        project_obj = {
            'name': project.name,
            'branch': project.repo.branch
        }
        self.userObj['projects'][project.name] = project_obj
        return project

    def loadProject(self, project_name: str) -> Project:
        return Project.load_project(project_name, user=self)

    def deleteProject(self, project_name: str):
        """
        Returns project_name
        """
        project = ProjectFactory.create(project_name, user=self)
        project.delete()
        del self.userObj['projects'][project.name]
        return project_name

    def getProjects(self) -> dict | None:
        """
        Returns dict or None if project list emty
        """
        projects = self.userObj['projects']
        if len(projects) > 0:
            return projects
        else: return None


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
        path = os.path.join(Directory.APPS_DIR, app_name, 'info.json')
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
        self.dir_path = Directory.new_app_dir(name)

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
        self.repo.pull(self.dir_path)
        self._set_pcport()
        self.build()
        self.run()
        return self.pc_port


class CloudflareController:
    headers: dict
    zone_id: str
    account_id: str
    tunnel_id: str

    class DNSRecord(TypedDict):
        type: str
        proxied: str
        name: str
        content: str

    class IngressRoute(TypedDict):
        hostname: str
        service: str

    def __init__(self):
        config = Directory.cf_config()
        if not config.get('account'): raise ValueError("Cloudflare account not set")
        if not config.get('tunnel'): raise ValueError("Cloudflare tunnel not created")

        self.headers = {"Authorization": f"Bearer {config['account']['api_token']}", "Content-Type": "application/json"}
        self.zone_id = config['tunnel']['zone']['id']
        self.account_id = config['account']['id']
        self.tunnel_id = config['tunnel']['id']

    def _request(self, method: str, url: str, json: dict = None) -> dict:
        try:
            res = requests.request(method, url, headers=self.headers, json=json)
            res_data = res.json()
            if not res_data.get("success"):
                raise Exception(res_data.get("errors", "Unknown error"))
            return res_data["result"]
        except Exception as e:
            raise ApiResponseError(res) from e
        
    @classmethod
    def request(cls, method: str, url: str, headers: dict, json: dict = None) -> dict:
        try:
            res = requests.request(method, url, headers=headers, json=json)
            res_data = res.json()
            if not res_data.get("success"):
                raise Exception(res_data.get("errors", "Unknown error"))
            return res_data["result"]
        except Exception as e:
            res.raise_for_status()

    def set_dns_record(self, data: DNSRecord) -> None:
        url = f'https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records'
        self._request(method='POST', url=url, json=data)

    def add_ingress_route(self, route: IngressRoute) -> None:
        url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/cfd_tunnel/{self.tunnel_id}/configurations'
        res = self._request(method='GET', url=url)

        ingress: list = res['ingress']
        ingress.insert(0, route)
        ingress.append({ "service": "http_status:404" })
        print(ingress)

        data = {
            "config": {
                "ingress": ingress
            }
        }

        url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/cfd_tunnel/{self.tunnel_id}/configurations'
        self._request(method='PUT', url=url, json=data)

    def del_ingress_route(self, hostname: str):
        url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/cfd_tunnel/{self.tunnel_id}/configurations'
        res = self._request(method='GET', url=url)

        ingress: list = res['ingress']
        if len(ingress) > 0:
            ingress = [route for route in ingress if route['hostname'] != hostname]
        ingress.append({ "service": "http_status:404" })
        print(ingress)

        data = {
            "config": {
                "ingress": ingress
            }
        }

        url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/cfd_tunnel/{self.tunnel_id}/configurations'
        self._request(method='PUT', url=url, json=data)

    @classmethod
    def set_config(cls, api_token: str, zone_name: str, tunnel_name: str = 'spcs-tunnel'):
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

        def check_account():
            url = 'https://api.cloudflare.com/client/v4/accounts'
            return cls.request('GET', url, headers)

        def check_zone():
            url = 'https://api.cloudflare.com/client/v4/zones'
            zones = cls.request('GET', url, headers)
            if len(zones) < 1: raise Exception("This cloudflare account have not any zones")
            for zone in zones:
                if zone_name == zone['name']: return zone
            raise Exception(f'Zone {zone_name} does not belong to this account')

        def tunnel(account_id, tunnel_name):
            def create_tunnel():
                data = {
                    "name": tunnel_name,
                    "config_src": "cloudflare"
                }
                url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel'
                return cls.request('POST', url, headers, json=data)

            url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel'
            tunnels = cls.request('GET', url, headers)

            if len(tunnels) < 1: return create_tunnel()
            for tunnel in tunnels:
                if tunnel['name'] == tunnel_name:
                    return tunnel
            return create_tunnel()

        account = check_account()[0]
        zone = check_zone()
        new_tunnel = tunnel(account['id'], tunnel_name)

        config = {
            'account': {
                'id': account['id'],
                'name': account['name'],
                'api_token': api_token
            },
            'tunnel': {
                'name': new_tunnel['name'],
                'id': new_tunnel['id'],
                'zone': {
                    'name': zone['name'],
                    'id': zone['id']
                }
            }
        }
        JsonEditor.overwrite(Directory.CF_CONFIG, config)
        return config


class TunnelBuilder:
    name: str
    zone: str = 'spc-server.xyz'
    cf_api: CloudflareController
    pc_port: int

    def __init__(self, app: DockerApp):
        """
        Init with localport or DockerApp object
        """
        self.cf_api = CloudflareController()
        self.name = app.name
        self.pc_port = app.pc_port

    def _set_route(self):
        route: CloudflareController.IngressRoute = {
            "hostname": f"{self.name}.{self.zone}",
            "service": f"http://172.24.240.192:{self.pc_port}"
        }
        self.cf_api.add_ingress_route(route)
        config = Directory.cf_config()
        config['tunnel']['ingress'].append(route)
        JsonEditor.overwrite(Directory.CF_CONFIG, config)
        return route['service']

    def _set_dns_record(self):
        config = Directory.cf_config()

        dns_record: CloudflareController.DNSRecord = {
            "type": "CNAME",
            "proxied": True,
            "name": f"{self.name}.{self.zone}",
            "content": f"{config['tunnel']['id']}.cfargotunnel.com"
        }
        self.cf_api.set_dns_record(dns_record)
        if not config.get('dns_records'): config['dns_records'] = []
        config['dns_records'].append(dns_record['name'])
        JsonEditor.overwrite(Directory.CF_CONFIG, config)

    def tunneling(self):
        config = Directory.cf_config()
        if not config.get('tunnel'): raise Exception('Create new tunnel before creatig route')
        
        self._set_dns_record()
        adress = self._set_route()
        # TODO checking route availability
        return adress



"""
DockerApp, обьекты сохраняются в projects и могут быть загружены по appName | принимает GitHubRepo параметром
TunnelBuilder принимает DcokerApp либо (port, appName)

Projects сохраняются в json: DockerApp, Tunnel
"""