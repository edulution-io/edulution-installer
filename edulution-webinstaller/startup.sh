#!/bin/bash

# Try to detect hostname from various sources
if [ -n "$INSTALLER_HOSTNAME" ]; then
    HOSTNAME="$INSTALLER_HOSTNAME"
else
    # Try to get from system
    HOSTNAME=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "localhost")
fi

echo "Generating certificate for: $HOSTNAME"

openssl req -x509 -newkey rsa:4096 -nodes \
    -out /cert.pem -keyout /key.pem -days 3650 \
    -subj "/C=DE/ST=State/L=City/O=Installer/OU=edulution/CN=$HOSTNAME" \
    -addext "subjectAltName=DNS:$HOSTNAME,DNS:localhost,IP:127.0.0.1,DNS:*.local"

# Start the application
uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-keyfile /key.pem --ssl-certfile /cert.pem