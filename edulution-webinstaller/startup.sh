#!/bin/bash

# Check if domain is provided for Let's Encrypt
if [ -n "$INSTALLER_DOMAIN" ]; then
    echo "Domain erkannt: $INSTALLER_DOMAIN"
    echo "Versuche Let's Encrypt Zertifikat zu erstellen..."
    
    # Try to get Let's Encrypt certificate
    if certbot certonly --standalone --non-interactive --agree-tos --email admin@${INSTALLER_DOMAIN} -d ${INSTALLER_DOMAIN} --http-01-port=8080; then
        echo "Let's Encrypt Zertifikat erfolgreich erstellt!"
        SSL_CERT="/etc/letsencrypt/live/${INSTALLER_DOMAIN}/fullchain.pem"
        SSL_KEY="/etc/letsencrypt/live/${INSTALLER_DOMAIN}/privkey.pem"
    else
        echo "Let's Encrypt fehlgeschlagen, verwende self-signed Zertifikat..."
        openssl req -x509 -newkey rsa:4096 -nodes -out /cert.pem -keyout /key.pem -days 3650 \
            -subj "/C=DE/ST=State/L=City/O=Installer/OU=edulution/CN=${INSTALLER_DOMAIN}" \
            -addext "subjectAltName=DNS:${INSTALLER_DOMAIN},DNS:localhost,IP:127.0.0.1"
        SSL_CERT="/cert.pem"
        SSL_KEY="/key.pem"
    fi
else
    echo "Keine Domain angegeben, verwende self-signed Zertifikat..."
    openssl req -x509 -newkey rsa:4096 -nodes -out /cert.pem -keyout /key.pem -days 3650 \
        -subj "/C=DE/ST=State/L=City/O=Installer/OU=edulution/CN=installer" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
    SSL_CERT="/cert.pem"
    SSL_KEY="/key.pem"
fi

# Start the application with HTTPS
echo "Starte Installer mit SSL-Zertifikat: $SSL_CERT"
uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-keyfile "$SSL_KEY" --ssl-certfile "$SSL_CERT"