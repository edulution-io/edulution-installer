from envtools import envValue
from update.envfile import EnvFile

SAMPLE = (
    "# comment\n"
    "\n"
    "MONGODB_PASSWORD='abc'\n"
    "OTHER=plain  \n"
    'QUOTED="a b"\n'
    "LAST=1\n"
)


def test_roundtrip_is_byte_identical():
    assert EnvFile.parse(SAMPLE).render() == SAMPLE
    crlf = SAMPLE.replace("\n", "\r\n")
    assert EnvFile.parse(crlf).render() == crlf
    assert EnvFile.parse("").render() == ""


def test_get_unquotes_like_compose():
    env = EnvFile.parse("A='x&y'\nB=\"a\\\"b\\$c\"\nC=plain  \n#D=1\nE=\"p\\qr\"\n")
    assert env.get("A") == "x&y"
    assert env.get("B") == 'a"b$c'
    assert env.get("C") == "plain"
    assert env.get("D") is None
    assert env.get("E") == "p\\qr"
    assert env.get("MISSING") is None


def test_get_first_line_wins():
    assert EnvFile.parse("A=1\nA=2\n").get("A") == "1"


def test_get_roundtrips_env_value():
    for value in ["plain", "it's", "back\\", 'q"$x', "a`b"]:
        assert EnvFile.parse(f"K={envValue(value)}\n").get("K") == value


def test_set_if_absent_inserts_after_key():
    env = EnvFile.parse(SAMPLE)
    assert env.set_if_absent("NEW", "v", after="MONGODB_PASSWORD") is True
    lines = env.render().splitlines()
    assert lines[3] == "NEW='v'"
    assert lines[2] == "MONGODB_PASSWORD='abc'"
    before = env.render()
    assert env.set_if_absent("NEW", "w", after="MONGODB_PASSWORD") is False
    assert env.render() == before


def test_set_if_absent_after_missing_key_appends():
    env = EnvFile.parse("A=1\n")
    assert env.set_if_absent("B", "2", after="NOPE") is True
    assert env.render() == "A=1\nB='2'\n"


def test_set_if_absent_keeps_crlf():
    env = EnvFile.parse("A=1\r\nB=2\r\n")
    env.set_if_absent("N", "v", after="A")
    assert env.render() == "A=1\r\nN='v'\r\nB=2\r\n"


def test_append_without_trailing_newline():
    env = EnvFile.parse("A=1\nB=2")
    assert env.render() == "A=1\nB=2"
    env.set_if_absent("N", "v")
    assert env.render() == "A=1\nB=2\nN='v'"


def test_insert_after_last_line_without_newline():
    env = EnvFile.parse("A=1")
    env.set_if_absent("N", "v", after="A")
    assert env.render() == "A=1\nN='v'"


def test_replace_touches_one_line():
    env = EnvFile.parse(SAMPLE)
    before = env.render().splitlines(keepends=True)
    assert env.replace("OTHER", "it's") is True
    after = env.render().splitlines(keepends=True)
    assert len(before) == len(after)
    diff = [(b, a) for b, a in zip(before, after) if b != a]
    assert diff == [("OTHER=plain  \n", 'OTHER="it\'s"\n')]
    assert env.replace("OTHER", "it's") is False
    assert env.replace("MISSING", "x") is False


def test_replace_keeps_line_ending_and_missing_newline():
    env = EnvFile.parse("A=1\r\nB=2")
    env.replace("A", "x")
    env.replace("B", "y")
    assert env.render() == "A='x'\r\nB='y'"


def test_only_newlines_split_lines():
    text = 'K=a b\nZ="x\x85y"\nR=a\rb\nQ=c\x85'
    env = EnvFile.parse(text)
    assert env.render() == text
    assert env.get("K") == "a b"
    assert env.get("Z") == "x\x85y"
    assert env.get("R") == "a\rb"
    assert env.set_if_absent("N", "v", after="Q") is True
    assert env.render() == text + "\nN='v'"
    env.set_if_absent("M", "v", after="K")
    assert env.render().startswith("K=a b\nM='v'\nZ=")


def test_get_stops_unquoted_value_at_inline_comment():
    env = EnvFile.parse("U=mongodb://edu-db:27017/ # x\nT=a\t# y\nH=a#b\nS=v #\n")
    assert env.get("U") == "mongodb://edu-db:27017/"
    assert env.get("T") == "a"
    assert env.get("H") == "a#b"
    assert env.get("S") == "v"


def test_get_quoted_value_with_trailing_comment():
    env = EnvFile.parse("D=\"a # b\" # c\nS='x # y' # z\n")
    assert env.get("D") == "a # b"
    assert env.get("S") == "x # y"


def test_replace_on_line_with_inline_comment():
    env = EnvFile.parse("U=mongodb://edu-db:27017/ # x\n")
    url = env.get("U")
    assert env.replace("U", url + "?replicaSet=rs0") is True
    assert env.render() == "U='mongodb://edu-db:27017/?replicaSet=rs0'\n"
