from update.migrations import Context, Migration

URL_KEY = "MONGODB_SERVER_URL"
REQUIRED = (("replicaSet", "rs0"), ("directConnection", "true"))


def _split(url: str) -> tuple[str, str, str]:
    """Return (everything up to the host part, host part, query without '?')."""
    start = url.rfind("@") + 1 if "@" in url else (len("mongodb://") if url.startswith("mongodb://") else 0)
    head, rest = url[:start], url[start:]
    host, sep, query = rest.partition("?")
    return head, host, query if sep else ""


def _params(query: str) -> list[str]:
    return query.split("&") if query else []


def with_replica_set(url: str) -> str:
    head, host, query = _split(url)
    params = _params(query)
    for name, value in REQUIRED:
        wanted = f"{name}={value}"
        for i, param in enumerate(params):
            if param.split("=", 1)[0] == name:
                params[i] = wanted
                break
        else:
            params.append(wanted)
    return f"{head}{host}?{'&'.join(params)}"


def _needed(ctx: Context) -> bool:
    if ctx.env.get("MONGODB_AUTH_SOURCE") is None:
        return True
    url = ctx.env.get(URL_KEY)
    return url is not None and with_replica_set(url) != url


def _apply(ctx: Context) -> None:
    ctx.env.set_if_absent("MONGODB_AUTH_SOURCE", "admin", after="MONGODB_PASSWORD")
    ctx.env.rewrite(URL_KEY, with_replica_set)


MIGRATION = Migration(
    id="0001-mongo-replica-set-env",
    kind="normal",
    recreate=("edu-db", "edu-api"),
    needed=_needed,
    apply=_apply,
)
