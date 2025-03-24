import json, os, requests, shutil, random
import logging as log
from .utils import ApiResponseError, ExecuterError, Executer, JsonEditor, AppDir
from typing import TypedDict


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
        config = AppDir.cf_config()
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
        JsonEditor.overwrite(AppDir.CF_CONFIG, config)
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
        config = AppDir.cf_config()
        config['tunnel']['ingress'].append(route)
        JsonEditor.overwrite(AppDir.CF_CONFIG, config)
        return route['service']

    def _set_dns_record(self):
        config = AppDir.cf_config()

        dns_record: CloudflareController.DNSRecord = {
            "type": "CNAME",
            "proxied": True,
            "name": f"{self.name}.{self.zone}",
            "content": f"{config['tunnel']['id']}.cfargotunnel.com"
        }
        self.cf_api.set_dns_record(dns_record)
        if not config.get('dns_records'): config['dns_records'] = []
        config['dns_records'].append(dns_record['name'])
        JsonEditor.overwrite(AppDir.CF_CONFIG, config)

    def tunneling(self):
        config = AppDir.cf_config()
        if not config.get('tunnel'): raise Exception('Create new tunnel before creatig route')
        
        self._set_dns_record()
        adress = self._set_route()
        # TODO checking route availability
        return adress

