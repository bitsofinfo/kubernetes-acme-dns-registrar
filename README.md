# kubernetes-acme-dns-registrar

Watches k8s resources (ingress objects etc) to trigger acme-dns registrations and CNAME record creation in various DNS providers


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
 uvicorn main:app --reload
```