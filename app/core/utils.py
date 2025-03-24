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

print(APP_DIR)
print(DB_DIR)

class AppDir:
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



