#!/bin/bash

openssl genrsa -out test.key.pem 4096
openssl req -new -sha256 -key  test.key.pem -out test.csr.csr
openssl req -x509 -sha256 -days 365 -key test.key.pem -in test.csr.csr -out test.certificate.pem