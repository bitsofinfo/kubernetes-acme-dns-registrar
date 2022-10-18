

from abc import ABC, abstractmethod

from ..settings import SmartSettings
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..logging import LogService

from ..utils import *

class DnsProviderSettings(SmartSettings):
    KADR_DNS_PROVIDER_CONFIG_YAML:str
    KADR_DNS_PROVIDER_SECRETS_YAML:str

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



class BaseDnsProvider(DnsProvider):

    def __init__(self):

        # we are only enabled if we have an entry in the dns-provider config YAML we load
        self.enabled = False

        self.logger = LogService(f"BaseDnsProvider {self.get_dns_provider_name()}").logger

        self.init_config()

        if self.enabled:
            self.post_config_init()

    
    def init_config(self):
        self.settings = DnsProviderSettings()

        all_dns_provider_configs = self.settings.get_from_yaml("KADR_DNS_PROVIDER_CONFIG_YAML")["dns_providers"]

        # not enabled
        if self.get_dns_provider_name() not in all_dns_provider_configs:
            self.enabled = False
            return

        self.dns_provider_config = all_dns_provider_configs[self.get_dns_provider_name()]

        if "enabled" in self.dns_provider_config and not self.dns_provider_config["enabled"]:
            self.enabled = False
            return

        self.logger.debug(f"BaseDnsProvider {self.get_dns_provider_name()} enabled")
        self.enabled = True

        dns_provider_secrets =self.settings.get_from_yaml("KADR_DNS_PROVIDER_SECRETS_YAML")["dns_providers"][self.get_dns_provider_name()]
   
        # merge them
        self.dns_provider_config.update(dns_provider_secrets)

        # copy all common settings into each zone level config (only if not overridden)
        for zone,zone_config in self.dns_provider_config["zones"].items():
            for overridable_prop_name in self.get_overridable_prop_names():
                if overridable_prop_name not in zone_config:
                    zone_config[overridable_prop_name] = self.dns_provider_config[overridable_prop_name]
           

        self.zone_configs = self.dns_provider_config["zones"]

        re_compile_patterns(self.zone_configs,["includes","excludes"])


    def get_zone_config(self, domain_name):
        return find_config(self.zone_configs, domain_name)
        
    @abstractmethod
    def get_overridable_prop_names(self):
        pass

    @abstractmethod
    def post_config_init(self):
        pass

