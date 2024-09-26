FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir --upgrade fastapi uvicorn[standard] cryptography python-multipart requests ldap3
RUN openssl req -x509 -newkey rsa:4096 -nodes -out /cert.pem -keyout /key.pem -days 3650 -subj "/C=/ST=/L=/O=Installer/OU=edulution/CN=edulution.io"
COPY ./app /app

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--ssl-keyfile", "/key.pem", "--ssl-certfile", "/cert.pem"]