import json

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