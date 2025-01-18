import logging

class CustomLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET, socketIO=None):
        super().__init__(name, level)
        self.socketIO = socketIO

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, forClient=False, **kwargs):
        if forClient:
            print(msg)
            self.socketIO.emit('log', msg)
        
        super()._log(level, msg, args, exc_info, extra, stack_info, **kwargs)

def setup_logger(name, socketIO):
    logging.setLoggerClass(CustomLogger)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.socketIO = socketIO

    # Форматирование логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый хендлер
    file_handler = logging.FileHandler('app.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
