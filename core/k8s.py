
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from queue import Queue
from k8swatcher import K8sTrackedObject, K8sWatchEvent, K8sEventHandler
from .logging import LogService
import sys
from .models import *
from .settings import SmartSettings

class K8sSettings(SmartSettings):
    KADR_K8S_WATCHER_CONFIG_FILE_PATH:Optional[str]
    KADR_K8S_WATCHER_CONTEXT_NAME:Optional[str]

    KADR_K8S_ACMEDNS_SECRETS_STORE_CONFIG_FILE_PATH:Optional[str]
    KADR_K8S_ACMEDNS_SECRETS_STORE_CONTEXT_NAME:Optional[str]
class K8sKindHostExtractor(ABC):
    
    @abstractmethod
    def extract_hosts(self, k8s_object) -> List[str]:
        pass

class K8sIngressHostsExtractor(K8sKindHostExtractor):

    def extract_hosts(self, k8s_object) -> List[str]:
        # capture hosts from tls block
        hosts = []
        for tls in k8s_object["spec"]["tls"]:
            hosts.extend(tls["hosts"])
        return hosts


class DomainNameEventCreator(K8sEventHandler):

    def __init__(self, domain_name_event_queue:Queue):
        self.domain_name_event_queue = domain_name_event_queue
        self.hosts_extractor = K8sIngressHostsExtractor()
        self.logger = LogService("DomainNameEventCreator").logger

    async def handle_k8s_watch_event(self, k8s_watch_event:K8sWatchEvent):
        try:
            k8s_tracked_object:K8sTrackedObject = k8s_watch_event.k8s_tracked_object

            extracted_hosts = self.hosts_extractor.extract_hosts(k8s_tracked_object.k8s_object)

            k8s_watch_event_dict:dict = k8s_watch_event.dict()

            for host in extracted_hosts:
                self.domain_name_event_queue.put(DomainNameEvent(**{
                    "type": DomainNameEventType(k8s_watch_event.event_type),
                    "domain_name": host,
                    "source": "k8swatcher",
                    "source_data": k8s_watch_event_dict
                }))

        except Exception as e:
            self.logger.exception(f"DomainNameEventCreator().handle_k8s_watch_event() unexpected error: {str(sys.exc_info()[:2])}")
