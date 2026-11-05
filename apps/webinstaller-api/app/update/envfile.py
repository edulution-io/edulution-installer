import re

from envtools import envValue

_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=")
_DOUBLE_QUOTED = re.compile(r'"((?:\\.|[^"\\])*)"')
_ESCAPE = re.compile(r'\\([\\"$])')


def _eol(line):
    return line[len(line.rstrip("\r\n")):]


def _unquote(raw):
    raw = raw.lstrip()
    if raw.startswith("'"):
        end = raw.find("'", 1)
        if end != -1:
            return raw[1:end]
    elif raw.startswith('"'):
        match = _DOUBLE_QUOTED.match(raw)
        if match:
            return _ESCAPE.sub(r"\1", match.group(1))
    return raw.rstrip()


class EnvFile:
    """An env file kept as raw lines, so untouched lines render byte-identical."""

    def __init__(self, lines):
        self._lines = lines

    @classmethod
    def parse(cls, text):
        return cls(text.splitlines(keepends=True))

    def _find(self, key):
        for index, line in enumerate(self._lines):
            match = _KEY.match(line)
            if match and match.group(1) == key:
                return index
        return None

    def _newline(self):
        return "\r\n" if self._lines and self._lines[0].endswith("\r\n") else "\n"

    def get(self, key):
        index = self._find(key)
        if index is None:
            return None
        line = self._lines[index]
        return _unquote(line[_KEY.match(line).end():].rstrip("\r\n"))

    def set_if_absent(self, key, value, after=None):
        if self._find(key) is not None:
            return False
        newline = self._newline()
        anchor = self._find(after) if after else None
        position = len(self._lines) if anchor is None else anchor + 1
        if position > 0 and not _eol(self._lines[position - 1]):
            self._lines[position - 1] += newline
            new_line = f"{key}={envValue(value)}"
        else:
            new_line = f"{key}={envValue(value)}{newline}"
        self._lines.insert(position, new_line)
        return True

    def replace(self, key, value):
        index = self._find(key)
        if index is None:
            return False
        old = self._lines[index]
        new = f"{key}={envValue(value)}{_eol(old)}"
        if new == old:
            return False
        self._lines[index] = new
        return True

    def render(self):
        return "".join(self._lines)
