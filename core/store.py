from abc import ABC, abstractmethod
from .models import *
from typing import List, Dict

import base64
from kubernetes import client, config
import json
from .logging import LogService
from .k8s import K8sSettings
import sys
from .settings import SmartSettings

class AcmeDnsK8sSecretStoreSettings(SmartSettings):
    KADR_ACME_DNS_CONFIG_YAML:str

class RegistrationStore(ABC):
    @abstractmethod
    def put_registration(self, registration:Registration) -> Registration:
        pass

    @abstractmethod
    def get_registration(self, cname_name:str) -> Registration:
        pass

    @abstractmethod
    def get_all(self) -> Dict[str,Registration]:
        pass

    @abstractmethod
    def get_by_name(self,name) -> Registration:
        pass

class DictRegistrationStore(RegistrationStore):

    def __init__(self):
        self.store = {}

    async def get_all(self) -> Dict[str,Registration]:
        return self.store

    async def get_by_name(self,name) -> Registration:
        if name in self.store:
            return self.store[name]
        return None

    def put_registration(self, registration:Registration) -> Registration:
        self.store[registration.cname_name] = registration

    def get_registration(self, cname_name:str) -> Registration:
        if cname_name in self.store:
            return self.store[cname_name]
        return None


class AcmeDnsK8sSecretStore():

    def __init__(self):

        self.logger = LogService("AcmeDnsK8sSecretStore").logger

        self.settings = AcmeDnsK8sSecretStoreSettings()

        # load the secret-meta-data location information
        acme_dns_config = self.settings.get_from_yaml("KADR_ACME_DNS_CONFIG_YAML")

        acme_dns_solver_config = acme_dns_config["acme-dns-solver"]
        self.secret_ref_name = acme_dns_solver_config["account_secret_ref"]["name"]
        self.secret_ref_key = acme_dns_solver_config["account_secret_ref"]["key"]
        self.secret_ref_namespace = acme_dns_solver_config["account_secret_ref"]["namespace"]

        self.logger.debug(f"AcmeDnsK8sSecretStore() managing cert-manager acmedns dns solver secret @ namespace={self.secret_ref_namespace} name={self.secret_ref_name} key={self.secret_ref_key}")
        
        # configure our kube client
        k8s_settings = K8sSettings()
        k8s_config_file_path = k8s_settings.get("KADR_K8S_ACMEDNS_SECRETS_STORE_CONFIG_FILE_PATH")
        k8s_config_context_name = k8s_settings.get("KADR_K8S_ACMEDNS_SECRETS_STORE_CONTEXT_NAME")
        
        try:
            self.logger.debug(f"AcmeDnsK8sSecretStore() loading kube config: k8s_config_file_path={k8s_config_file_path} k8s_config_context_name={k8s_config_context_name} (Note: 'None' = using defaults)")
            config.load_kube_config(config_file=k8s_config_file_path, context=k8s_config_context_name)
        except Exception as e:
            self.logger.debug(f"AcmeDnsK8sSecretStore() load_kube_config() failed, attempting load_incluster_config()....")
            config.load_incluster_config()
            self.logger.debug(f"AcmeDnsK8sSecretStore() load_incluster_config() OK!")

        self.k8s_v1client = client.CoreV1Api()
       
    async def get_acme_dns_registrations_k8s_secret(self) -> client.V1Secret:
            secret:client.V1Secret = self.k8s_v1client.read_namespaced_secret(self.secret_ref_name, self.secret_ref_namespace)
            if not secret:
                raise Exception(f"get_secret() nothing returned! {self.secret_ref_namespace}:{self.secret_ref_name}")
            return secret

    async def get_acme_dns_registrations_k8s_secret_data(self) -> dict:
        try:
            secret = self.get_acme_dns_registrations_k8s_secret()
            data_json = base64.b64decode(secret.data[self.secret_ref_key]).decode('utf-8')
            acme_dns_registrations = json.loads(data_json)
            return acme_dns_registrations

        except Exception as e:
            self.logger.exception(f"get_secret() unexpected error: {str(sys.exc_info()[:2])}")

    async def put_acme_dns_registrations_k8s_secret_data(self, acme_dns_registrations:dict):
        try:

            # get existing
            secret = await self.get_acme_dns_registrations_k8s_secret()
            metadata:client.V1ObjectMeta = secret.metadata
            annotations:dict = {}

            # modify annotations
            if 'kubernetes-acme-dns-registrar-version' not in metadata.annotations:
                annotations['kubernetes-acme-dns-registrar-version'] = "0"
            else:
                annotations['kubernetes-acme-dns-registrar-version'] = \
                    str(int(metadata.annotations['kubernetes-acme-dns-registrar-version']) + 1)

            annotations['kubernetes-acme-dns-registrar-last-update-at'] = datetime.utcnow().isoformat()

            acme_registrations_json_b64 = \
                    base64.encodebytes(json.dumps(acme_dns_registrations).encode('utf-8')).decode('utf-8')

            secret_body = {
                    "apiVersion": "v1",
                    "kind": "Secret",
                    "data": { self.secret_ref_key: acme_registrations_json_b64 },
                    "metadata": {
                        "annotations": annotations,
                        "name": self.secret_ref_name,
                        "namespace": self.secret_ref_namespace
                    },
                    "type": "Opaque"
                }


            result = self.k8s_v1client.patch_namespaced_secret(self.secret_ref_name,self.secret_ref_namespace,body=secret_body)
            self.logger.debug("put_acme_dns_registrations_k8s_secret_data() successfully PATCHed " + \
                f"k8s secret of acme-dns registartions for cert-manager @ {self.secret_ref_namespace}:{self.secret_ref_name}:{self.secret_ref_key}")

            data_json = base64.b64decode(secret.data[self.secret_ref_key]).decode('utf-8')
            acme_dns_registrations = json.loads(data_json)
            return acme_dns_registrations

        except Exception as e:
            self.logger.exception(f"put_acme_dns_registrations_k8s_secret_data() unexpected error: {str(sys.exc_info()[:2])}")

