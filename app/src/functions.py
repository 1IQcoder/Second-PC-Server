import subprocess, json, os, requests, yaml, shutil, base64
from subprocess import CompletedProcess
import logging as log
from src.config import BASE_DIR
# BASE_DIR = r'D:\\sklad\\txt\\SecondPC-server\\app'

class ApiResponseError(Exception):
    def __init__(self, res, message='-', requestUrl='-', status_code='-'):
        if res:
            self.message = res.text
            self.requestUrl = res.url
            self.status_code = res.status_code
        else:
            self.message = message
            self.requestUrl = requestUrl
            self.status_code = status_code

    def __str__(self):
        return (
            f"ResponseContent: {self.message} \n"
            f"(URL: {self.requestUrl}, Status Code: {self.status_code})"
        )


class ExecuterError(Exception):
    def __init__(self, result: CompletedProcess):
        self.stdout = result.stdout.strip()
        self.stderr = result.stderr.strip()
        self.command = result.args
        self.returncode = result.returncode

    def __str__(self):
        return (
            f"Execute command error; command='{self.command}' \n"
            f"Stdout ({self.stdout})\n"
            f"Stderr ({self.stderr})\n"
        )


class Executer:
    @staticmethod
    def run_cmd(command: str) -> CompletedProcess:
        """
        Executes a shell command and returns the result.
        
        :param command: The command to execute as a string.
        :return: A CompletedProcess object containing the execution result.
        """
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            shell=isinstance(command, str)
        )
        log.info(f'running command: ({command}); code: {result.returncode}')
        return result

    @staticmethod
    def run_batch(scriptName: str, *args) -> CompletedProcess:
        """
        Executes a .bat script with optional parameters.
        
        :param scriptName: The name of the .bat script to run.
        :param args: Arguments to pass to the script.
        :return: A CompletedProcess object containing the execution result.
        """
        scriptPath = os.path.join(BASE_DIR, 'bats', scriptName)
        if not os.path.exists(scriptPath): raise ValueError("Bat file not found")
        command = [scriptPath, *args]
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        return result


class SSEEvents:
    @staticmethod
    def info(msg, closeConnection: bool = False):
        msgToSend = json.dumps({ 'type': 'info', 'msg': msg, 'close': closeConnection })
        yield f'data: {msgToSend} \n\n'

    @staticmethod
    def error(msg, closeConnection: bool = False):
        msgToSend = json.dumps({ 'type': 'error', 'msg': msg, 'close': closeConnection })
        yield f'data: {msgToSend} \n\n'

    @staticmethod
    def fatal(msg = 'FATAL ERROR'):
        msgToSend = json.dumps({ 'type': 'fatal', 'msg': msg, 'close': True })
        yield f'data: {msgToSend} \n\n'

    @staticmethod
    def sendJson(data: dict | str, closeConnection: bool = False):
        if type(data) == dict: data = json.dumps(data)
        msgToSend = json.dumps({ 'type': 'json', 'data': data, 'close': closeConnection })
        yield f'data: {msgToSend} \n\n'

    @staticmethod
    def close(msg: str = None):
        data = { 'type': 'close' }
        if msg: data['msg'] = msg
        msgToSend = json.dumps(data)
        yield f'data: {msgToSend} \n\n'


class JsonEditor:
    @staticmethod
    def overwrite(jsonFilePath: str, dataToWrite: dict) -> None:
        dirPath = os.path.dirname(jsonFilePath)
        if not os.path.exists(dirPath): raise ValueError("json file not found in the specified directory")
        with open(jsonFilePath, 'w') as file:
            json.dump(dataToWrite, file, indent=4, ensure_ascii=False)
        print(f"Файл {jsonFilePath} успешно перезаписан.")

    @staticmethod
    def read(file_path) -> dict:
        """
        Reads data from .json file

        Returns dictrionary or None if error occured
        """
        with open(file_path, 'r') as file:
            data = json.load(file)
        if not data: return {}
        return data


class BaseController:
    CURRENT_DIR = BASE_DIR
    DB_DIR = os.path.join(CURRENT_DIR, 'db')
    REPOS_DIR = os.path.join(CURRENT_DIR, 'db', 'repos')
    ACCOUNTS_JSON_PATH = os.path.join(CURRENT_DIR, 'db', 'accounts.json')
    DELETE_REPO_BAT = os.path.join(CURRENT_DIR, 'bats', 'delete_repo.bat')
    USERS_FILE_PATH = os.path.join(DB_DIR, 'users.json')


class AccountsController(BaseController):
    """
    Methods for working with accounts.json
    """

    def __init__(self):
        if not os.path.exists(self.ACCOUNTS_JSON_PATH):
            with open(self.ACCOUNTS_JSON_PATH, "w") as file:
                file.write('{}')

    def getAccounts(self) -> tuple[bool, dict]:
        """
        Reads the accounts.json file.

        Return tuple[isEmpty(bool), accounts(dict)]
        """
        accs = JsonEditor.read(self.ACCOUNTS_JSON_PATH)
        if len(accs) < 1:
            return True, {}
        return False, accs
    
    def getAccount(self, username: str) -> dict | None:
        """
        Reads the accounts.json file.

        Parametrs:
            account username
        
        Return account object (dict) or None
        """
        accs = JsonEditor.read(self.ACCOUNTS_JSON_PATH)
        if accs[username]:
            return accs[username]
        return None

    def addAccount(self, account: dict) -> None:
        """
        Writes a new account object to accounts.json

        Parameters:
            account (dict): { username, name, access_token }
        """
        isEmpty, file = self.getAccounts()
        file[account['username']] = account
        JsonEditor.overwrite(self.ACCOUNTS_JSON_PATH, file)

    def deleteAccount(self, account: dict | str) -> None:
        """
        Deletes account from accounts.json

        Parameters:
            account (dict): { username, name, access_token } OR account username (str)
        """
        isEmpty, file = self.getAccounts()
        if type(account == str):
            del file[account]
        elif type(account == dict):
            del file[account['username']]
        JsonEditor.overwrite(self.ACCOUNTS_JSON_PATH, file)


class ReposController(BaseController):
    def __init__(self):
        if not os.path.exists(self.REPOS_DIR): os.mkdir(self.REPOS_DIR)

    """
    Methods for working with info.json files in local repositories
    """
    def getRepos(self) -> tuple[bool, dict]:
        """
        Returns tuple:
            isEmpty (bool)\n
            repoName/info.json datas (list)
        """
        reposList = []
        repoDirs = os.listdir(self.REPOS_DIR)

        if len(repoDirs) < 1:
            return True, []

        for repo in repoDirs:
            repoPath = os.path.join(self.REPOS_DIR, repo)
            infoPath = os.path.join(repoPath, 'info.json')

            if not os.path.isdir(repoPath) or not os.path.exists(infoPath):
                continue

            with open(infoPath, 'r') as file:
                repo_info = json.load(file)
                reposList.append(repo_info)
        return False, reposList
    
    def getRepo(self, repoName: str | dict) -> dict | None:
        """
        Returns:
            data (dict) or None if not repo
        """
        if not os.path.isdir(os.path.join(self.REPOS_DIR, repoName)):
            # repo not found
            return None
        file = JsonEditor.read(os.path.join(self.REPOS_DIR, repoName, 'info.json'))
        if not file:
            return None
        return file

    def addRepo(self, repoObj: dict):
        """
        Added new repository. Creates a new repository folder and info.json file.
        """
        os.mkdir(os.path.join(self.REPOS_DIR, repoObj['name']))
        pathToInfo = os.path.join(self.REPOS_DIR, repoObj['name'], 'info.json')
        JsonEditor.overwrite(pathToInfo, repoObj)
        log.info(f"New repository created ({repoObj['name']})")

    def deleteRepo(self, repo: dict | str) -> None | str:
        """
        Removes repository from repoName/info.json

        Parameters:
            repoObject (dict) or repoFullName (str)

        Return exception (str) if an errors occurs
        """
        repoName = ''
        if type(repo) == str:
            repoName = repo
        elif type(repo) == dict:
            repoName = repo['name']
        deleteFolder = os.path.join(self.REPOS_DIR, repoName)
        print('deleteFolder ', deleteFolder)

        try:
            result = subprocess.run(
                [self.DELETE_REPO_BAT, deleteFolder],
                check=True,
                text=True,
                capture_output=True,
            )
            log.info(f"Repository ({repoName}) deleted successfully.")
            log.debug(f"Command output: {result.stdout}")
        except Exception as e:
            log.exception(f"An unexpected error occurred while deleting the repository ({repoName}).")
            return str(e)

    def updateRepo(self, repo: dict | str, forUpdates: dict) -> None | str:
        """
        Updates information in repoFolder/info.json

        Parameters:\n
            1. repoObject (dict) or repoFullName (str)\n
            2. valuesForUpdate (dict) example: { 'a': 46, 'j/dsgd/34': 'pon' }

        Return exception (str) if an errors occurs
        """
        repoName = ''
        if type(repo) == str:
            repoName = repo
        elif type(repo) == dict:
            repoName = repo['name']

        infoFilePath = os.path.join(self.REPOS_DIR, repoName, 'info.json')
        infoFile = JsonEditor.read(infoFilePath)

        def setInfoValue(dictionary, keys, value):
            current = dictionary
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value

        try:
            for key, value in forUpdates.items():
                subkeys = key.split('/')
                setInfoValue(infoFile, subkeys, value)
        except Exception as e:
            log.exception(f"Update values in {repoName}/info.json' error: {e}")
            return str(e)

        JsonEditor.overwrite(infoFilePath, infoFile)
        log.info(f'Updated values: {forUpdates} in {repoName}/info.json')

    def createUserFolder(self, username: str) -> None:
        folderPath = os.path.join(self.REPOS_DIR, username)
        if not os.path.isdir(folderPath):
            os.mkdir(folderPath)

    @staticmethod
    def urlToName(url: str):
        """
        Input: "https://github.com/1IQcoder/Second-PC-Server.git"
        Returns: "second-pc-server"
        """
        return url.rstrip('/').split('/')[-1].removesuffix('.git')
    
    @staticmethod
    def urlToOwnerName(url: str):
        """
        Input: "https://github.com/1IQcoder/Second-PC-Server.git"
        Returns: "1iqcoder"
        """
        return url.rstrip('/').split('/')[-2]
    
    @staticmethod
    def urlToFullName(url: str, replaceSlashToDot = False):
        """
        Input: "https://github.com/1IQcoder/Second-PC-Server.git"
        Returns: "1iqcoder/second-pc-server" or "1iqcoder.second-pc-server"
        """
        parts = url.rstrip('.git').split('/')
        res = f'{parts[-2]}/{parts[-1]}'
        if replaceSlashToDot: res = res.replace('/', '.')
        return res
    
    @staticmethod
    def readRepoFiles(repoFullName: str, headers: dict = None) -> tuple[bool, dict | str]:
        """
        Returns tuple[isErrorOccured(bool), data or errorMsg]
        """
        res = requests.get(f'https://api.github.com/repos/{repoFullName}/contents/', headers=headers)
        if res.status_code != 200: return False, res.json()['message']
        return False, res.json()
    
    @staticmethod
    def findFileInRepo(repoFullName: str, headers: dict = None):
        res = requests.get(f'https://api.github.com/repos/{repoFullName}/contents/', headers=headers)
        if res.status_code != 200: return False, res.json()['message']


class Repo(BaseController):
    """
    #### Can be initialized with:
    1. `url` or repository. Example: https://api.github.com/repos/1IQcoder/Second-PC-Server
    2. `full_name` of repository. Example: 1IQcoder/Second-PC-Server
    #### Can be loaded with `hash` of already initialized repository
    """
    url: str                    # https://api.github.com/repos/1IQcoder/Second-PC-Server
    hash: str
    private: bool
    branch: str
    ports: list                 # [pcPort, dockerPort]
    repoOwner: str              # 1IQcoder
    repoFullName: str           # 1IQcoder/Second-PC-Server
    repoName: str               # Second-PC-Server
    projectOwner: str           # InvalidObject (discord username)
    name: str                   # InvalidObject.Second-PC-Server.branch
    dockerName: str             # invalidobject.second-pc-server.branch
    dirPath: str
    dkfilePath: str             # file path relative to repository root

    def _isRepoExists(self, urlOrFullname) -> bool:
        """
        #### Param `urlOrFullname` can be:
        1. `git url`. Example: https://github.com/1IQcoder/Second-PC-Server.git
        2. `repository full name`. Example: 1IQcoder/Second-PC-Server
        #### Checking repo exists and setting attrs:
        1. `url`
        2. `repoName`
        3. `repoFullName`
        4. `repoOwner`
        5. `private`
        """
        if urlOrFullname.startswith('https://'):
            reqUrl = urlOrFullname.replace("https://github.com/", "https://api.github.com/repos/").removesuffix(".git")
        else:
            reqUrl = f'https://api.github.com/repos/{urlOrFullname}'
        log.info(f'Checking repository URL: {reqUrl}')
        res = requests.get(reqUrl, headers=self.ghHeaders)
        resData = res.json()
        if res.status_code != 200:
            if res.status_code == 404:
                log.error("Repository not found")
                raise ValueError("Repository not found")
            if res.status_code == 401:
                log.error("Bad credentials, GitHub access_token is bad")
                raise ValueError("Bad credentials, GitHub access_token is bad")
            log.error(f'GitHub API error: {resData["message"]}')
            raise ApiResponseError(resData['message'], reqUrl, status_code=res.status_code)
        log.info('Repository URL is valid.')
        self.url = resData['url']
        self.repoName = resData['name']
        self.repoFullName = resData['full_name']
        self.repoOwner = resData['owner']['login']
        self.private = resData['private']
        self.repoDefaultBranch = resData['default_branch']
        return True

    def _isBranchValid(self, branch) -> bool:
        """
        #### Checking branch exists and setting `self.branch`
        """
        if branch == 'default':
            self.branch = self.repoDefaultBranch
            del self.repoDefaultBranch
            return True
        reqUrl = f'{self.url}/branches/{branch}'
        res = requests.get(reqUrl, headers=self.ghHeaders)
        if res.status_code != 200:
            if res.status_code == 404:
                return False
            raise ApiResponseError(res.json()['message'], reqUrl, res.status_code)
        self.branch = branch
        return True

    def _isDockerfileExists(self) -> str:
        reqUrl = f'{self.url}/git/trees/{self.branch}?recursive=1'
        log.info(f'Checking Dockerfile existence in repository: {reqUrl}')
        res = requests.get(reqUrl, headers=self.ghHeaders)
        if res.status_code != 200:
            log.error(f'Failed to fetch repository tree: {res.status_code}')
            raise ApiResponseError(res)
        fileTree = res.json()['tree']
        for file in fileTree:
            path = file['path']
            if path.endswith('Dockerfile'):
                self.dkfilePath = path
                log.info(f'Found Dockerfile at {self.dkfilePath}')
                return file['path']
        log.warning('Dockerfile not found in repository.')
        return False

    def _load_attrs(self, infoFilePath):
        infoData = JsonEditor.read(infoFilePath)
        attrs = infoData['attrs']
        for attr in attrs.keys():
            setattr(self, attr, attrs[attr])

    def _git_pull(self, file_list, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for file in file_list:
            if file['type'] == 'file':
                file_name = file['name']
                download_url = file['download_url']

                if download_url:
                    # print(f"Downloading {file_name}...")
                    response = requests.get(download_url, headers=self.ghHeaders)
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
                response = requests.get(dir_url, headers=self.ghHeaders)
                if response.status_code == 200:
                    sub_files = response.json()
                    sub_dir = os.path.join(output_dir, dir_name)
                    self._git_pull(sub_files, sub_dir)
                else:
                    print(f"Failed to access directory {dir_name}. HTTP {response.status_code}")

    def _dkDelImage(self):
        res = Executer.run_cmd(f'docker rmi --force {self.dockerName}:latest')
        if res.returncode != 0:
            log.error(f'Failed to delete old Docker image: {res.stderr}')
            raise ExecuterError(res)

    def _dkDelContainer(self):
        res = Executer.run_cmd(f'docker stop {self.dockerName}')
        if res.returncode != 0:
            log.warning(f'Docker stop container error: {res.stderr}', exc_info=True)
        res = Executer.run_cmd(f'docker rm {self.dockerName}')
        if res.returncode != 0:
            log.warning(f'Docker remove container error: {res.stderr}', exc_info=True)

    # Constructors
    def __loadWithHash(self, hash, user):
        try:
            relPath = base64.b64decode(hash).decode()
        except Exception as e:
            raise ValueError("Hash of repository incorrect", str(e))
        path = os.path.join(self.DB_DIR, 'repos', user.username, relPath, 'info.json')
        if not os.path.exists(path):
            raise ValueError("Repository with such hash not found")
        self._load_attrs(path)

    def __init__(self, initMethod: str, ghAccess_token: str = None, branch: str = 'default', ports: list = [0, 0], user = None):
        if not initMethod: raise ValueError("initMethod parameter is required")
        if not '/' in initMethod:
            return self.__loadWithHash(initMethod, user)

        if not ghAccess_token: raise ValueError("Access_token is required")
        self.ghHeaders = { "Authorization": f"token {ghAccess_token}" }
        self.projectOwner = user.username

        if not self._isRepoExists(initMethod): raise ValueError("GitHub repository not found")
        if not self._isBranchValid(branch): raise ValueError("The GitHub repository does not have such a branch")
        self.name = (self.repoFullName + '.' + self.branch).replace('/', '.')
        self.dirPath = os.path.join(user.userFolderPath, self.name)
        if not self._isDockerfileExists(): raise ValueError("Path to Dockerfile is not specified or invalid")
        self.dockerName = self.name.lower()
        self.ports = ports

        if os.path.exists(self.dirPath): shutil.rmtree(self.dirPath)
        os.mkdir(self.dirPath)

    def __del__(self):
        # Saving project data before destruction
        if hasattr(self, 'isDeleted'): return
        dataObj = {
            'docker': {
                'imageName': self.name,
                'rootPath': self.dkfilePath,
                'buildCommand': f'docker build -t {self.name}:latest {self.name} --no-cache',
                'containerStatus': 'offline',
                'runCommand': f'docker run --name {self.name} -d -p {self.ports[0]}:${self.ports[1]} ${self.name}:latest'
            }
        }
        attrs = self.__dict__
        dataObj.update({ 'attrs': attrs })
        path = os.path.join(self.dirPath, 'info.json')
        JsonEditor.overwrite(path, dataObj)

    def getHash(self):
        """
        `name` -> hash\n
        Example: InvalidObject.Second-PC-Server.main -> hash
        """
        if not hasattr(self, "hash") or not self.hash:
            self.hash = base64.b64encode(self.name.encode()).decode()
        return self.hash

    def download(self):
        reqUrl = f'{self.url}/contents/?ref={self.branch}'
        log.info(f'Downloading repository contents from {reqUrl}')
        res = requests.get(reqUrl, headers=self.ghHeaders)
        if res.status_code != 200:
            log.error(f'Failed to fetch repository contents: {res.json()["message"]}')
            raise ApiResponseError(res)
        files = res.json()
        srcPath = os.path.join(self.dirPath, 'src')
        self._git_pull(files, srcPath)
        log.info(f'Repository {self.repoFullName} downloaded successfully.')

    def delete(self):
        log.info(f'Removing project ({self.name}) from docker')
        self._dkDelContainer()
        self._dkDelImage()
        log.info(f'Deleting project ({self.name})...')
        shutil.rmtree(self.dirPath, True)
        self.isDeleted = True # for __del__ method
        log.info(f'Project ({self.name}) deleted.')

    def build(self):
        self._dkDelImage()
        log.info(f'Starting Docker image build for {self.dockerName}')
        dkfileFullPath = os.path.join(self.dirPath, 'src', self.dkfilePath)
        runCommand = f'docker build -t {self.dockerName}:latest -f {dkfileFullPath} {self.dirPath}/src --no-cache'
        res = Executer.run_cmd(runCommand)
        if res.returncode != 0:
            log.error(f'Failed to build Docker image: {res.stderr}')
            raise ExecuterError(res)
        log.info(f'Docker image {self.dockerName} built successfully.')

    def run(self):
        self._dkDelContainer()
        log.info(f'Starting container for {self.name}')
        runCommand = f'docker run --name {self.dockerName} -d -p {self.ports[0]}:{self.ports[1]} {self.dockerName}:latest'
        res = Executer.run_cmd(runCommand)
        if res.returncode != 0:
            log.error(f'Failed to start Docker container: {res.stderr}')
            raise ExecuterError(res)
        log.info(f'Container {self.name} started successfully.')


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
        print(fileData)
        fileData[self.username] = self.userObj
        JsonEditor.overwrite(self.USERS_FILE_PATH, fileData)
        if len(os.listdir(self.userFolderPath)) < 1:
            os.rmdir(self.userFolderPath)

    def newProject(self, urlOrHash: str, ghAccess_token, **kwargs) -> Repo:
        """
        Returns created project
        """
        repo = Repo(urlOrHash, ghAccess_token, user=self, **kwargs)
        project = {
            'name': repo.repoFullName,
            'branch': repo.branch,
            'hash': repo.getHash()
        }
        self.userObj['projects'][repo.repoName] = project
        return repo

    def loadProject(self, hash: str) -> Repo:
        return Repo(hash, user=self)

    def deleteProject(self, hash: str):
        """
        Returns projectName
        """
        repo = Repo(hash, user=self)
        repoName = repo.repoFullName
        repo.delete()
        del self.userObj['projects'][repo.repoName]
        return repoName

    def getProjects(self) -> dict | None:
        """
        Returns dict or None if project list emty
        """
        projects = self.userObj['projects']
        if len(projects) > 0:
            return projects
        else: return None


class CloudflareController(BaseController):
    def __init__(self):
        self.FLARE_FILE_PATH = os.path.join(self.CURRENT_DIR, 'db', 'cloudflare.json')
        self.FLARE_YAMLS_FOLDER_PATH = os.path.join(self.CURRENT_DIR, 'db', 'tunnels')
        if not os.path.exists(self.FLARE_FILE_PATH):
            with open(self.FLARE_FILE_PATH, 'w') as file:
                file.write('{}')
            pass
        if not os.path.exists(self.FLARE_YAMLS_FOLDER_PATH): os.mkdir(self.FLARE_YAMLS_FOLDER_PATH)

    def addAccout(self, api_token: str) -> None | str:
        """
        Return str if error occured
        """
        saveData = JsonEditor.read(self.FLARE_FILE_PATH)
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        res = requests.get('https://api.cloudflare.com/client/v4/accounts', headers=headers)
        if res.status_code != 200: return res.text
        account = res.json()['result'][0]
        saveData['account'] = {
            'id': account['id'],
            'name': account['name'],
            'api_token': api_token
        }
        res = requests.get('https://api.cloudflare.com/client/v4/zones', headers=headers)
        print(res.json())
        if res.status_code != 200: return res.text
        zones = res.json()['result']
        saveData['zones'] = {}
        for zone in zones:
            saveData['zones'][zone['name']] = {
                'name': zone['name'],
                'status': zone['status'],
                'id': zone['id']
            }
        JsonEditor.overwrite(self.FLARE_FILE_PATH, saveData)

    def getAccount(self) -> dict | str:
        """
        Returns str if error occured
        """
        data = JsonEditor.read(self.ACCOUNTS_JSON_PATH)
        if not data.get('account'): return 'account has not been added yet'
        accountData = data['account']
        return accountData

    def _generate_tunnel_yaml(self, tunnel: dict, tunnelFolderPath: str):
        tunnel_obj = {
            'tunnel': tunnel['id'],
            'credentials-file': os.path.join(tunnelFolderPath, 'credentials.json'),
            'ingress': [
                {
                    'hostname': tunnel['hostname'],
                    'service': tunnel['service']
                },
                {
                    'service': 'http_status:404'
                }
            ]
        }
        yaml_file_path = os.path.join(tunnelFolderPath, 'config.yaml')
        with open(yaml_file_path, 'w') as file:
            yaml.dump(tunnel_obj, file, default_flow_style=False)

    def createTunnel(self, tunnelName: str, localPort: str, domain: str = None) -> None | str:
        """
        Return str if error occured
        """
        flareData = JsonEditor.read(self.FLARE_FILE_PATH)
        if not flareData['account']: return "you don't have account"
        if len(flareData['zones']) < 1: return "you don't have registered domains"
        if not domain: domain = next(iter(flareData['zones']))
        if not flareData['zones'][domain]: return f'your account does not own the {tunnelName} domain'
        headers = {
            'Authorization': f'Bearer {flareData['account']['api_token']}',
            'Content-Type': 'application/json'
        }
        hostname = f'{tunnelName}.{domain}'
        service = f'http://192.168.1.159:{localPort}'
        payload = {
            'name': tunnelName,
            'config_src': 'local'
        }
        res = requests.post(f'https://api.cloudflare.com/client/v4/accounts/{flareData['account']['id']}/cfd_tunnel', headers=headers, data=json.dumps(payload))
        print(res.json())
        if res.status_code != 200: return res.text
        res = res.json()['result']
        os.mkdir(os.path.join(self.FLARE_YAMLS_FOLDER_PATH, tunnelName))
        credentials_data = res['credentials_file']
        tunnelFolderPath = os.path.join(self.CURRENT_DIR, 'db', 'tunnels', tunnelName)
        credentials_file_path = os.path.join(tunnelFolderPath, 'credentials.json')
        JsonEditor.overwrite(credentials_file_path, credentials_data)
        tunnel = {
            'name': tunnelName,
            'id': res['id'],
            'service': service,
            'hostname': hostname,
            'dns_record_id': None,
            'zone': domain
        }
        if not flareData.get('tunnels'): flareData['tunnels'] = {}
        flareData['tunnels'][tunnelName] = tunnel
        JsonEditor.overwrite(self.FLARE_FILE_PATH, flareData)
        self._generate_tunnel_yaml(tunnel, os.path.normpath(tunnelFolderPath))
        data = {
            'type': 'CNAME',
            'name': hostname,
            'content': f'{tunnel['id']}.cfargotunnel.com',
            'ttl': 1,
            'proxied': True
        }
        res = requests.post(f'https://api.cloudflare.com/client/v4/zones/{flareData['zones'][domain]['id']}/dns_records', headers=headers, data=json.dumps(data))
        print(res.json())
        if res.status_code != 200: return res.text()
        res = res.json()['result']
        flareData['tunnels'][tunnelName]['dns_record_id'] = res['id']

    def deleteTunnel(self, tunnelName: str) -> None | str:
        flareData = JsonEditor.read(self.FLARE_FILE_PATH)
        tunnel_id = flareData['tunnels'][tunnelName]['id']
        headers = {
            'Authorization': f'Bearer {flareData['account']['api_token']}',
            'Content-Type': 'application/json'
        }
        res = requests.delete(f'https://api.cloudflare.com/client/v4/accounts/{flareData['account']['id']}/tunnels/{tunnel_id}/connections', headers=headers)
        print(res.json())
        if res.status_code != 200: return res.text
        res = requests.delete(f'https://api.cloudflare.com/client/v4/accounts/{flareData['account']['id']}/tunnels/{tunnel_id}', headers=headers)
        print(res.json())
        if res.status_code != 200: return res.text
        try:
            zone_id = flareData['zones'][flareData['tunnels'][tunnelName]['zone']]['id']
            dns_record_id = flareData['tunnels'][tunnelName]['dns_record_id']
            res = requests.delete(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{dns_record_id}', headers=headers)
        except: pass
        tunnelFolderPath = os.path.join(self.FLARE_YAMLS_FOLDER_PATH, tunnelName)
        if os.path.exists(tunnelFolderPath): shutil.rmtree(tunnelFolderPath)
        if flareData.get('tunnels') and flareData['tunnels'].get(tunnelName): del flareData['tunnels'][tunnelName]
        JsonEditor.overwrite(self.FLARE_FILE_PATH, flareData)
