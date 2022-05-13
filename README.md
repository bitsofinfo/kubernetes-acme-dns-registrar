# kubernetes-acme-dns-registrar <!-- omit in TOC -->

Watches k8s resources (ingress objects etc) to trigger acme-dns registrations and CNAME record creation in various DNS providers. 

This project attempts to address the manual steps as described here in the [cert-manager dns01 acmd-dns solver documentation](https://cert-manager.io/docs/configuration/acme/dns01/acme-dns/) by fully automating the following steps:

* [acme-dns registaration](https://github.com/joohoi/acme-dns)
* dns provider CNAME creation
* `acme-dns.json` secret update

- [local dev](#local-dev)
- [k8swatcher lib dev install](#k8swatcher-lib-dev-install)
- [local run](#local-run)
  - [example output](#example-output)
  - [review the ACMEDNS cert-manager acme-dns.json secret data](#review-the-acmedns-cert-manager-acme-dnsjson-secret-data)
- [Docker](#docker)
  - [Docker Build:](#docker-build)
  - [Docker Run manual:](#docker-run-manual)
  - [Docker Run with .env file:](#docker-run-with-env-file)
  - [API](#api)
  - [related projects](#related-projects)
  - [TODO](#todo)

![](docs/diag1.svg)
# local dev

```
python3 -m venv kubernetes-acme-dns-registrar.ve
source kubernetes-acme-dns-registrar.ve/bin/activate
pip install -r requirements-dev.txt
```


# k8swatcher lib dev install

```
 pip install     \
    --index-url https://test.pypi.org/simple/     \
    --extra-index-url https://pypi.org/simple/     \
    k8swatcher==0.0.0.20220509142406
```

# local run

```

KADR_K8S_WATCHER_CONFIG_YAML=file@`pwd`/dev.k8s-watcher-config.yaml \
KADR_ACME_DNS_CONFIG_YAML=file@`pwd`/dev.acme-dns-config.yaml \
KADR_DNS_PROVIDER_CONFIG_YAML=file@`pwd`/dev.dns-provider-config.yaml \
KADR_DNS_PROVIDER_SECRETS_YAML=file@`pwd`/dev.dns-provider-secrets.yaml \
KADR_JWT_SECRET_KEY=123 \
 uvicorn main:app --reload
```

## example output

Here are some example logs showing what this does, here we are detecting 2 new domain names from the `tls.hosts` section of an `Ingress` object that gets deployed on kubernetes. We react by creating a new registration in `acme-dns`, saving the meta-data to our local storage, and then use the `azuredns` provider to automatically create the `CNAME` pointer to the `acme-dns` subdomin so that that `cert-manager` can fulfill the negotiation w/ `lets-encrypt` to issue the certificate for the `Ingress'`

```
K8sWatcher - DEBUG - K8sWatcher() loading kube config: k8s_config_file_path=/opt/scripts/kubeconfig.secret k8s_config_context_name=myk8scontext (Note: 'None' = using defaults)
K8sWatcher - DEBUG - __iter__() processing K8sWatchConfig[kind=Ingress]
K8sWatcher - DEBUG - handle_k8s_object_list() processing K8sWatchConfig[kind=Ingress]
BaseAzureDnsProvider azuredns - DEBUG - AzureDnsProvider azuredns enabled
DnsProviderProcessor - DEBUG - load_dns_providers() registered DnsProvider: azuredns
DnsProviderProcessor - DEBUG - DnsProviderProcessor() starting run of process_dns_registration_events()....
RegistrarService - DEBUG - __init__() RegistrarService started OK...
K8sWatcher - DEBUG - __iter__() processing K8sWatchConfig[kind=Ingress]
K8sWatcher - DEBUG - handle_k8s_object_watch() processing K8sWatchConfig[kind=Ingress]
ACMEDnsRegistrar - DEBUG - run() no Registration record exists for *.int.mydomain.net ... creating
ACMEDnsRegistrar - DEBUG - run() new Registration record created OK for *.int.mydomain.net target: 66dbc160-2952-40f0-8a76-013423cfc9aa.auth.mydomain.net
ACMEDnsRegistrar - DEBUG - run() no Registration record exists for my-service.int.mydomain.net ... creating
DnsProviderProcessor - DEBUG - process_dns_registration_events() invoking ensure_cname_for_acme_dns() -> azuredns
ACMEDnsRegistrar - DEBUG - run() new Registration record created OK for my-service.int.mydomain.net target: 51b2f5b3-3632-45bd-9f2d-4fb9e0d56bfa.auth.mydomain.net
BaseAzureDnsProvider azuredns - DEBUG - ensure_cname_for_acme_dns() azuredns processed *.int.mydomain.net (_acme-challenge.int) -> 66dbc160-2952-40f0-8a76-013423cfc9aa.auth.mydomain.net
DnsProviderProcessor - DEBUG - process_dns_registration_events() successfully completed for: azuredns
DnsProviderProcessor - DEBUG - process_dns_registration_events() invoking ensure_cname_for_acme_dns() -> azuredns
BaseAzureDnsProvider azuredns - DEBUG - ensure_cname_for_acme_dns() azuredns processed my-service.int.mydomain.net (_acme-challenge.my-service.int) -> 51b2f5b3-3632-45bd-9f2d-4fb9e0d56bfa.auth.mydomain.net
DnsProviderProcessor - DEBUG - process_dns_registration_events() successfully completed for: azuredns
```

## review the ACMEDNS cert-manager acme-dns.json secret data

the `Registrar` automatically manages the ACMEDNS secret that contains all registrations. You can quickly validate its contents; i.e.:

```
kubectl get secret acme-dns -n cert-manager -o json | jq -r '.data."acme-dns.json"' | base64 --decode | jq
```
# Docker
## Docker Build:

The [Dockerfile](Dockerfile) can be built with the following command:

```
docker build -t kubernetes-acme-dns-registrar:0.0.1 .
```

## Docker Run manual:
```
docker run \
    -p 8000:8000 \
    -v `pwd`/kubeconfig.secret:/opt/scripts/kubeconfig.secret \
    -v `pwd`/dev.k8s-watcher-config.yaml:/opt/scripts/k8s-watcher-config.yaml \
    -v `pwd`/dev.acme-dns-config.yaml:/opt/scripts/acme-dns-config.yaml \
    -v `pwd`/dev.dns-provider-config.yaml:/opt/scripts/dns-provider-config.yaml \
    -v `pwd`/dev.dns-provider-secrets.yaml:/opt/scripts/dns-provider-secrets.yaml\
        \
    -e KADR_K8S_WATCHER_CONFIG_YAML=file@/opt/scripts/k8s-watcher-config.yaml \
    -e KADR_ACME_DNS_CONFIG_YAML=file@/opt/scripts/acme-dns-config.yaml \
    -e KADR_DNS_PROVIDER_CONFIG_YAML=file@/opt/scripts/dns-provider-config.yaml \
    -e KADR_DNS_PROVIDER_SECRETS_YAML=file@/opt/scripts/dns-provider-secrets.yaml \
    -e KADR_JWT_SECRET_KEY=123 \
    -e KADR_K8S_WATCHER_CONFIG_FILE_PATH=/opt/scripts/kubeconfig.secret \
    -e KADR_K8S_WATCHER_CONTEXT_NAME=my-k8s-context \
    -e KADR_K8S_ACMEDNS_SECRETS_STORE_CONFIG_FILE_PATH=/opt/scripts/kubeconfig.secret \
    -e KADR_K8S_ACMEDNS_SECRETS_STORE_CONTEXT_NAME=my-k8s-context
        \
    kubernetes-acme-dns-registrar:0.0.1
```

## Docker Run with .env file:

`cp sample.env .env`

```
docker run \
    -p 8000:8000 \
        \
    -v `pwd`/.env:/opt/scripts/.env \
        \
    -v `pwd`/kubeconfig.secret:/opt/scripts/kubeconfig.secret \
    -v `pwd`/dev.k8s-watcher-config.yaml:/opt/scripts/k8s-watcher-config.yaml \
    -v `pwd`/dev.acme-dns-config.yaml:/opt/scripts/acme-dns-config.yaml \
    -v `pwd`/dev.dns-provider-config.yaml:/opt/scripts/dns-provider-config.yaml \
    -v `pwd`/dev.dns-provider-secrets.yaml:/opt/scripts/dns-provider-secrets.yaml\
        \
    kubernetes-acme-dns-registrar:0.0.1
```



## API

Once you start up the registrar, you can access the following endpoints:

* `GET /health` - FastAPI healthcheck endpoint
* `GET /docs` - FastAPI swagger docs
* `POST /oauth2/token` - Acquire an OAuth2 `client_credentials` grant token (username/pw basic auth OR via `client_id/client_secret` FORM post params)
* `GET /registrations[/{name}]` - View the registrar's `Registration` database records

## related projects

https://github.com/joohoi/acme-dns  

https://github.com/bitsofinfo/k8swatcher

## TODO

* update acme-dns solver secret w/ registrations