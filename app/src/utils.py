import json, subprocess, os
import logging as log
from subprocess import CompletedProcess
from src.config import BASE_DIR

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



