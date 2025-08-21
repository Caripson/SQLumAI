Development TLS certificates

- The TLS-terminating proxy expects `TLS_CERT_PATH` and `TLS_KEY_PATH` (default `certs/dev-cert.pem` and `certs/dev-key.pem`).
- For local testing, generate a self-signed cert:

  openssl req -x509 -newkey rsa:2048 -keyout certs/dev-key.pem -out certs/dev-cert.pem -days 365 -nodes -subj "/CN=localhost"

- Clients must trust this certificate for encrypted connections to succeed.

