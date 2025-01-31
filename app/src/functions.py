import subprocess, json, os, requests, yaml, shutil
from subprocess import CompletedProcess
import logging as log
from git import Repo    # pip install GitPython
# from src.config import BASE_DIR
BASE_DIR = r'D:\\sklad\\txt\\SecondPC-server\\app'

class ApiResponseError(Exception):
    def __init__(self, message, requestUrl='-', status_code='-'):
        super().__init__(message)
        self.message = message
        self.requestUrl = requestUrl
        self.status_code = status_code

    def __str__(self):
        return (
            f"ApiResponseError: {self.message} \n"
            f"(URL: {self.requestUrl}, Status Code: {self.status_code})"
        )

    def __repr__(self):
        return (
            f"ApiResponseError(message={self.message!r}, \n"
            f"requestUrl={self.requestUrl!r}, status_code={self.status_code!r})"
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


def run_command(command) -> tuple[bool, str]:
    print(f'run command: {command}')
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            shell=isinstance(command, str)
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, f"Error: {result.stderr.strip()}"
    except Exception as e:
        return False, f"Exception: {str(e)}"


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
    class log:
        @staticmethod
        def info(msg):
            msgToSend = json.dumps({ 'type': 'info', 'msg': msg })
            yield f'data: {msgToSend} \n\n'

        @staticmethod
        def error(msg, closeConnection: bool):
            msgToSend = json.dumps({ 'type': 'error', 'msg': msg })
            yield f'data: {msgToSend} \n\n'
            if closeConnection:
                yield from SSEEvents.close()

    @staticmethod
    def sendJson(data: dict | str):
        if type(data) == dict: data = json.dumps(data)
        msgToSend = json.dumps({ 'type': 'json', 'data': data })
        yield f'data: {msgToSend} \n\n'

    @staticmethod
    def close(msg: str = None):
        data = { 'type': 'close' }
        if msg: data['msg'] = msg
        msgToSend = json.dumps(data)
        yield f'data: {msgToSend} \n\n'


class JsonEditor:
    @staticmethod
    def overwrite(file_path, data):
        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            print(f"Файл {file_path} успешно перезаписан.")
        except Exception as e:
            print(f"Ошибка при перезаписи файла: {e}")

    @staticmethod
    def read(file_path) -> dict | None:
        """
        Reads data from .json file

        Returns dictrionary or None if error occured
        """
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            return data
        except FileNotFoundError:
            print(f"Файл {file_path} не найден.")
            return None
        except json.JSONDecodeError:
            print(f"Файл {file_path} повреждён или не является JSON.")
            return None
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return None


class BaseController:
    CURRENT_DIR = BASE_DIR
    REPOS_DIR = os.path.join(CURRENT_DIR, 'db', 'repos')
    ACCOUNTS_JSON_PATH = os.path.join(CURRENT_DIR, 'db', 'accounts.json')
    DELETE_REPO_BAT = os.path.join(CURRENT_DIR, 'bats', 'delete_repo.bat')


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


class myRepo(BaseController):
    def _isUrlValid(self) -> bool:
        reqUrl = f'https://api.github.com/repos/{self.repoFullName}'
        res = requests.get(reqUrl, headers=self.ghHeaders)
        if res.status_code != 200:
            if res.status_code == 404:
                raise ValueError("Repository not found")

            if res.status_code == 401:
                raise ValueError("Bad credentials, GitHub access_token is bad")

            if res.json()['message'].startswith('API rate limit'):
                print('GitHub API rate limit, _isUrlValid skipping...')
                return True
            
            raise ApiResponseError(res.json()['message'], reqUrl, status_code=res.status_code)
        return True

    def _isBranchValid(self) -> bool:
        reqUrl = f'https://api.github.com/repos/{self.repoFullName}/branches'
        res = requests.get(reqUrl, headers=self.ghHeaders)
        if res.status_code != 200:
            if not res.json()['message'].startswith('API rate limit'):
                raise ApiResponseError(res.json()['message'], reqUrl, res.status_code)
            print('GitHub API rate limit, _isBranchValid skipping...')
            return True
        branches = res.json()
        for branch in branches:
            if branch['name'] == self.branch: return True
            if self.branch == 'main/master':
                if (branch['name'] == 'main') or (branch['name'] == 'master'): return True
        return False

    def _save_info_file(self, dataForFile: dict):
        JsonEditor.overwrite(os.path.join(self.repoDirPath, 'info.json'), dataForFile)

    def _write_info_file(self):
        self._mk_repo_dir()
        portsObj = [0, 0]  # 0 - locall port / 1 - docker port
        dataObj = {
            'url': self.url,
            'repoFullName': self.repoFullName,
            'ownerUsername': self.ownerUsername,
            'repoName': self.repoName,
            'name': self.name,
            'branch': self.branch,
            'isPrivate': self.private,
            'ghHeaders': {},
            'git': { 'isPulled': False, 'commitHash': 1 },
            'docker': {
                'imageName': self.dockerName,
                'rootPath': '/',
                'buildCommand': f'docker build -t {self.dockerName}:latest {self.dockerName} --no-cache',
                'isBuilded': False,
                'isRunning': False,
                'containerStatus': 'offline',
                'runCommand': f'docker run --name {self.dockerName} -d -p {portsObj[0]}:${portsObj[1]} ${self.dockerName}:latest'
            }
        }
        if self.private: dataObj['ghHeaders'] = self.ghHeaders
        attrs = self.__dict__
        dataObj.update({ 'attrs': attrs })
        self._save_info_file(dataObj)

    def _load_attrs(self, infoFilePath):
        infoData = JsonEditor.read(infoFilePath)
        attrs = ['url', 'branch', 'private', 'ghHeaders', 'repoFullName', 'repoName', 'ownerUsername', 'name', 'dockerName', 'userFolderPath', 'repoDirPath']
        for atr in attrs:
            setattr(self, atr, infoData['attrs'][atr])

    def _mk_repo_dir(self):
        """
        Makes dir for repository in 'db' folder like a "db/1IQcoder/1IQcoder.Second-PC-Server"\n
        Skips logic if repository dir already exists
        """
        if not os.path.isdir(self.userFolderPath): os.mkdir(self.userFolderPath)
        if not os.path.isdir(self.repoDirPath): os.mkdir(self.repoDirPath)

    def _download_files(self, file_list, output_dir):
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
                    self._download_files(sub_files, sub_dir)
                else:
                    print(f"Failed to access directory {dir_name}. HTTP {response.status_code}")

    # Constructors
    def __initWithUrl(self, url, branch = 'main/master', private = False, ports = [0, 0]):
        self.branch = branch
        self.repoFullName = ReposController.urlToFullName(url)
        self.ownerUsername = ReposController.urlToOwnerName(url)
        self.name = (self.repoFullName + '.' + self.branch).replace('/', '.')

        # загрузка существующего репозитория если он есть
        infoFilePath = os.path.join(self.REPOS_DIR, self.ownerUsername, self.name, 'info.json')
        if os.path.exists(infoFilePath):
            print('Repo already exists.')
            return self._load_attrs(infoFilePath)

        self.url = url
        self.private = private
        self.repoName = ReposController.urlToName(url)                              # Second-PC-Server
        self.dockerName = self.name.lower()                                         # 1iqcoder.second-pc-server.main
        self.userFolderPath = os.path.join(self.REPOS_DIR, self.ownerUsername)
        self.repoDirPath = os.path.join(self.userFolderPath, self.name)

        if not self._isUrlValid(): raise ValueError(f"GitHub repository not found")
        if not self._isBranchValid(): raise ValueError("The GitHub repository does not have such a branch")
        self._write_info_file()

    def __initWithName(self, infoFilePath):
        self._load_attrs(infoFilePath)

    def __init__(self, urlOrName: str, branch: str = 'main/master', private: bool = False, ghAccess_token: str = None, ports: list = [0, 0]):
        if not urlOrName: raise ValueError("urlOrName parameter is required")
        if private and not ghAccess_token: raise ValueError("Access_token is required for private repository")
        
        if ghAccess_token:
            self.ghHeaders = { "Authorization": f"token {ghAccess_token}" }

        if urlOrName.startswith('https://'):
            args = {k: v for k, v in locals().items() if k != 'self'}
            args['url'] = args.pop('urlOrName')
            args.pop('ghAccess_token')
            return self.__initWithUrl(**args)
        else:
            infoFilePath = os.path.join(self.REPOS_DIR, urlOrName, 'info.json')
            if not os.path.exists(infoFilePath):
                raise ValueError("Repository not exists")
            return self.__initWithName(infoFilePath)

    def download(self):
        reqUrl = f'https://api.github.com/repos/{self.repoFullName}/contents/'
        res = requests.get(reqUrl, headers=self.ghHeaders)
        if res.status_code != 200: raise ApiResponseError(res.json()['message'], reqUrl, res.status_code)
        files = res.json()
        self._mk_repo_dir()
        srcPath = os.path.join(self.repoDirPath, 'src')
        self._download_files(files, srcPath)

    def delete(self):
        shutil.rmtree(self.repoDirPath, True)
        # удаление папки юзера если она пуста
        self.userFolderPath = os.path.join(self.REPOS_DIR, self.ownerUsername)
        if len(os.listdir(self.userFolderPath)) < 1: os.rmdir(self.userFolderPath)

    def build(self):
        delImagesCommand = f'docker rmi --force {self.dockerName}:latest'
        res = Executer.run_cmd(delImagesCommand)
        if res.returncode != 0: raise ExecuterError(res)

        runCommand = f'docker build -t {self.dockerName}:latest {self.repoDirPath} --no-cache'
        res = Executer.run_cmd(runCommand)
        if res.returncode != 0: raise ExecuterError(res)

    def run(self):
        delContainerCommand = f'docker stop {self.dockerName} && docker rm {self.dockerName}'
        res = Executer.run_cmd(delContainerCommand)
        if res.returncode != 0: raise ExecuterError(res)

        runCommand = f'docker run --name {self.dockerName} -d -p {self.ports[0]}:{self.ports[1]} {self.dockerName}:latest'
        res = Executer.run_cmd(runCommand)
        if res.returncode != 0: raise ExecuterError(res)


class GitController(BaseController):
    def pullRepo(self, repo: dict | str) -> None | str:
        """
        Downloads files from branch of GitHub repository

        Parameters:
            repoObject (dict) or repoFullName (str)

        Return exception (str) if an errors occurs
        """
        repoName = ''
        if type(repo) == str:
            repoName = repo
        elif type(repo) == dict:
            repoName = repo['name']
        
        infoFilePath = os.path.join(self.REPOS_DIR, repoName, 'info.json')
        infoFile = JsonEditor.read(infoFilePath)
        repoSrcPath = os.path.join(self.REPOS_DIR, repoName, 'src')
        url = infoFile['url']
        branch = infoFile['branchName']
        commitHash  = ''

        try:
            if os.path.exists(repoSrcPath):
                repo = Repo(repoSrcPath)
                log.info(f"Starting repository update ({repoName}; {url})")
                origin = repo.remotes.origin
                origin.pull(branch)
                commitHash = repo.head.commit.hexsha
            else:
                log.info(f"Start cloning repository ({repoName}; {url})")
                Repo.clone_from(url, repoSrcPath, branch=branch)
                repo = Repo(repoSrcPath)
                commitHash = repo.head.commit.hexsha
        except Exception as e:
            log.error(f"Pulling repository error: {e}")
            return str(e)

        infoFile['git']['commitHash'] = commitHash
        JsonEditor.overwrite(infoFilePath, infoFile)
        log.info(f"Repository src files downloaded ({repoName}; {url})")


class DockerController(ReposController):
    def dockerBuild(self, repo: dict | str) -> None | str:
        """
        Executes docker image build command

        Parameters:
            repoObject (dict) or repoFullName (str)

        Return exception (str) if an errors occurs
        """
        repoName = ''
        if type(repo) == str:
            repoName = repo
        elif type(repo) == dict:
            repoName = repo['name']

        infoFilePath = os.path.join(self.REPOS_DIR, repoName, 'info.json')
        infoFile = JsonEditor.read(infoFilePath)
        imageName = infoFile['docker']['imageName']

        delImagesCommand = f'docker rmi --force {imageName}:latest'
        status, output = run_command(delImagesCommand)
        if not status:
            log.error(f"Error while deleting images with indentical name: {output}")
            # return f"Error while deleting images with indentical name: {output}"

        buildCommand = infoFile['docker']['buildCommand'] + ' ' + os.path.join(self.REPOS_DIR, repoName, 'src', infoFile['docker']['rootPath'])
        log.info(f"Start docker image building. repoName=({repoName}) command=({buildCommand})")

        status, output = run_command(buildCommand)

        if not status:
            log.error(f"Error while building image: {output}")
            return f"Error while building image: {output}"

        infoFile['docker']['containerStatus'] = 'offline'
        infoFile['docker']['isBuilded'] = True
        JsonEditor.overwrite(infoFilePath, infoFile)
        log.info(f"Docker image successfully built. repoName=({repoName})")

    def dockerRun(self, repo: dict | str) -> None | str:
        """
        Starts a docker container
        
        Parameters:
            repoObject (dict) or repoFullName (str)

        Return exception (str) if an errors occurs
        """
        repoName = ''
        if type(repo) == str:
            repoName = repo
        elif type(repo) == dict:
            repoName = repo['name']

        infoFilePath = os.path.join(self.REPOS_DIR, repoName, 'info.json')
        infoFile = JsonEditor.read(infoFilePath)
        imageName = infoFile['docker']['imageName']

        delContainersCommand = f'docker stop {imageName} && docker rm {imageName}'
        status, output = run_command(delContainersCommand)
        if not status:
            log.error(f"error deleting images with identical name. Output: {output}")
            # return f"error deleting images with identical name. Output: {output}"

        status, output = run_command(f'docker image inspect {imageName}')
        if not status:
            self.updateRepo(repoName, { "docker/isBuilded": False })
            log.error(f"No such image exists: repoName=({repoName}), command output: {output}")
            return f"No such image exists"
        
        status, output = run_command(infoFile['docker']['runCommand'])
        if not status:
            log.error(f"Container startup error: command failed. command output: {output}")
            return f"Container startup error: command failed. command output: {output}"
        log.info(f"Container started successfully. repoName=({repoName}) imageName=({imageName})")


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

# tunnels = CloudflareController()
# tunnels.addAccout('1PtYlwiQz_xCUIjOvVSuzwVyC0Qt5j05lzHVRMqq')
# tunnels.deleteTunnel('ivan-rak')
# tunnels.createTunnel('ivan-rak', '5173')

repo = myRepo('https://github.com/1IQcoder/Second-PC-Server.git')
# repo.download()
# repo.delete()
repo.build()
