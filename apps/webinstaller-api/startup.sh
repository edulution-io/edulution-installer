#!/bin/bash

# Self-signed Zertifikat für den Installer
openssl req -x509 -newkey rsa:4096 -nodes -out /cert.pem -keyout /key.pem -days 3650 \
    -subj "/C=DE/ST=State/L=City/O=Installer/OU=edulution/CN=installer" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

# Start the application with HTTPS
uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-keyfile /key.pem --ssl-certfile /cert.pem
