#!/bin/bash

# Start with HTTPS using the generated certificate
echo "Starting installer on HTTPS port 8443..."
uvicorn main:app --host 0.0.0.0 --port 8443 --ssl-keyfile /key.pem --ssl-certfile /cert.pem