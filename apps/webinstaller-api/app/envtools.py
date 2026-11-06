import os
import re
import secrets
import string


def generateSecret(length=32):
    characters = string.ascii_letters + string.digits
    random_string = "".join(secrets.choice(characters) for _ in range(length))
    return random_string


def openPrivate(path, mode="w"):
    """Oeffnet eine Datei mit Geheimnissen zum Schreiben, nur fuer root lesbar."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    # Der Modus von os.open gilt nur fuer neue Dateien.
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, mode)


def envValue(value):
    # Docker Compose takes single-quoted values literally, except a trailing \ escaping the closing quote.
    # In double quotes it unescapes \\, \" and \$ but keeps a backslash before anything else, such as `.
    if "'" not in value and not value.endswith("\\"):
        return f"'{value}'"
    return '"' + re.sub(r'([\\"$])', r'\\\1', value) + '"'
