from .models import *
from queue import Queue
from .logging import LogService
from re import Pattern
import simplejson
import requests
from .store import RegistrationStore
from threading import Thread
import sys
import re
from re import Pattern
from .settings import SmartSettings
from .utils import *

class ACMEDnsSettings(SmartSettings):
    KADR_ACME_DNS_CONFIG_YAML:str

class ACMEDnsRegistrar(Thread):

    def __init__(self, registration_store:RegistrationStore, \
                       domain_name_event_queue:Queue, \
                       acme_dns_registration_queue:Queue, *args, **kwargs):
        kwargs.setdefault('daemon', True)
        super().__init__(*args, **kwargs)

        self.logger = LogService("ACMEDnsRegistrar").logger

        self.registration_store = registration_store
        self.domain_name_event_queue = domain_name_event_queue
        self.acme_dns_registration_queue = acme_dns_registration_queue

        self.init_configs()

    def init_configs(self):

        self.settings = ACMEDnsSettings()

        self.acme_dns_config = self.settings.get_from_yaml("KADR_ACME_DNS_CONFIG_YAML")
        self.zone_configs = self.acme_dns_config["zone_configs"]

        re_compile_patterns(self.zone_configs,["includes","excludes"])

    def any_pattern_matches(self, patterns:List[Pattern], value:str):
        if patterns and len(patterns) > 0:
            for p in patterns:
                if p.match(value):
                    return True

        return False


    def get_zone_config(self, domain_name) -> dict: 
        for conf_name, config in self.zone_configs.items():
            if self.any_pattern_matches(config["excludes"],domain_name):
                continue
            if self.any_pattern_matches(config["includes"],domain_name):
                return config

    def run(self):
        try:
           while True:
                domain_name_event:DomainNameEvent = self.domain_name_event_queue.get()

                print(simplejson.dumps(domain_name_event.dict(),indent=2, default=str))

                registration:Registration = \
                   self.registration_store.get_registration(domain_name_event.domain_name)

                if not registration:

                    zone_config = self.get_zone_config(domain_name_event.domain_name)

                    acme_dns_registration_url = zone_config["acme_dns_registration_url"]
                    acme_dns_registration_response = requests.post(zone_config["acme_dns_registration_url"], data=None)

                    acme_dns_registration:AcmeDnsRegistration = \
                            AcmeDnsRegistration(**acme_dns_registration_response.json())

                    registration = Registration(**{
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        
                        "acme_dns_registered_at": datetime.utcnow(),
                        "acme_dns_registration": acme_dns_registration,
                        "acme_dns_registration_url": acme_dns_registration_url,

                        "cname_name": domain_name_event.domain_name,
                        "cname_target_fulldomain": acme_dns_registration.fulldomain,
                        "cname_target_subdomain": acme_dns_registration.subdomain,

                        "source_domain_name_event": domain_name_event
                    })

                    self.registration_store.put_registration(registration)

                acme_dns_register_event:AcmeDnsRegistationEvent = \
                        AcmeDnsRegistationEvent(registration=registration)

                self.acme_dns_registration_queue.put(acme_dns_register_event)
            
        except Exception as e : 
            self.logger.exception(f"ACMEDnsRegistrar().run() unexpected error: {str(sys.exc_info()[:2])}")
        finally:
            pass