

from abc import ABC, abstractmethod

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EnsureCNAMEResult(BaseModel):
    dns_cname_updated_at:Optional[datetime]
    dns_cname_id:Optional[str]
    dns_cname_provider:Optional[str]
    dns_cname_record:Optional[dict]

class DnsProvider(ABC):

    @abstractmethod
    def is_enabled(self) -> bool:
        pass
    
    @abstractmethod
    def get_dns_provider_name(self) -> str:
        pass

    @abstractmethod
    def ensure_cname_for_acme_dns(self, name:str, cname_target:str) -> EnsureCNAMEResult:
        pass

