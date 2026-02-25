FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl openssl && \
    curl -sSL https://get.docker.com/ | CHANNEL=stable sh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY apps/webinstaller-api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY apps/webinstaller-api/app /app
COPY dist/apps/webinstaller /app/static
COPY apps/webinstaller-api/startup.sh /startup.sh
RUN chmod +x /startup.sh

EXPOSE 8000
CMD ["/startup.sh"]
