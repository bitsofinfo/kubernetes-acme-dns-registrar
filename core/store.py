from abc import ABC, abstractmethod
from .models import *
from typing import List, Dict

class RegistrationStore(ABC):
    @abstractmethod
    def put_registration(self, registration:Registration) -> Registration:
        pass

    @abstractmethod
    def get_registration(self, cname_name:str) -> Registration:
        pass

    @abstractmethod
    def get_all(self) -> List[Dict[str,Registration]]:
        pass

    @abstractmethod
    def get_by_name(self,name) -> Registration:
        pass

class DictRegistrationStore(RegistrationStore):

    def __init__(self):
        self.store = {}

    async def get_all(self) -> List[Dict[str,Registration]]:
        return self.store

    async def get_by_name(self,name) -> Registration:
        if name in self.store:
            return self.store[name]
        return None

    def put_registration(self, registration:Registration) -> Registration:
        self.store[registration.cname_name] = registration

    def get_registration(self, cname_name:str) -> Registration:
        if cname_name in self.store:
            return self.store[cname_name]
        return None


