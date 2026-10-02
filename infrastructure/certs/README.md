# Extra CA certificates for Docker builds

Some networks intercept HTTPS (corporate proxies, antivirus "HTTPS scanning"
such as Avast Web Shield). The host trusts the interception root CA, but
containers do not, so `pip install` / `npm ci` inside `docker compose build`
fail with `CERTIFICATE_VERIFY_FAILED`.

If that happens, export the interception root CA as PEM and point the build
at it:

```bash
EXTRA_CA_CERT_FILE=./infrastructure/certs/local-extra-ca.pem docker compose build
```

The file is passed as a BuildKit secret: it is mounted only for the package
install steps and is **not** copied into any image layer. `*.pem` files are
git-ignored; never commit a CA certificate here. Without the variable,
`empty-ca-bundle.txt` (empty) is used and nothing extra is trusted.
