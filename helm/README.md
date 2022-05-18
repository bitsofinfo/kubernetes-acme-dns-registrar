IMPORTANT: when using `--set-file` neither `values.yaml` OR any of the yaml content within the files you are referencing should have any dangling `attribute:` with no value, otherwise you will get parse errors. 

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