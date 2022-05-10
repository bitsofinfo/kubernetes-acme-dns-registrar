from pydantic import BaseSettings
from typing import Optional, Dict, List
import os
import re
import yaml

class SmartSettings(BaseSettings):

    as_dict:Dict = None

    def __init__(self, **data):
        super().__init__(**data)
        self.as_dict = self.dict()

    def get_from_yaml(self, key) -> any:
        raw = self.get(key)
        return yaml.safe_load(raw)

    def get(self, key) -> any:    

        value = None

        # get from settings as you normally would
        if key in self.as_dict:
            value = self.as_dict[key]

        # if an file@ ref.. read it
        if value and value.startswith('file@'):
            file_path = value.replace('file@','')
            if os.path.exists(file_path) and os.path.isfile(file_path):
                with open(file_path,'r') as f:
                    return f.read().strip()

        # TODO: secret@ support?

        # TODO: {{}} jinja interpolation support?

        # literal... the value itself is the value
        elif value:
            return value.strip()

        else:
            return None

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
    