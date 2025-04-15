import json, subprocess, os, sys
import logging as log
from subprocess import CompletedProcess

def get_app_dir():
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(os.path.dirname(sys._MEIPASS))
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return app_dir

APP_DIR = get_app_dir()
DB_DIR = os.path.join(APP_DIR, 'db')
CLIENT_DIR = os.path.join(APP_DIR, 'client')

class AppDir:
    if not os.path.isdir(DB_DIR): os.mkdir(DB_DIR)

    CURRENT_DIR = APP_DIR
    DB_DIR = os.path.join(CURRENT_DIR, 'db')
    APPS_DIR = os.path.join(DB_DIR, 'apps')
    CF_CONFIG = os.path.join(DB_DIR, 'cloudflare.json')             # Cloudflare config (account data, zones list, tunnels data)

    @classmethod
    def create_db_folder(cls):
        print(cls.CURRENT_DIR)
        if not os.path.isdir(cls.DB_DIR): os.mkdir(cls.DB_DIR)

    @classmethod
    def new_app_dir(cls, app_name: str):
        if not os.path.isdir(cls.APPS_DIR): os.mkdir(cls.APPS_DIR)
        path = os.path.join(cls.APPS_DIR, app_name)
        if not os.path.isdir(path): os.mkdir(path)
        return path
    
    @classmethod
    def is_cf_ready(cls) -> bool:
        """
        Checks the cloudflare.json file for account and tunnel info
        """
        config = cls.cf_config()
        if not config.get('account', False) or not config.get('tunnel', False):
            return False
        return True


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
        scriptPath = os.path.join(APP_DIR, 'bats', scriptName)
        if not os.path.exists(scriptPath): raise ValueError("Bat file not found")
        command = [scriptPath, *args]
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        return result


class JsonEditor:
    @staticmethod
    def overwrite(jsonFilePath: str, dataToWrite: dict) -> None:
        dirPath = os.path.dirname(jsonFilePath)
        if not os.path.exists(dirPath): raise ValueError("json file not found in the specified directory")
        with open(jsonFilePath, 'w') as file:
            json.dump(dataToWrite, file, indent=4, ensure_ascii=False)
        log.info(f"Файл {jsonFilePath} успешно перезаписан.")

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
    
    @staticmethod
    def validate_file(file_path: str) -> bool:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                json.load(file)
            return True
        except (json.JSONDecodeError, FileNotFoundError, IOError):
            return False

    @staticmethod
    def check_file(path: str):
        if os.path.exists(path):
            return
        if path.endswith(os.sep) or "." not in os.path.basename(path):
            os.makedirs(path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as file:
                json.dump({}, file, indent=4, ensure_ascii=False)


class BaseJsonFile:
    """
    Usage for read: `data = config('account', 'id')`\n
    Usage for write: `config.set('account', 'id', value='734985984')`
    """

    FILE_PATH: str

    def __init__(self):
        JsonEditor.check_file(self.FILE_PATH)
        self.data = JsonEditor.read(self.FILE_PATH)

    def __call__(self, *args):
        for arg in args:
            if isinstance(self.data, dict) and arg in self.data:
                self.data = self.data[arg]
            else:
                return None
        return self.data

    def set(self, *args, value):
        if not args:
            return
        data = self.data
        for arg in args[:-1]:
            if arg not in data or not isinstance(data[arg], dict):
                data[arg] = {}
            data = data[arg]
        data[args[-1]] = value

    def save(self, obj: dict = None):
        print('Save method')
        print(obj)
        JsonEditor.overwrite(self.FILE_PATH, obj if obj else self.data)
        if obj: self.data = obj
        print(self.data)
