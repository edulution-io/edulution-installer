FROM python:3.13.16-slim-trixie@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

# The release tag the LMN bootstrap is fetched from; an explicit -e BOOTSTRAP_BRANCH still wins.
ARG INSTALLER_REF=main
ENV BOOTSTRAP_BRANCH=$INSTALLER_REF

WORKDIR /app

COPY apps/webinstaller-api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY apps/webinstaller-api/app /app
COPY dist/apps/webinstaller /app/static
COPY apps/webinstaller-api/startup.sh /startup.sh
RUN chmod +x /startup.sh

EXPOSE 8000
CMD ["/startup.sh"]
