FROM python:3.13.18-slim-trixie@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

WORKDIR /app

COPY apps/webinstaller-api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY apps/webinstaller-api/app /app
COPY LICENSE /app/LICENSE
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
