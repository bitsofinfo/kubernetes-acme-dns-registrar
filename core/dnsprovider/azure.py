
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

class DnsProviderSettings(SmartSettings):
    KADR_DNS_PROVIDER_CONFIG_YAML:str
    KADR_DNS_PROVIDER_SECRETS_YAML:str

class AzureDnsProvider(Thread):

    def __init__(self, registration_store:RegistrationStore, acme_dns_registration_queue:Queue, *args, **kwargs):
        kwargs.setdefault('daemon', True)
        super().__init__(*args, **kwargs)
        self.acme_dns_registration_queue = acme_dns_registration_queue
        self.registration_store = registration_store

        self.logger = LogService("AzureDnsProvider").logger

        self.init_config()

        # EXT
        # See above for details on creating different types of AAD credentials
        # 
        # - local dev cred
        self.ext_credentials = ClientSecretCredential(
            tenant_id=self.dns_provider_config["tenant_id"],
            client_id=self.dns_provider_config["client_id"],
            client_secret=self.dns_provider_config["client_secret"]
        )

        # Replace this with your subscription id
        self.subscription_id = self.dns_provider_config["subscription_id"]

        self.dns_client = DnsManagementClient(
            self.ext_credentials,
            self.subscription_id
        )


    def init_config(self):
        self.settings = DnsProviderSettings()

        self.dns_provider_config =self.settings.get_from_yaml("KADR_DNS_PROVIDER_CONFIG_YAML")["dns_providers"]["azuredns"]
        dns_provider_secrets =self.settings.get_from_yaml("KADR_DNS_PROVIDER_SECRETS_YAML")["dns_providers"]["azuredns"]

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

    def any_pattern_matches(self, patterns:List[Pattern], value:str):
        if patterns and len(patterns) > 0:
            for p in patterns:
                if p.match(value):
                    return True

        return False

    def get_zone_config(self, domain_name) -> dict: 
        for zone, zone_config in self.zone_configs.items():
            if self.any_pattern_matches(zone_config["excludes"],domain_name):
                continue
            if self.any_pattern_matches(zone_config["includes"],domain_name):
                return zone_config

    def run(self):
        try:
           while True:
                acme_dns_registration_event:AcmeDnsRegistationEvent = self.acme_dns_registration_queue.get()
                print(simplejson.dumps(acme_dns_registration_event.dict(),indent=2, default=str))
               
                domain_name = acme_dns_registration_event.registration.source_domain_name_event.domain_name

                registration:Registration = \
                   self.registration_store.get_registration(domain_name)

                if not registration:
                    raise Exception(f"get_registration() no Registration found for: {domain_name}")

                cname_name = acme_dns_registration_event.registration.cname_name

                zone_config = self.get_zone_config(acme_dns_registration_event.registration.cname_name)
                
                if not zone_config:
                    raise Exception(f"get_zone_config() no zone_config found for: {cname_name}")

                # strip the zone out of the name plus any wildcard...
                relative_record_set_name = f"_acme-challenge.{domain_name.replace('.'+zone_config['zone_name'],'').replace('*.','')}"

                # https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/network/azure-mgmt-dns/azure/mgmt/dns/v2018_05_01/models/_models_py3.py#L288
                record_set:RecordSet = self.dns_client.record_sets. \
                        create_or_update(resource_group_name=zone_config["resource_group_name"], \
                            zone_name=zone_config["zone_name"], \
                            relative_record_set_name=relative_record_set_name, \
                            record_type="CNAME",

                            # https://docs.microsoft.com/en-us/python/api/azure-mgmt-dns/azure.mgmt.dns.v2018_05_01.models.recordset?view=azure-python
                            parameters={
                                "ttl": zone_config["ttl"],
                                "cname_record": { 
                                    "cname": acme_dns_registration_event.registration.cname_target_fulldomain 
                                },
                                "metadata":{
                                    "domain_name":domain_name,
                                    "created_by":"kubernetes-acme-dns-registrar",
                                    "source_system": "k8s",
                                    "source_k8s_ingress": registration.source_domain_name_event.source_data["k8s_tracked_object"]["name"]
                                }
                            })

                registration.dns_cname_id = record_set.id
                registration.dns_cname_provider = "azure-dns"
                registration.dns_cname_record_json = simplejson.dumps(record_set.as_dict())
                registration.dns_cname_updated_at = datetime.utcnow()

                self.registration_store.put_registration(registration)

                print(simplejson.dumps(registration.dict(),default=str,indent=2))
        except: 
            self.logger.exception("AzureDnsProvider().run()")
        finally:
            pass




"""

from azure.mgmt.privatedns import PrivateDnsManagementClient

private_dns_client = PrivateDnsManagementClient(
	int_credentials,
	subscription_id
)


record_set = private_dns_client.record_sets.create_or_update(resource_group_name="my-rg", \
                        private_zone_name="int.zzzz.net", \
                        relative_record_set_name="_acme-challenge.ZZZ1", \
                        record_type="CNAME",

                        # https://docs.microsoft.com/en-us/python/api/azure-mgmt-dns/azure.mgmt.dns.v2018_05_01.models.recordset?view=azure-python
                        parameters={
                            "ttl": 300,
                            "cname_record": { 
                                "cname": "ZZZTARGET2222222.auth.zzzz.net"
                            },
                            "metadata":{
                                "something":"whatever",
                                "otherthing":"whatever"
                            }
                        })



"""