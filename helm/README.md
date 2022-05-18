# helm chart

You can install this project in a kubernetes cluster with this helm chart. 

Please see [values.yaml](values.yaml) for all configurable options.

## Using!

```
helm repo add bitsofinfo-kubernetes-acme-dns-registrar https://raw.githubusercontent.com/bitsofinfo/kubernetes-acme-dns-registrar/master/repo
helm repo update
```

Using as a dependency:
```
# requirements.yaml
dependencies:
- name: appdeploy
  version: "<TAG_VERSION>"
  repository: "https://raw.githubusercontent.com/bitsofinfo/kubernetes-acme-dns-registrar/master/repo"
```

## Usage 

*IMPORTANT: when using `--set-file` neither `values.yaml` OR any of the yaml content within the files you are referencing should have any dangling `attribute:` with no value, otherwise you will get parse errors. *

See what it will output:
```
helm template kubernetes-acme-dns-registrar . \
    --values values.yaml \
    --debug \
    --set-file acmedns.configYaml=../dev.acme-dns-config.yaml \
    --set-file k8swatcher.configYaml=../dev.k8s-watcher-config.yaml \
    --set-file dnsproviders.configYaml=../dev.dns-provider-config.yaml \
    --set-file dnsproviders.secretsYaml=../dev.dns-provider-secrets.yaml \
    --set api.jwtSecretKey='1234$kadr@*j_dummykey' 
```


Install/upgrade
```
helm [install|upgrade] kubernetes-acme-dns-registrar . \
    --values values.yaml \
    --debug \
    --set-file acmedns.configYaml=../dev.acme-dns-config.yaml \
    --set-file k8swatcher.configYaml=../dev.k8s-watcher-config.yaml \
    --set-file dnsproviders.configYaml=../dev.dns-provider-config.yaml \
    --set-file dnsproviders.secretsYaml=../dev.dns-provider-secrets.yaml \
    --set api.jwtSecretKey='1234$kadr@*j_dummykey' \
    --namespace cert-manager
```

## <a id="pack"></a>Helm package/update

```
helm package . -d repo/charts/
helm repo index repo/
```