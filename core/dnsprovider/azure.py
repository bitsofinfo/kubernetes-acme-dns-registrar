
from lib2to3.pytree import Base
from azure.mgmt.dns import DnsManagementClient
from azure.mgmt.dns.models import RecordSet
from azure.mgmt.privatedns import PrivateDnsManagementClient
from azure.identity import ClientSecretCredential

from ..models import *
from queue import Queue
from ..store import RegistrationStore
from threading import Thread
import simplejson
from ..logging import LogService
from re import Pattern
import re
from ..settings import SmartSettings
from ..utils import *
from . import DnsProvider, EnsureCNAMEResult
from abc import ABC, abstractmethod
import sys
class DnsProviderSettings(SmartSettings):
    KADR_DNS_PROVIDER_CONFIG_YAML:str
    KADR_DNS_PROVIDER_SECRETS_YAML:str

class BaseAzureDnsProvider(DnsProvider):

    def __init__(self):

        # we are only enabled if we have an entry in the dns-provider config YAML we load
        self.enabled = False

        self.logger = LogService(f"BaseAzureDnsProvider {self.get_dns_provider_name()}").logger

        self.init_config()

        if self.is_enabled():
            self.init_dns_client()
    
    def init_config(self):
        self.settings = DnsProviderSettings()

        all_dns_provider_configs = self.settings.get_from_yaml("KADR_DNS_PROVIDER_CONFIG_YAML")["dns_providers"]

        # not enabled
        if self.get_dns_provider_name() not in all_dns_provider_configs:
            self.enabled = False
            return

        self.logger.debug(f"AzureDnsProvider {self.get_dns_provider_name()} enabled")
        self.enabled = True

        self.dns_provider_config = all_dns_provider_configs[self.get_dns_provider_name()]
        dns_provider_secrets =self.settings.get_from_yaml("KADR_DNS_PROVIDER_SECRETS_YAML")["dns_providers"][self.get_dns_provider_name()]
   
        # merge them
        self.dns_provider_config.update(dns_provider_secrets)

        # copy all common settings into each zone level config (only if not overridden)
        for zone,zone_config in self.dns_provider_config["zones"].items():
            if "client_secret" not in zone_config:
                zone_config["client_secret"] = self.dns_provider_config["client_secret"]
            if "client_id" not in zone_config:
                zone_config["client_id"] = self.dns_provider_config["client_id"]
            if "tenant_id" not in zone_config:
                zone_config["tenant_id"] = self.dns_provider_config["tenant_id"]
            if "subscription_id" not in zone_config:
                zone_config["subscription_id"] = self.dns_provider_config["subscription_id"]

        self.zone_configs = self.dns_provider_config["zones"]

        re_compile_patterns(self.zone_configs,["includes","excludes"])

        self.credentials = ClientSecretCredential(
            tenant_id=self.dns_provider_config["tenant_id"],
            client_id=self.dns_provider_config["client_id"],
            client_secret=self.dns_provider_config["client_secret"]
        )

        self.subscription_id = self.dns_provider_config["subscription_id"]

    def get_zone_config(self, domain_name):
        return find_config(self.zone_configs, domain_name)

    @abstractmethod
    def init_dns_client(self):
        pass

    @abstractmethod
    def get_azure_dns_client_instance(self):
        pass

    @abstractmethod
    def get_zone_name_param_name(self) -> str:
        pass

    def is_enabled(self) -> bool:
        return self.enabled

    def get_record_set_params(self, name, cname_target, relative_record_set_name:str, zone_config:dict):
        return { 
                "resource_group_name": zone_config["resource_group_name"], 
                self.get_zone_name_param_name(): zone_config["zone_name"], 
                "relative_record_set_name": relative_record_set_name, 
                "record_type": "CNAME",

                # https://docs.microsoft.com/en-us/python/api/azure-mgmt-dns/azure.mgmt.dns.v2018_05_01.models.recordset?view=azure-python
                "parameters": {
                    "ttl": zone_config["ttl"],
                    "cname_record": { 
                        "cname": cname_target 
                    },
                    "metadata":{
                        "domain_name":name,
                        "created_by":"kubernetes-acme-dns-registrar",
                        "source_system": "k8s"
                    }
                }  
            }

    def ensure_cname_for_acme_dns(self, name: str, cname_target: str) -> EnsureCNAMEResult:

        if not self.is_enabled():
            raise Exception(f"ensure_cname_for_acme_dns() {self.get_dns_provider_name()} misconfiguration, I am not enabled, yet i was invoked!")

        try:
            self.logger.debug(f"ensure_cname_for_acme_dns() {self.get_dns_provider_name()} processing {name} -> {cname_target}")

            zone_config = self.get_zone_config(name)
            
            if not zone_config:
                raise Exception(f"get_zone_config() no zone_config found for: {name}")

            # strip the zone out of the name plus any wildcard...
            relative_record_set_name = get_relative_recordset_name(name,zone_config["zone_name"])
            
            # https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/network/azure-mgmt-dns/azure/mgmt/dns/v2018_05_01/models/_models_py3.py#L288
            record_set_params = self.get_record_set_params(name,cname_target,relative_record_set_name,zone_config)
            record_set:RecordSet = self.get_azure_dns_client_instance().record_sets.create_or_update(**record_set_params)

            return EnsureCNAMEResult(dns_cname_id=record_set.id, \
                                    dns_cname_provider=self.get_dns_provider_name(), \
                                    dns_cname_record=record_set.as_dict(), \
                                    dns_cname_updated_at=datetime.utcnow())

        except Exception as e:
            self.logger.exception(f"AzureDnsProvider().ensure_cname_for_acme_dns() unexpected error: {str(sys.exc_info()[:2])}")



