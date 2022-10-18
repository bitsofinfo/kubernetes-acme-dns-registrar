
from .. import BaseDnsProvider, DnsProvider, DnsProviderSettings
import sys
from .. import EnsureCNAMEResult
import CloudFlare

from .. import *

class DnsProvider(BaseDnsProvider):

    def post_config_init(self):

        self.zone_clients = {}
        for zone_name in self.zone_configs.keys():
            zone_config = self.zone_configs[zone_name]
            self.zone_clients[zone_name] = CloudFlare.CloudFlare(token=zone_config["api_token"],debug=False)
            self.logger.debug(f"post_config_init() {self.get_dns_provider_name()} configured CloudFlare client for zone {zone_name}")

    def get_overridable_prop_names(self):
        return ["zone_id","api_token"]

    def is_enabled(self) -> bool:
        return self.enabled
    
    def get_dns_provider_name(self) -> str:
        return "cloudflare"

    def ensure_cname_for_acme_dns(self, name:str, cname_target:str) -> EnsureCNAMEResult:

        if not self.is_enabled():
            raise Exception(f"ensure_cname_for_acme_dns() {self.get_dns_provider_name()} misconfiguration, I am not enabled, yet i was invoked!")

        try:
            zone_config = self.get_zone_config(name)
            cf_zone_id = zone_config["zone_id"]
            cf_zone_name = zone_config["zone_name"]
            
            if not zone_config:
                raise Exception(f"{self.get_dns_provider_name()} get_zone_config() no zone_config found for: {name}")

            # strip the zone out of the name plus any wildcard...
            relative_record_set_name = get_relative_recordset_name(name,cf_zone_name)
            
            zone_client = self.zone_clients[cf_zone_name]

            if not zone_client:
                raise Exception(f"ensure_cname_for_acme_dns() {self.get_dns_provider_name()} no zone_client found for: {name}")


            # POST to cloudflare
            result = None
            try:
                result = zone_client.zones.dns_records.post(cf_zone_id,data={'name': relative_record_set_name, 'type':'CNAME', 'content':cname_target, 'ttl':300})

            except Exception as e:
                
                # An A, AAAA, or CNAME record with that host already exists.
                if e.evalue.code == 81053:
                    self.logger.debug(f"ensure_cname_for_acme_dns() {self.get_dns_provider_name()} CNAME record already exists")
                    result = zone_client.zones.dns_records.get(identifier1=cf_zone_id,params={'name': f"{relative_record_set_name}.{cf_zone_name}", 'type':'CNAME'})
                    if len(result) != 0:
                        result = result[0]    
                        if result["content"] != cname_target:
                            self.logger.debug(f"ensure_cname_for_acme_dns() {self.get_dns_provider_name()} EXISTING CNAME points to an out of date target, OLD:{result['content']}, id={result['id']}, NEW:{cname_target}.. deleting old id={result['id']} and replacing w/ new...")

                            # delete old
                            result = zone_client.zones.dns_records.delete(cf_zone_id,result["id"])

                            # create new
                            result = zone_client.zones.dns_records.post(cf_zone_id,data={'name': relative_record_set_name, 'type':'CNAME', 'content':cname_target, 'ttl':300})

                else:
                    raise e

            self.logger.debug(f"ensure_cname_for_acme_dns() {self.get_dns_provider_name()} processed {name} ({relative_record_set_name}) -> {cname_target}")

            return EnsureCNAMEResult(dns_cname_id=result["id"], \
                                    dns_cname_provider=self.get_dns_provider_name(), \
                                    dns_cname_record=result, \
                                    dns_cname_updated_at=datetime.utcnow())

        except Exception as e:
            self.logger.exception(f"ensure_cname_for_acme_dns() {self.get_dns_provider_name()} unexpected error: {str(sys.exc_info()[:2])}")






