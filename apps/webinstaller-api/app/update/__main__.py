import argparse
import json
import sys
from pathlib import Path

from update.drift import check, exit_code, fingerprint, to_json
from update.migrations import MIGRATIONS
from update.runner import UpdateError, apply, init, migrate
from update.templates import history, target_compose, target_version

DEFAULT_DIR = "/edulution-ui"


STATUS_DE = {
    "current": "aktuell",
    "outdated": "veraltet",
    "modified": "lokal geändert",
    "unknown": "unbekannt",
}


def _print_report(report) -> None:
    installed = report.installed_version or "unbekannt"
    print(f"Status: {STATUS_DE.get(report.status, report.status)}")
    print(f"Installierte Version: {installed}")
    print(f"Zielversion: {report.target_version}")
    if report.pending:
        print("Ausstehende Migrationen:")
        for m in report.pending:
            print(f"  {m.id} ({m.kind})")
    if report.blocked_by:
        print("Blockiert durch: " + ", ".join(m.id for m in report.blocked_by))
    if report.available_majors:
        print("Verfügbare größere Migrationen: " + ", ".join(m.id for m in report.available_majors))
    if report.recreate:
        print("Neu zu erstellende Dienste: " + ", ".join(report.recreate))
    if report.diff:
        print()
        print(report.diff)


def _summary(outcome) -> None:
    if not outcome.applied and not outcome.template_installed:
        print("Bereits aktuell, nichts geändert.")
        return
    if outcome.template_installed:
        print(f"Vorlage {outcome.report.target_version} installiert.")
    if outcome.applied:
        print("Ausgeführte Migrationen: " + ", ".join(outcome.applied))
    by_id = {m.id: m for m in MIGRATIONS}
    services = list(dict.fromkeys(
        svc for mid in outcome.applied if mid in by_id for svc in by_id[mid].recreate
    ))
    if services:
        print("Neu zu erstellende Dienste: " + ", ".join(services))
    if outcome.report.blocked_by:
        print("Weitere Migration nötig: " + ", ".join(m.id for m in outcome.report.blocked_by))
    elif exit_code(outcome.report) != 0:
        print("Ein Update der Installation steht noch aus.")


def _run(args) -> int:
    root = Path(args.dir)
    version = target_version()
    if args.command == "check":
        report = check(root, target_compose(), version, history(), MIGRATIONS)
        if args.json:
            print(json.dumps(to_json(report), ensure_ascii=False, indent=2))
        else:
            _print_report(report)
        return exit_code(report)
    if args.command == "expect":
        print(fingerprint(root))
        return 0
    if args.command == "init":
        init(root, target_version=version, registry=MIGRATIONS)
        print(f"Installation für Updates vorbereitet (Version {version}).")
        return 0

    if not args.yes:
        print("Ohne --yes wird nichts geändert.", file=sys.stderr)
        return 2
    text = target_compose()
    hist = history()
    if args.command == "apply":
        outcome = apply(
            root,
            expect=args.expect,
            discard_local_changes=args.discard_local_changes,
            target_text=text,
            target_version=version,
            history=hist,
            registry=MIGRATIONS,
        )
    else:
        outcome = migrate(
            root,
            args.id,
            expect=args.expect,
            target_text=text,
            target_version=version,
            history=hist,
            discard_local_changes=args.discard_local_changes,
            registry=MIGRATIONS,
        )
    _summary(outcome)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m update", description="edulution Compose-Update")
    parser.add_argument("--dir", default=DEFAULT_DIR, help="Installationsverzeichnis")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="Zustand prüfen")
    p.add_argument("--json", action="store_true")

    sub.add_parser("expect", help="Fingerabdruck der Dateien ausgeben")

    p = sub.add_parser("apply", help="Update anwenden")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--expect", required=True)
    p.add_argument("--discard-local-changes", action="store_true")

    p = sub.add_parser("migrate", help="Größere Migration ausführen")
    p.add_argument("--id", required=True)
    p.add_argument("--yes", action="store_true")
    p.add_argument("--expect", required=True)
    p.add_argument("--discard-local-changes", action="store_true")

    sub.add_parser("init", help="Bestehende Installation für Updates vorbereiten")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    try:
        return _run(args)
    except UpdateError as err:
        print(err.message, file=sys.stderr)
        return err.code
    except FileNotFoundError as err:
        print(f"Datei nicht gefunden: {err.filename or err}", file=sys.stderr)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        print(f"Datei ist nicht lesbar oder beschädigt: {err}", file=sys.stderr)
    except Exception as err:
        print(f"Unerwarteter Fehler: {str(err) or type(err).__name__}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
