from azure.mgmt.dns.models import RecordSet
from azure.mgmt.privatedns import PrivateDnsManagementClient
from azure.identity import ClientSecretCredential
from ..azure import BaseAzureDnsProvider

class DnsProvider(BaseAzureDnsProvider):

    def init_dns_client(self) -> str:
        self.dns_client = PrivateDnsManagementClient(
            self.credentials,
            self.subscription_id
        )
        return self.dns_client

    def get_dns_provider_name(self) -> str:
        return "azureprivatedns"
 
    def get_azure_dns_client_instance(self):
        return self.dns_client

    def get_zone_name_param_name(self) -> str:
        return "private_zone_name"

