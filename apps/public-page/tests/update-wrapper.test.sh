#!/bin/bash
# Runs public/update against a stub docker. Usage: bash update-wrapper.test.sh
set -u

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WRAPPER="$HERE/../public/update"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

mkdir "$WORK/bin" "$WORK/dir"
touch "$WORK/dir/edulution.env"
cat > "$WORK/bin/docker" <<'STUB'
#!/bin/bash
echo "$*" >> "$STUB_LOG"
case $1 in
    pull) echo "pull progress"; exit "${STUB_PULL_RC:-0}" ;;
    image) exit "${STUB_INSPECT_RC:-0}" ;;
    compose) exit "${STUB_COMPOSE_RC:-0}" ;;
    run)
        while [[ $# -gt 0 && $1 != update ]]; do shift; done
        [[ $# -gt 0 ]] || exit 98
        shift
        case $1 in
            check) echo "report"; exit "${STUB_CHECK_RC:-10}" ;;
            expect) echo "${STUB_EXPECT:-a:b}"; exit 0 ;;
            apply) exit "${STUB_APPLY_RC:-0}" ;;
            migrate) [[ -z "${STUB_MIGRATE_OUT:-}" ]] || echo "$STUB_MIGRATE_OUT"; exit "${STUB_MIGRATE_RC:-0}" ;;
        esac
        ;;
esac
exit 99
STUB
chmod +x "$WORK/bin/docker"

fails=0
LOG="$WORK/log"
RC=0

PENDING_FILE="$WORK/dir/.update-restart-pending"

# reset: clears the log and the restart marker; PENDING=1 sets the marker for the case.
reset() {
    : > "$LOG"
    RC=0
    rm -f "$PENDING_FILE"
    [[ -z "${PENDING:-}" ]] || touch "$PENDING_FILE"
}

# run_wrapper <wrapper args...>; the environment of the case is set by the caller.
run_wrapper() {
    reset
    PATH="$WORK/bin:$PATH" STUB_LOG="$LOG" EDULUTION_UPDATE_DIR="$WORK/dir" \
        EDULUTION_UPDATE_SKIP_ROOT_CHECK=1 bash "$WRAPPER" "$@" > "$WORK/out" 2>&1 || RC=$?
}

# run_split <wrapper args...>: like run_wrapper, but keeps stdout apart in $WORK/stdout.
run_split() {
    reset
    PATH="$WORK/bin:$PATH" STUB_LOG="$LOG" EDULUTION_UPDATE_DIR="$WORK/dir" \
        EDULUTION_UPDATE_SKIP_ROOT_CHECK=1 bash "$WRAPPER" "$@" > "$WORK/stdout" 2> "$WORK/stderr" || RC=$?
    cat "$WORK/stdout" "$WORK/stderr" > "$WORK/out"
}

# expect_case <name> <condition...>: runs the condition and prints one line.
expect_case() {
    local name=$1
    shift
    if "$@"; then
        echo "ok   $name"
    else
        echo "FAIL $name"
        sed 's/^/     /' "$WORK/out" "$LOG"
        fails=$((fails + 1))
    fi
}

logged() { grep -q -- "$1" "$LOG"; }
not_logged() { ! grep -q -- "$1" "$LOG"; }
rc_is() { [[ $RC -eq $1 ]]; }

answer() { printf '%s\n' "$@" > "$WORK/tty"; export EDULUTION_UPDATE_TTY="$WORK/tty"; }

declined() { rc_is 2 && not_logged "update apply" && not_logged "compose"; }
answer n
run_wrapper
expect_case "answer n changes nothing" declined

accepted() {
    rc_is 0 && logged "update apply --yes --expect=a:b" && logged "compose --project-directory $WORK/dir/ pull" \
        && logged "compose --project-directory $WORK/dir/ up -d" && [[ ! -e $PENDING_FILE ]]
}
answer j
run_wrapper
expect_case "answer j applies, pulls and restarts" accepted

compose_only() {
    rc_is 0 && logged "update apply --yes --expect=a:b" && not_logged "compose" && [[ -e $PENDING_FILE ]] \
        && grep -q "up -d" "$WORK/out"
}
run_wrapper --compose-only --yes
expect_case "--compose-only --yes skips compose" compose_only

modified_no_discard() { rc_is 20 && not_logged "update apply"; }
STUB_CHECK_RC=20 run_wrapper --yes
expect_case "check 20 with --yes needs --discard-local-changes" modified_no_discard

modified_discard() { rc_is 0 && logged "update apply --yes --expect=a:b --discard-local-changes"; }
STUB_CHECK_RC=20 run_wrapper --yes --discard-local-changes
expect_case "check 20 with --yes --discard-local-changes applies" modified_discard

discard_question() { rc_is 0 && logged "--discard-local-changes"; }
answer j j
STUB_CHECK_RC=20 run_wrapper
expect_case "check 20 asks the second question" discard_question

discard_declined() { rc_is 2 && not_logged "update apply"; }
answer j n
STUB_CHECK_RC=20 run_wrapper
expect_case "declining the discard question changes nothing" discard_declined

pull_failed() { rc_is 0 && logged "update apply" && logged "image inspect" && grep -q "lokale Image" "$WORK/out"; }
STUB_PULL_RC=1 run_wrapper --yes
expect_case "failed pull continues with the local image" pull_failed

no_image() { rc_is 1 && not_logged "run "; }
STUB_PULL_RC=1 STUB_INSPECT_RC=1 run_wrapper --yes
expect_case "failed pull without local image aborts" no_image

blocked() { rc_is 30 && not_logged "update apply" && grep -q -- "--migration" "$WORK/out"; }
STUB_CHECK_RC=30 run_wrapper --yes
expect_case "check 30 names --migration and exits 30" blocked

current() { rc_is 0 && not_logged "update apply" && not_logged "compose"; }
STUB_CHECK_RC=0 run_wrapper --yes
expect_case "check 0 exits 0 without apply" current

pending_restart() { rc_is 0 && not_logged "update apply" && logged "compose --project-directory $WORK/dir/ up -d" && [[ ! -e $PENDING_FILE ]]; }
PENDING=1 STUB_CHECK_RC=0 run_wrapper
expect_case "check 0 with a pending restart restarts without asking" pending_restart

pending_compose_only() { rc_is 0 && not_logged "compose" && [[ -e $PENDING_FILE ]] && grep -q "up -d" "$WORK/out"; }
PENDING=1 STUB_CHECK_RC=0 run_wrapper --compose-only --yes
expect_case "check 0 with a pending restart and --compose-only names the commands" pending_compose_only

pending_check() { rc_is 10 && grep -q "Neustart" "$WORK/out"; }
PENDING=1 STUB_CHECK_RC=0 run_wrapper --check
expect_case "--check at 0 with a pending restart exits 10" pending_check

migrate_blocked() { rc_is 0 && logged "update migrate --id X --yes --expect=a:b" && not_logged "docker.sock"; }
STUB_CHECK_RC=30 run_wrapper --migration X --yes
expect_case "--migration X --yes at check 30 migrates without the Docker socket" migrate_blocked

token_dash() { rc_is 0 && logged "--expect=-:-"; }
STUB_EXPECT="-:-" run_wrapper --yes
expect_case "a token starting with a dash is passed with =" token_dash

no_tty() { rc_is 2 && not_logged "update apply" && not_logged "compose"; }
export EDULUTION_UPDATE_TTY="$WORK/missing"
run_wrapper
expect_case "unreadable TTY without --yes exits 2" no_tty

check_code() { rc_is 20 && logged "update check"; }
STUB_CHECK_RC=20 run_wrapper --check
expect_case "--check returns the check code" check_code

check_json() { rc_is 10 && logged "update check --json"; }
run_wrapper --check --json
expect_case "--check --json passes --json" check_json

json_stdout() { rc_is 10 && [[ "$(cat "$WORK/stdout")" == report ]] && grep -q "pull progress" "$WORK/stderr"; }
STUB_PULL_RC=1 run_split --version 2.2.0 --check --json
expect_case "--check --json prints only the container's stdout on stdout" json_stdout

# Backups are named after the local time.
localtime() {
    rc_is 0 && { [[ ! -e /etc/localtime ]] \
        || [[ $(grep -c "^run .*-v /etc/localtime:/etc/localtime:ro .*python -m update" "$LOG") -eq 3 ]]; }
}
run_wrapper --yes --compose-only
expect_case "the container gets the host's local time" localtime

restart_failed() {
    rc_is 1 && grep -q "docker-compose-backups" "$WORK/out" && grep -q "up -d" "$WORK/out" && [[ -e $PENDING_FILE ]]
}
STUB_COMPOSE_RC=1 run_wrapper --yes
expect_case "failed restart exits 1 and names the backups" restart_failed

apply_failed() { rc_is 4 && not_logged "compose"; }
STUB_APPLY_RC=4 run_wrapper --yes
expect_case "apply errors pass through" apply_failed

for code in 1 3 4 5; do
    check_error() { rc_is "$code" && not_logged "update apply" && not_logged "compose"; }
    STUB_CHECK_RC=$code run_wrapper --yes
    expect_case "check $code aborts with that code" check_error
done

migrate_chain() {
    rc_is 0 && logged "compose --project-directory $WORK/dir/ pull" && logged "compose --project-directory $WORK/dir/ up -d" \
        && grep -q "Weitere Migration nötig: 0099-b" "$WORK/out" && grep -q "Migration 0098-a abgeschlossen." "$WORK/out"
}
STUB_CHECK_RC=30 STUB_MIGRATE_OUT="Weitere Migration nötig: 0099-b" run_wrapper --migration 0098-a --yes
expect_case "--migration with a further gating major exits 0, restarts and names it" migrate_chain

downgrade() { rc_is 5 && not_logged "update apply" && grep -q -- "--version" "$WORK/out"; }
STUB_CHECK_RC=5 run_wrapper --yes
expect_case "check 5 names --version and exits 5" downgrade
STUB_CHECK_RC=5 run_wrapper --check
expect_case "--check at 5 names --version and exits 5" downgrade

migrate_current() { rc_is 0 && logged "update migrate --id X --yes --expect=a:b"; }
STUB_CHECK_RC=0 run_wrapper --migration X --yes
expect_case "--migration X at check 0 migrates" migrate_current

migrate_discard() { rc_is 0 && logged "update migrate --id X --yes --expect=a:b --discard-local-changes"; }
STUB_CHECK_RC=20 run_wrapper --migration X --yes --discard-local-changes
expect_case "--migration at check 20 passes --discard-local-changes" migrate_discard
answer j j
STUB_CHECK_RC=20 run_wrapper --migration X
expect_case "--migration at check 20 interactive passes --discard-local-changes" migrate_discard

migrate_no_discard() { rc_is 20 && not_logged "update migrate"; }
STUB_CHECK_RC=20 run_wrapper --migration X --yes
expect_case "--migration at check 20 with --yes needs --discard-local-changes" migrate_no_discard

info_10() { grep -q "${WORK}/dir/docker-compose-backups/" "$WORK/out" && ! grep -q "docker-compose.override.yml" "$WORK/out"; }
run_wrapper --yes
expect_case "backup location is shown before applying" info_10

info_20() { grep -q "${WORK}/dir/docker-compose-backups/" "$WORK/out" && grep -q "docker-compose.override.yml" "$WORK/out"; }
answer n
STUB_CHECK_RC=20 run_wrapper
expect_case "check 20 shows backups and override hint before asking" info_20
STUB_CHECK_RC=20 run_wrapper --yes
expect_case "check 20 --yes exit message has the override hint" info_20

expect_first() { rc_is 0 && [[ $(grep -o "update \(expect\|check\)" "$LOG" | head -1) == "update expect" ]]; }
run_wrapper --yes
expect_case "the token is taken before the check is shown" expect_first

json_alone() { rc_is 2 && not_logged "run "; }
run_wrapper --json
expect_case "--json without --check exits 2" json_alone

if [[ $fails -ne 0 ]]; then
    echo "$fails case(s) failed"
    exit 1
fi
echo "all cases passed"
