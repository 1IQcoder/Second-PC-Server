import json, os, requests, yaml, shutil, base64, random
import logging as log
from src.config import BASE_DIR
from types import SimpleNamespace
from src.utils import ApiResponseError, ExecuterError, Executer, JsonEditor
# BASE_DIR = r'D:\\sklad\\txt\\SecondPC-server\\app'


class BaseController:
    CURRENT_DIR = BASE_DIR
    DB_DIR = os.path.join(CURRENT_DIR, 'db')
    REPOS_DIR = os.path.join(CURRENT_DIR, 'db', 'repos')
    ACCOUNTS_JSON_PATH = os.path.join(CURRENT_DIR, 'db', 'accounts.json')
    DELETE_REPO_BAT = os.path.join(CURRENT_DIR, 'bats', 'delete_repo.bat')
    USERS_FILE_PATH = os.path.join(DB_DIR, 'users.json')


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
    def add_account(api_token: str):
        saveData = JsonEditor.read(CFManager.CONFIG_PATH)
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        res = requests.get('https://api.cloudflare.com/client/v4/accounts', headers=headers)
        if res.status_code != 200: raise Exception(res.text)
        account = res.json()['result'][0]
        saveData['account'] = {
            'id': account['id'],
            'name': account['name'],
            'api_token': api_token
        }
        res = requests.get('https://api.cloudflare.com/client/v4/zones', headers=headers)
        if res.status_code != 200: raise Exception(res.text)
        zones = res.json()['result']
        if len(zones) < 1: raise Exception("This cloudflare account have not any zones")
        saveData['zones'] = {}
        for zone in zones:
            saveData['zones'][zone['name']] = {
                'name': zone['name'],
                'status': zone['status'],
                'id': zone['id']
            }
        JsonEditor.overwrite(CFManager.CONFIG_PATH, saveData)
        return saveData

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

    @staticmethod
    def set_zone(zone_name: str):
        config = JsonEditor.read(CFManager.CONFIG_PATH)
        config['tunnel']['zone'] = zone_name
        JsonEditor.overwrite(CFManager.CONFIG_PATH, config)

    name: str
    zone = 'spc-server.xyz'
    headers: dict

    def __init__(self, app_name: str):
        self.name = app_name
        config = JsonEditor.read(self.CONFIG_PATH)
        self.headers = {"Authorization": f"Bearer {config['account']['api_token']}", "Content-Type": "application/json"}

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


