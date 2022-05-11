import yaml
from .acmedns import ACMEDnsRegistrar
from .k8s import DomainNameEventCreator, K8sSettings
from .models import *
from .store import *
from queue import Queue
from k8swatcher import K8sWatchConfig, K8sWatcherService
from .settings import SmartSettings
import json
from threading import Thread
from .logging import LogService
from .dnsprovider import DnsProvider, EnsureCNAMEResult
import json
import asyncio
import os
from pathlib import Path, PurePath
import importlib
class CNAMEServiceSettings(SmartSettings):
    KADR_K8S_WATCHER_CONFIG_YAML:str

class DnsProviderProcessor(Thread):

    def __init__(self, registration_store:RegistrationStore, \
                     acme_dns_registration_queue:Queue, *args, **kwargs):
        kwargs.setdefault('daemon', True)
        super().__init__(*args, **kwargs)

        self.acme_dns_registration_queue = acme_dns_registration_queue
        self.registration_store = registration_store

        self.logger = LogService("DnsProviderProcessor").logger

        self.dns_providers = self.load_dns_providers()

    def load_dns_providers(self):

        enabled_dns_providers = {}

        root_path = Path(os.path.dirname(os.path.realpath(__file__)))
        dns_providers_root_path = str(root_path.absolute()) + "/dnsprovider"

        for x in os.walk(dns_providers_root_path):
            dns_provider_dir_path = x[0]

            if dns_providers_root_path != dns_provider_dir_path and \
               '__pycache__' not in dns_provider_dir_path:

                dns_provider_dir_name = PurePath(dns_provider_dir_path).name

                # a module should exist for this DNS provider...
                dns_provider_module = importlib.import_module(f'.dnsprovider.{dns_provider_dir_name}', package=__name__)

                # construct the provider....
                dns_provider:DnsProvider = dns_provider_module.DnsProvider()

                if dns_provider.is_enabled():
                    enabled_dns_providers[dns_provider.get_dns_provider_name()] = dns_provider
                    self.logger.debug(f"load_dns_providers() registered DnsProvider: {dns_provider.get_dns_provider_name()}")

        return enabled_dns_providers

    def process_dns_registration_events(self):
        try:
            while True:
                acme_dns_registration_event:AcmeDnsRegistationEvent = self.acme_dns_registration_queue.get()

                domain_name = acme_dns_registration_event.registration.source_domain_name_event.domain_name

                registration:Registration = self.registration_store.get_registration(domain_name)

                if not registration:
                    raise Exception(f"get_registration() no Registration found for: {domain_name}")

                for provider_name, dns_provider in self.dns_providers.items():

                    self.logger.debug(f"process_dns_registration_events() -> {dns_provider.get_dns_provider_name()}")

                    ensure_cname_result:EnsureCNAMEResult = \
                                dns_provider.ensure_cname_for_acme_dns(\
                                    name=acme_dns_registration_event.registration.cname_name,
                                    cname_target=acme_dns_registration_event.registration.cname_target_fulldomain)
           
                    registration.dns_cname_id = ensure_cname_result.dns_cname_id
                    registration.dns_cname_provider = ensure_cname_result.dns_cname_provider
                    registration.dns_cname_record_json = json.dumps(ensure_cname_result.dns_cname_record.as_dict())
                    registration.dns_cname_updated_at = ensure_cname_result.dns_cname_updated_at

                    self.registration_store.put_registration(registration)

        except Exception as e:
            pass
        
    def run(self):
        self.logger.debug("DnsProviderProcessor() starting run of process_dns_registration_events()....")
        self.process_dns_registration_events()
               
class CNAMEService():

    def __init__(self):
        self.domain_name_event_queue:Queue = Queue()
        self.acme_dns_registration_queue:Queue = Queue()

        self.registration_store:RegistrationStore = DictRegistrationStore()

        self.init_configs()
        self.k8s_watcher_service = self.init_k8s_watcher_service()

        acme_dns_registrar = ACMEDnsRegistrar(registration_store=self.registration_store,\
                                                domain_name_event_queue=self.domain_name_event_queue, \
                                                acme_dns_registration_queue=self.acme_dns_registration_queue)

        dns_provider_processor = DnsProviderProcessor(registration_store=self.registration_store,\
                                                      acme_dns_registration_queue=self.acme_dns_registration_queue)

        acme_dns_registrar.start()
        dns_provider_processor.start()

        acme_dns_registrar.join()
        dns_provider_processor.join()

        self.k8s_watcher_service.join()

    def init_configs(self):

        self.settings = CNAMEServiceSettings()

        k8s_watcher_config =self.settings.get_from_yaml("KADR_K8S_WATCHER_CONFIG_YAML")

        self.k8s_watch_configs = []
        for wc in k8s_watcher_config['k8s_watch_configs']:
            self.k8s_watch_configs.append(K8sWatchConfig(**wc))

    def init_k8s_watcher_service(self):

        k8s_event_handler = DomainNameEventCreator(self.domain_name_event_queue)    

        k8s_settings = K8sSettings()

        return K8sWatcherService(k8s_config_file_path=k8s_settings.KADR_K8S_CONFIG_FILE_PATH,
                                 k8s_config_context_name=k8s_settings.KADR_K8S_CONTEXT_NAME) \
                                   .asyncio_watch(self.k8s_watch_configs, k8s_event_handler)
