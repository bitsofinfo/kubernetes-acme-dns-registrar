from azure.mgmt.dns.models import RecordSet
from azure.mgmt.dns import DnsManagementClient
from azure.identity import ClientSecretCredential
from ..azure import BaseAzureDnsProvider


class DnsProvider(BaseAzureDnsProvider):

    def create_dns_client(self, credential:ClientSecretCredential, subscription_id) -> any:
        dns_client = DnsManagementClient(
            credential=credential,
            subscription_id=subscription_id,

            # https://docs.microsoft.com/en-us/azure/developer/python/sdk/azure-sdk-library-usage-patterns?view=azure-python&tabs=pip#optional-arguments-for-client-objects-and-methods
            kwargs={
                "connection_timeout":10,
                "read_timeout":30,
                "retry_total":10
            }
        )

        return dns_client

    def get_dns_provider_name(self) -> str:
        return "azuredns"

    def get_zone_name_param_name(self) -> str:
        return "zone_name"



