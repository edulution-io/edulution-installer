FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl openssl certbot
RUN curl -sSL https://get.docker.com/ | CHANNEL=stable sh

WORKDIR /app
RUN pip install --no-cache-dir --upgrade fastapi uvicorn[standard] cryptography python-multipart requests ldap3 pyyaml
COPY ./app /app
COPY ./startup.sh /startup.sh
RUN chmod +x /startup.sh

EXPOSE 8000 8080
CMD ["/startup.sh"]