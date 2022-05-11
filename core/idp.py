
from .logging import LogService
from .settings import SmartSettings
from .health import HealthcheckParticipant, HealthcheckResult
from .models import AuthorizedPrincipal
from abc import ABC, abstractmethod

logger = LogService(__file__).logger

class IdpService(ABC):
 
    @abstractmethod
    def get_authorized_principal(self, principal_id:str) -> AuthorizedPrincipal:
        pass

    @abstractmethod
    def authenticate_principal(self, principal_id:str, secret:str):
        pass


class AuthorizedPrincipalNotFoundError(Exception):
    pass
class IdpSettings(SmartSettings):
    TBD:str

class DefaultIdpService(IdpService):

    async def get_authorized_principal(self, principal_id:str) -> AuthorizedPrincipal:

        # raise AuthorizedPrincipalNotFoundError

        return AuthorizedPrincipal(principal_id=principal_id)

    async def authenticate_principal(self, principal_id:str, secret:str):
        try:
            if principal_id:
                return

            else:
                raise Exception("Invalid credentials")

        except Exception as e:
            msg = f"authenticate_principal({principal_id}) error: {e}"
            logger.error(msg)
            raise Exception(msg)