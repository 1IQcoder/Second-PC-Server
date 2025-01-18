import subprocess, json, os
import logging as log
from git import Repo    # pip install GitPython
from src.config import BASE_DIR

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
    def run_cmd(command: str) -> tuple[bool, str]:
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

    @staticmethod
    def run_batch(scriptName: str, *args) -> tuple[bool, str]:
        """
        Executes a bat file with the ability to pass parameters.
        
        bat_file: Name of .bat file
        args: Parameters to be passed to the bat file
        Return: tuple (exit code, error text or None)
        """
        scriptPath = os.path.join(BASE_DIR, 'bats', scriptName)
        try:
            command = [scriptPath, *args]
            result = subprocess.run(command, shell=True, text=True, capture_output=True)
            
            if result.returncode != 0:
                return False, result.stderr
            return True, None
        except Exception as e:
            return False, str(e)


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


class JsonEditor():
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


class BaseController():
    CURRENT_DIR = BASE_DIR
    REPOS_DIR = os.path.join(CURRENT_DIR, 'db', 'repos')
    ACCOUNTS_JSON_PATH = os.path.join(CURRENT_DIR, 'db', 'accounts.json')
    DELETE_REPO_BAT = os.path.join(CURRENT_DIR, 'bats', 'delete_repo.bat')

    def __init__(self):
        if not os.path.exists(self.REPOS_DIR): os.mkdir(self.REPOS_DIR)
        if not os.path.exists(self.ACCOUNTS_JSON_PATH):
            with open(self.ACCOUNTS_JSON_PATH, "w") as file:
                file.write('{}')


class AccountsController(BaseController):
    """
    Methods for working with accounts.json
    """

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




