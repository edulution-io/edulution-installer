FROM python:3.13.17-slim-trixie@sha256:d98cc29d3266e535dd9da1099688d9cb3ca4753813571e071763d17725460962

WORKDIR /app

COPY apps/webinstaller-api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY apps/webinstaller-api/app /app
# Handed to the LMN server over SSH, so it runs the installer of this image's version.
COPY edulution-lmninstaller /app/lmninstaller
COPY dist/apps/webinstaller /app/static
COPY apps/webinstaller-api/startup.sh /startup.sh
RUN chmod +x /startup.sh

# Set from the release tag by the release workflow.
ARG INSTALLER_VERSION=dev
ENV INSTALLER_VERSION=$INSTALLER_VERSION

EXPOSE 8000
CMD ["/startup.sh"]
