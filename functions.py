import subprocess, json, os
import logging as log
from git import Repo

def run_command(command):
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

# Пример использования
'''
success, output = run_command("ls -la" if subprocess.os.name != "nt" else "dir")
if success:
    print("Команда выполнена успешно:")
    print(output)
else:
    print("Произошла ошибка:")
    print(output)
'''

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
    def read(file_path):
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
    CURRENT_DIR = os.getcwd()
    REPOS_DIR = os.path.join(CURRENT_DIR, 'repos')
    ACCOUNTS_JSON_PATH = os.path.join(CURRENT_DIR, 'accounts.json')
    DELTE_REPO_BAT = os.path.join(CURRENT_DIR, 'bats', 'delete_repo.bat')


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

        try:
            result = subprocess.run(
                [self.DELTE_REPO_BAT, deleteFolder],
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
            2. valuesForUpdate (dict) example: { 'a': 46, 'j': 'pon' }

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

        status, output = run_command(f'docker image inspect {imageName}')
        if not status:
            log.error(f"No such image exists: repoName=({repoName}), command output: {output}")
            return f"No such image exists"
        status, output = run_command(infoFile['docker']['runCommand'])
        if not status:
            log.error(f"Container startup error: command failed. command output: {output}")
            return f"Container startup error: command failed. command output: {output}"
        log.info(f"Container started successfully. repoName=({repoName}) imageName=({imageName})")





