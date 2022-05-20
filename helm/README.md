# helm chart

You can install this project in a kubernetes cluster with this helm chart. 

Please see [values.yaml](values.yaml) for all configurable options.

## Install

```
helm repo add bitsofinfo-kubernetes-acme-dns-registrar https://raw.githubusercontent.com/bitsofinfo/kubernetes-acme-dns-registrar/main/helm/repo
helm repo update
```

Using as a dependency in another chart:
```
# requirements.yaml
dependencies:
- name: appdeploy
  version: "<TAG_VERSION>"
  repository: "https://raw.githubusercontent.com/bitsofinfo/kubernetes-acme-dns-registrar/main/helm/repo"
```

## Usage 

*IMPORTANT: when using `--set-file` neither `values.yaml` OR any of the yaml content within the files you are referencing should have any dangling `attribute:` with no value, otherwise you will get parse errors. *

See what it will output:
```
helm template kubernetes-acme-dns-registrar \
    bitsofinfo-kubernetes-acme-dns-registrar/kubernetes-acme-dns-registrar \
    --set-file acmedns.configYaml=my.acme-dns-config.yaml \
    --set-file k8swatcher.configYaml=my.k8s-watcher-config.yaml \
    --set-file dnsproviders.configYaml=my.dns-provider-config.yaml \
    --set-file dnsproviders.secretsYaml=my.dns-provider-secrets.yaml \
    --set api.jwtSecretKey='1234$kadr@*j_dummykey' 
```


Install/upgrade
```
helm install kubernetes-acme-dns-registrar \
    bitsofinfo-kubernetes-acme-dns-registrar/kubernetes-acme-dns-registrar \
    --set-file acmedns.configYaml=my.acme-dns-config.yaml \
    --set-file k8swatcher.configYaml=my.k8s-watcher-config.yaml \
    --set-file dnsproviders.configYaml=my.dns-provider-config.yaml \
    --set-file dnsproviders.secretsYaml=my.dns-provider-secrets.yaml \
    --set api.jwtSecretKey='1234$kadr@*j_dummykey' \
    --namespace cert-manager
```

## <a id="pack"></a>Helm package/update

```
helm package . -d repo/charts/
helm repo index repo/
```

## local dev


See what it will output:
```
helm template kubernetes-acme-dns-registrar . \
    --values values.yaml \
    --debug \
    --set-file acmedns.configYaml=../my.acme-dns-config.yaml \
    --set-file k8swatcher.configYaml=../my.k8s-watcher-config.yaml \
    --set-file dnsproviders.configYaml=../my.dns-provider-config.yaml \
    --set-file dnsproviders.secretsYaml=../my.dns-provider-secrets.yaml \
    --set api.jwtSecretKey='1234$kadr@*j_dummykey' \
    --set ingress.hostnameFqdn=my-kadr.mydomain.net \
    --set ingress.tls.enabled=true \
    --set ingress.tls.secretName=my-kadr-mydomain-net \
    --set ingress.metadata.annotations.kubernetes\\.io/ingress\\.class=my-ingress-class \
    --set ingress.metadata.labels.my-label=test
```


Install/upgrade
```
helm [install|upgrade] kubernetes-acme-dns-registrar . \
    --values values.yaml \
    --debug \
    --set-file acmedns.configYaml=../my.acme-dns-config.yaml \
    --set-file k8swatcher.configYaml=../my.k8s-watcher-config.yaml \
    --set-file dnsproviders.configYaml=../my.dns-provider-config.yaml \
    --set-file dnsproviders.secretsYaml=../my.dns-provider-secrets.yaml \
    --set api.jwtSecretKey='1234$kadr@*j_dummykey' \
    --namespace cert-manager
```
