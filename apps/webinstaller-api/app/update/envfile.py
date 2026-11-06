import re

from envtools import envValue

_KEY = re.compile(r"^[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*=")
_ESCAPE = re.compile(r'\\([\\"$])')
_SINGLE_ESCAPE = re.compile(r"\\(.)", re.S)


def _eol(line):
    if line.endswith("\r\n"):
        return "\r\n"
    return "\n" if line.endswith("\n") else ""


def _closing_quote(raw):
    # As in Compose, a backslash escapes the next character in both quote styles.
    escaped = False
    for index in range(1, len(raw)):
        if escaped:
            escaped = False
        elif raw[index] == "\\":
            escaped = True
        elif raw[index] == raw[0]:
            return index
    return -1


def _value_span(raw):
    """Return (start, end) of the value as written inside raw, without quotes or inline comment."""
    if raw[:1] in ("'", '"'):
        end = _closing_quote(raw)
        if end != -1:
            return 1, end
    # Compose ends an unquoted value at " #", a space and not a tab.
    comment = raw.find(" #")
    return 0, len(raw[: comment if comment != -1 else len(raw)].rstrip(" \t"))


def _unquote(raw):
    raw = raw.lstrip(" \t")
    start, end = _value_span(raw)
    value = raw[start:end]
    if start == 0:
        return value
    if raw[0] == '"':
        return _ESCAPE.sub(r"\1", value)
    return _SINGLE_ESCAPE.sub(lambda m: "'" if m.group(1) == "'" else m.group(0), value)


class EnvFile:
    """An env file kept as raw lines, so untouched lines render byte-identical."""

    def __init__(self, lines):
        self._lines = lines

    @classmethod
    def parse(cls, text):
        # str.splitlines would also split on U+2028, \x85 and a bare \r.
        return cls(re.findall(r"[^\n]*\n|[^\n]+", text))

    def _find(self, key):
        # Compose uses the last assignment of a key.
        for index in range(len(self._lines) - 1, -1, -1):
            match = _KEY.match(self._lines[index])
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

    def rewrite(self, key, transform):
        """Apply transform to the value as written, keeping its quoting, so ${VAR} references keep
        expanding. transform may only add characters that need no quoting or escaping."""
        index = self._find(key)
        if index is None:
            return False
        old = self._lines[index]
        eol = _eol(old)
        body = old[: len(old) - len(eol)]
        head = _KEY.match(body).end()
        start = len(body) - len(body[head:].lstrip(" \t"))
        raw = body[start:]
        value_start, value_end = _value_span(raw)
        new = (
            body[:start] + raw[:value_start] + transform(raw[value_start:value_end]) + raw[value_end:] + eol
        )
        if new == old:
            return False
        self._lines[index] = new
        return True

    def render(self):
        return "".join(self._lines)
