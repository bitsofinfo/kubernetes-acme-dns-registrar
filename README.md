# kubernetes-acme-dns-registrar <!-- omit in TOC -->

Watches k8s resources (ingress objects etc) to trigger acme-dns registrations and CNAME record creation in various DNS providers

- [local dev](#local-dev)
- [k8swatcher lib dev install](#k8swatcher-lib-dev-install)
- [local run](#local-run)
- [Docker](#docker)
  - [Docker Build:](#docker-build)
  - [Docker Run w/ .env file:](#docker-run-w-env-file)
  - [API](#api)
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


# Docker
## Docker Build:

The [Dockerfile](Dockerfile) can be built with the following command:

```
docker build -t kubernetes-acme-dns-registrar:0.0.1 .
```

## Docker Run w/ .env file:
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
    -e KADR_K8S_CONFIG_FILE_PATH=/opt/scripts/kubeconfig.secret \
    -e KADR_K8S_CONTEXT_NAME=edg-eastus-rnd2-nuc-test-001-aks \
        \
    kubernetes-acme-dns-registrar:0.0.1
```


## API

Once you start up the registrar, you can access the following endpoints:

* `GET /health` - FastAPI healthcheck endpoint
* `GET /docs` - FastAPI swagger docs
* `POST /oauth2/token` - Acquire an OAuth2 `client_credentials` grant token (username/pw basic auth OR via `client_id/client_secret` FORM post params)
* `GET /registrations[/{name}]` - View the registrar's `Registration` database records