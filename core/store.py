from abc import ABC, abstractmethod
from .models import *

class RegistrationStore(ABC):
    @abstractmethod
    def put_registration(self, registration:Registration) -> Registration:
        pass

    @abstractmethod
    def get_registration(self, cname_name:str) -> Registration:
        pass

class DictRegistrationStore(RegistrationStore):

    def __init__(self):
        self.store = {}

    def put_registration(self, registration:Registration) -> Registration:
        self.store[registration.cname_name] = registration

    def get_registration(self, cname_name:str) -> Registration:
        if cname_name in self.store:
            return self.store[cname_name]
        return None


