
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
from ..utils import *
from . import BaseDnsProvider, DnsProvider, DnsProviderSettings, EnsureCNAMEResult
from abc import ABC, abstractmethod
import sys

class BaseAzureDnsProvider(BaseDnsProvider):

    def post_config_init(self):

        if self.is_enabled():

            self.zone_clients = {}

            for zone_name in self.zone_configs.keys():
                zone_config = self.zone_configs[zone_name]

                subscription_id = zone_config["subscription_id"]

                zone_credential = ClientSecretCredential(
                                        tenant_id=zone_config["tenant_id"],
                                        client_id=zone_config["client_id"],
                                        client_secret=zone_config["client_secret"]
                                    )

                self.zone_clients[zone_name] = self.create_dns_client(zone_credential,subscription_id)

                self.logger.debug(f"post_config_init() {self.get_dns_provider_name()} configured Azure client for zone {zone_name}")


    def get_overridable_prop_names(self):
        return ["client_secret","client_id","tenant_id","subscription_id"]

    @abstractmethod
    def create_dns_client(self, credential:ClientSecretCredential, subscription_id) -> any:
        pass

    def get_azure_dns_client_instance(self, zone_name):
        return self.zone_clients[zone_name]

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
            zone_config = self.get_zone_config(name)
            
            if not zone_config:
                raise Exception(f"get_zone_config() no zone_config found for: {name}")

            # strip the zone out of the name plus any wildcard...
            relative_record_set_name = get_relative_recordset_name(name,zone_config["zone_name"])
            
            # https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/network/azure-mgmt-dns/azure/mgmt/dns/v2018_05_01/models/_models_py3.py#L288
            record_set_params = self.get_record_set_params(name,cname_target,relative_record_set_name,zone_config)
            record_set:RecordSet = self.get_azure_dns_client_instance(zone_config["zone_name"]).record_sets.create_or_update(**record_set_params)

            self.logger.debug(f"ensure_cname_for_acme_dns() {self.get_dns_provider_name()} processed {name} ({relative_record_set_name}) -> {cname_target}")

            return EnsureCNAMEResult(dns_cname_id=record_set.id, \
                                    dns_cname_provider=self.get_dns_provider_name(), \
                                    dns_cname_record=record_set.as_dict(), \
                                    dns_cname_updated_at=datetime.utcnow())

        except Exception as e:
            self.logger.exception(f"AzureDnsProvider().ensure_cname_for_acme_dns() unexpected error: {str(sys.exc_info()[:2])}")



