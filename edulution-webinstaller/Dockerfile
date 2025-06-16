FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl openssl
RUN curl -sSL https://get.docker.com/ | CHANNEL=stable sh

WORKDIR /app
RUN pip install --no-cache-dir --upgrade fastapi uvicorn[standard] cryptography python-multipart requests ldap3 pyyaml aiofiles
COPY ./app /app
COPY ./startup.sh /startup.sh
COPY ./startup-https.sh /startup-https.sh
RUN chmod +x /startup.sh /startup-https.sh

EXPOSE 8000 8443
CMD ["/startup.sh"]