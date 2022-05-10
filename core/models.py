
from pydantic import BaseModel
import enum
from datetime import datetime
from typing import Optional, List, Any

class DomainNameEventType(str, enum.Enum):
    LOADED:str = "LOADED"
    ADDED:str = "ADDED"
    MODIFIED:str = "MODIFIED"
    DELETED:str = "DELETED"

    def __str__(self):
        return self.name

class DomainNameEvent(BaseModel):
    type:DomainNameEventType
    domain_name:str
    event_at:datetime = datetime.utcnow()
    source:str
    source_data:Optional[Any]

class AcmeDnsRegistration(BaseModel):
    username:str
    password:str
    fulldomain:str
    subdomain:str
    allowFrom:Optional[List[str]]

class Registration(BaseModel):
    created_at:datetime
    updated_at:datetime
    
    acme_dns_registered_at:datetime
    acme_dns_registration:AcmeDnsRegistration
    acme_dns_registration_url:str

    dns_cname_updated_at:Optional[datetime]
    dns_cname_id:Optional[str]
    dns_cname_provider:Optional[str]
    dns_cname_record_json:Optional[str]

    cname_name:str
    cname_target_fulldomain:str
    cname_target_subdomain:str

    source_domain_name_event:DomainNameEvent

class AcmeDnsRegistationEvent(BaseModel):
    event_at:datetime = datetime.utcnow()
    registration:Registration