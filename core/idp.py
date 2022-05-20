
from .logging import LogService
from .settings import SmartSettings
from .health import HealthcheckParticipant, HealthcheckResult
from .models import AuthorizedPrincipal
from abc import ABC, abstractmethod
from typing import Dict, Optional, Dict

import sys
import hashlib


class IdpService(ABC):
 
    @abstractmethod
    def get_authorized_principal(self, principal_id:str) -> AuthorizedPrincipal:
        pass

    @abstractmethod
    def authenticate_principal(self, principal_id:str, secret:str):
        pass


class AuthorizedPrincipalNotFoundError(Exception):
    def __init__(sel, principal_id, message):
        super().__init__(message)

class DefaultIdpSettings(SmartSettings):
    KADR_DEFAULT_IDP_PRINCIPAL_DB_CONFIG_YAML:str

"""
Default IDP service, is backed by a 
dictionary of principals/secrets
"""
class DefaultIdpService(IdpService):

    def __init__(self):
        self.settings = DefaultIdpSettings()

        self.principal_db = self.settings.get_from_yaml("KADR_DEFAULT_IDP_PRINCIPAL_DB_CONFIG_YAML")
        self.principals:dict = self.principal_db["principals"]

        self.hasher = hashlib.sha3_512()

        self.logger = LogService(__file__).logger



    async def get_authorized_principal(self, principal_id:str) -> AuthorizedPrincipal:

        if principal_id not in self.principals:
            raise AuthorizedPrincipalNotFoundError(principal_id, f"DefaultIdpService() principal not found: {principal_id}")

        return AuthorizedPrincipal(principal_id=principal_id)

    async def authenticate_principal(self, principal_id:str, secret:str):
        try:
            if principal_id and secret:
                
                if principal_id not in self.principals:
                    raise Exception("authenticate_principal() Invalid credentials: 001")

                principal = self.principals[principal_id]

                self.hasher.update(secret.strip().encode("utf8"))

                digest = self.hasher.hexdigest()

                if principal["secretHash"] != self.hasher.hexdigest():
                    raise Exception("authenticate_principal() Invalid credentials: 002")

                return True

            else:
                raise Exception("authenticate_principal() Invalid credentials: 000")

        except Exception as e:
            msg = f"authenticate_principal({principal_id}) error: {str(sys.exc_info()[:2])}"
            self.logger.exception(msg)
            raise Exception(msg)