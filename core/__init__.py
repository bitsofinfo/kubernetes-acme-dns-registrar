import yaml
from .acmedns import ACMEDnsRegistrar
from .dnsprovider.azure import AzureDnsProvider
from .k8s import DomainNameEventCreator, K8sSettings
from .models import *
from .store import *
from queue import Queue
from k8swatcher import K8sWatchConfig, K8sWatcherService
from .settings import SmartSettings
import json

class CNAMEServiceSettings(SmartSettings):
    KADR_K8S_WATCHER_CONFIG_YAML:str


class CNAMEService():

    def __init__(self):
        self.domain_name_event_queue:Queue = Queue()
        self.acme_dns_registration_queue:Queue = Queue()

        self.registration_store:RegistrationStore = DictRegistrationStore()

        self.init_configs()
        self.k8s_watcher_service = self.init_k8s_watcher_service()

        domain_name_consumer = ACMEDnsRegistrar(registration_store=self.registration_store,domain_name_event_queue=self.domain_name_event_queue, acme_dns_registration_queue=self.acme_dns_registration_queue)
        dns_cname_provider_consumer = AzureDnsProvider(registration_store=self.registration_store,acme_dns_registration_queue=self.acme_dns_registration_queue)

        domain_name_consumer.start()
        dns_cname_provider_consumer.start()

        domain_name_consumer.join()
        dns_cname_provider_consumer.join()

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
