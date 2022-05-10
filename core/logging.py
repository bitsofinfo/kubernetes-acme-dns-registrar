import logging
import sys


class LogService:

    def __init__(self, handle_name):
        logging.basicConfig()
        logging.root.setLevel(logging.WARN)
        self.handle = handle_name
        self.logger = logging.getLogger(self.handle)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.propagate = False
