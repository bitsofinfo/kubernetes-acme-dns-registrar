# setup overview <!-- omit in TOC -->

Trying to figure out an entire dynamic tls certificate solution in kubernetes can be daunting. This guide will try to point you in the right direction by laying out the general guideposts and order of operations. Any code/sample blocks below are just that, examples... and are not necessarily something that will work; those details are up to you.

- [1. Get a kubernetes cluster](#1-get-a-kubernetes-cluster)
- [2. Setup a DNS name server(s)](#2-setup-a-dns-name-servers)
- [3. Setup acme-dns](#3-setup-acme-dns)
- [4. Install cert-manager](#4-install-cert-manager)
- [5. Seed the acme-dns.json k8s secret](#5-seed-the-acme-dnsjson-k8s-secret)
- [6. Configure an cert-manager Issuer for lets-encrypt](#6-configure-an-cert-manager-issuer-for-lets-encrypt)
- [7. Install kubernetes-acme-dns-registrar](#7-install-kubernetes-acme-dns-registrar)
## 1. Get a kubernetes cluster

The obvious step one is getting a kubernetes cluster that you have the appropriate access to.

## 2. Setup a DNS name server(s)

The fact that you are even looking at this project assumes you are NOT using the [cert-manager HTTP01 solver](https://cert-manager.io/docs/configuration/acme/http01/)... there can be issues with this in larger setups depending on the ingress controller you are using and the lack of resiliency it can limit you to with regards to number of ingress controller replicas.... ([such as with Traefik](https://doc.traefik.io/traefik/providers/kubernetes-ingress/#letsencrypt-support-with-the-ingress-provider))

Given that, the more extensible solution is just to use a [DNS01 solver](https://cert-manager.io/docs/configuration/acme/dns01/)... and that requires a DNS server.

Depending on your situation you may be wanting to issue certificates for public zones and/or private zones. Out of the box, the standard [DNS01 solvers](https://cert-manager.io/docs/configuration/acme/dns01/) for `cert-manager` work great... but they only work with publically available nameservers. If you have a private zone you want to get certificates for, then you are going to need another tool which is a special DNS server that only handles the ACME challenges, and nothing else.. i.e. [acme-dns](https://github.com/joohoi/acme-dns/) that is available to be queried via the internet (by nature private nameservers cannot be queried that way)

In fact, regardless of if you have private zones or not, its recommended you use [acme-dns](https://github.com/joohoi/acme-dns/) anyways, even for your public zones, why? because it can limit the amount of power `cert-manager` has over writing data into your dns server.

## 3. Setup acme-dns

Now that you have your nameserver(s) you are going to want to install [acme-dns](https://github.com/joohoi/acme-dns/) DNS challenge nameserver. This is what `cert-manager` will use to store the ACME challenges as TXT records within so that the CA (lets-encrypt) can validate you own the domain that you want a cert for. When you use this, your real production servers won't be involved in serving up the ACME challenge TXT records.

You can run `acme-dns` however/wherever you want. You are just going to want to make sure it is accessible like any other public nameserver (i.e. port 53).

In the context of this conversation however, you can skip the manual API calls to `POST /register` because that is what [kubernetes-acme-dns-registrar](https://github.com/bitsofinfo/kubernetes-acme-dns-registrar) will handle for you automatically.

## 4. Install cert-manager

The workhorse of the automatic TLS certificate acquisition and management is [cert-manager](https://cert-manager.io/docs/installation/). You are going to need to [install cert-manager](https://cert-manager.io/docs/installation/) on your cluster

Here is an example using `helm`:

```
helm repo add jetstack https://charts.jetstack.io

helm repo update

helm upgrade \
  cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.8.0 \
  --set installCRDs=true \
  --set global.logLevel=4 \
  --set "extraArgs={--max-concurrent-challenges=2,--dns01-recursive-nameservers-only,--dns01-recursive-nameservers=8.8.8.8:53,1.1.1.1:53}"
  ```

  You can read on your own about the uses of `--max-concurrent-challenges` and `--dns01-recursive-nameservers-only` on your own. One key thing about `--dns01-recursive-nameservers-only` is that it forces `cert-manager` to not use a local dns server on the network, (that might be your private dns server) for which you are trying to get a certificate for, hence leading it to not being able to find it, which is what [acme-dns](https://github.com/joohoi/acme-dns) is there for (i.e. as a front for all your zone's challenges, even the private zones)

## 5. Seed the acme-dns.json k8s secret

Our goal here is to configure a [cert-manager [Cluster]Issuer](https://cert-manager.io/docs/configuration/acme/#creating-a-basic-acme-issuer) for `lets-encrypt` using a [DNS01 solver](https://cert-manager.io/docs/configuration/acme/dns01/) using [ACMEDNS challenge provider](https://cert-manager.io/docs/configuration/acme/dns01/acme-dns/)....but in order to do that we need a pre-requisite to be done... configure the `acme-dns.json` secret that will contain all the `acme-dns` registrations.

Lets provision this secret into the cluster. Note the `acme-dns.json` contents are intentionally empty... why? because [kubernetes-acme-dns-registrar](https://github.com/bitsofinfo/kubernetes-acme-dns-registrar) will be automatically populating this for you.

You will want to apply this to whatever `namespace` that `cert-manager` is installed in.

```
apiVersion: v1
kind: Secret
metadata:
  name: acme-dns
type: Opaque
stringData:
  acme-dns.json: |
    {
    }

```

## 6. Configure an cert-manager Issuer for lets-encrypt

Next we need to configure a [cert-manager [Cluster]Issuer](https://cert-manager.io/docs/configuration/acme/#creating-a-basic-acme-issuer) for `lets-encrypt`

Here is a sample of what this looks like for `lets-encrypt` STAGING (which is what you will want to start with). This configuration is basically telling `cert-manager` *"here is where you go to write ACME challenges TXT records, and this acme-dns.json contains the credentials you will need to do the writes..."*

Note the `acmeDNS` section and `accountSecretRef` below.

```
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging-acme
spec:
  acme:
    email: <YOUR_EMAIL>
    server: https://acme-staging-v02.api.letsencrypt.org/directory

    privateKeySecretRef:
      # Secret resource that will be used to store the account's private key.
      name: stage-issuer-account-key

    solvers:
      - dns01:
          acmeDNS:
            accountSecretRef:
              name: acme-dns
              key: acme-dns.json
            host: http[s]://<YOUR_ACME_DNS_CHALLENGE_SERVER>:[PORT]
```

## 7. Install kubernetes-acme-dns-registrar

Ok, now lets tie everything above together w/ `kubernetes-acme-dns-registrar`

TBD