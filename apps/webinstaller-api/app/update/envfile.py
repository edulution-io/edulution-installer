import re

from envtools import envValue

_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)[ \t]*=")
_DOUBLE_QUOTED = re.compile(r'"((?:\\.|[^"\\])*)"')
_ESCAPE = re.compile(r'\\([\\"$])')
_INLINE_COMMENT = re.compile(r"[ \t]#.*")


def _eol(line):
    if line.endswith("\r\n"):
        return "\r\n"
    return "\n" if line.endswith("\n") else ""


def _unquote(raw):
    raw = raw.lstrip(" \t")
    if raw.startswith("'"):
        end = raw.find("'", 1)
        if end != -1:
            return raw[1:end]
    elif raw.startswith('"'):
        match = _DOUBLE_QUOTED.match(raw)
        if match:
            return _ESCAPE.sub(r"\1", match.group(1))
    # Compose ends an unquoted value at whitespace followed by "#".
    return _INLINE_COMMENT.sub("", raw, count=1).rstrip(" \t")


class EnvFile:
    """An env file kept as raw lines, so untouched lines render byte-identical."""

    def __init__(self, lines):
        self._lines = lines

    @classmethod
    def parse(cls, text):
        # str.splitlines would also split on U+2028, \x85 and a bare \r.
        return cls(re.findall(r"[^\n]*\n|[^\n]+", text))

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
        body = line[: len(line) - len(_eol(line))]
        return _unquote(body[_KEY.match(body).end():])

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
