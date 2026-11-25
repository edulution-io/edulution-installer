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
# docker compose config is logged apart, so "compose" in the log still means pull or up.
if [[ $1 == compose && " $* " == *" config "* ]]; then
    echo "$*" >> "$STUB_LOG.config"
    [[ -z "${STUB_RESOLVED_CONFIG_RC:-}" ]] || exit "$STUB_RESOLVED_CONFIG_RC"
    echo '{"services": {"edu-api": {"environment": {}}}}'
    exit 0
fi
echo "$*" >> "$STUB_LOG"
case $1 in
    pull)
        echo "pull progress"
        [[ -z "${STUB_PULL_FAIL:-}" || $2 != *"$STUB_PULL_FAIL" ]] || exit 1
        exit "${STUB_PULL_RC:-0}"
        ;;
    image) exit "${STUB_INSPECT_RC:-0}" ;;
    compose) exit "${STUB_COMPOSE_RC:-0}" ;;
    run)
        if [[ -n "${STUB_NO_MODULE:-}" ]]; then
            echo "ModuleNotFoundError: No module named 'update'" >&2
            exit 1
        fi
        [[ "$*" != *"python -c import update"* ]] || exit 0
        while [[ $# -gt 0 && $1 != update ]]; do
            # What the container would find: mode and content of the resolved config while it runs.
            if [[ $1 == -e && ${2:-} == EDULUTION_UPDATE_RESOLVED_CONFIG=/edulution-ui/* ]]; then
                f="$EDULUTION_UPDATE_DIR/${2#*=/edulution-ui/}"
                if [[ -s $f ]]; then echo "seen $(stat -c %a "$f") $(cat "$f")"; else echo "seen missing"; fi >> "$STUB_LOG.seen"
            fi
            shift
        done
        [[ $# -gt 0 ]] || exit 98
        shift
        case $1 in
            check)
                echo "report"
                exit "${STUB_CHECK_RC:-10}"
                ;;
            restart-check) exit "${STUB_RESTART_CHECK_RC:-0}" ;;
            expect)
                # A second expect sees the files as apply left them.
                if [[ -n "${STUB_EXPECT_AFTER:-}" && $(grep -c "update expect" "$STUB_LOG") -gt 1 ]]; then
                    echo "$STUB_EXPECT_AFTER"
                else
                    echo "${STUB_EXPECT:-a:b}"
                fi
                exit 0
                ;;
            apply)
                # Simulates the wrapper being stopped right after apply wrote the files.
                [[ -z "${STUB_APPLY_KILL:-}" ]] || kill "-$STUB_APPLY_KILL" "$PPID"
                exit "${STUB_APPLY_RC:-0}"
                ;;
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

# reset: clears the log and the restart marker; PENDING=1 sets an empty marker (scripts before 2.2.3),
# PENDING=<version> one naming the release that wrote the files.
reset() {
    : > "$LOG"
    : > "$LOG.seen"
    RC=0
    rm -f "$PENDING_FILE"
    case ${PENDING:-} in
        "") ;;
        1) touch "$PENDING_FILE" ;;
        *) printf '%s\n' "$PENDING" > "$PENDING_FILE" ;;
    esac
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

pending_check() { rc_is 0 && logged "update check --json --restart-pending"; }
PENDING=1 STUB_CHECK_RC=0 run_wrapper --check --json
expect_case "--check passes a pending restart to the check" pending_check

no_pending_check() { rc_is 0 && not_logged "restart-pending"; }
STUB_CHECK_RC=0 run_wrapper --check
expect_case "--check without a pending restart passes no flag" no_pending_check

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

apply_failed() { rc_is 4 && not_logged "compose" && [[ ! -e $PENDING_FILE ]]; }
STUB_APPLY_RC=4 run_wrapper --yes
expect_case "apply errors pass through and leave no pending restart" apply_failed

apply_failed_keeps() { rc_is 4 && [[ -e $PENDING_FILE ]]; }
PENDING=1 STUB_APPLY_RC=4 run_wrapper --yes
expect_case "an apply refusal keeps an earlier pending restart" apply_failed_keeps

apply_error() { rc_is 1 && not_logged "compose" && [[ -e $PENDING_FILE ]]; }
STUB_APPLY_RC=1 STUB_EXPECT_AFTER=c:d run_wrapper --yes
expect_case "an apply error after writing files keeps the restart pending" apply_error

apply_error_clean() { rc_is 1 && not_logged "compose" && [[ ! -e $PENDING_FILE ]]; }
STUB_APPLY_RC=1 run_wrapper --yes
expect_case "an apply error before writing files leaves no pending restart" apply_error_clean

PENDING=1 STUB_APPLY_RC=1 run_wrapper --yes
expect_case "an apply error keeps an earlier pending restart" apply_error

old_image() { rc_is 1 && not_logged "update apply" && grep -q "neuere Version" "$WORK/out"; }
STUB_NO_MODULE=1 run_wrapper --version 2.0.0 --yes
expect_case "an image without the update tool names --version" old_image
STUB_NO_MODULE=1 run_wrapper --version 2.0.0 --check
expect_case "--check with an image without the update tool names --version" old_image

# The braces keep bash's own report about the stopped wrapper out of the test output.
for signal in TERM:143 INT:130 HUP:129; do
    interrupted() { rc_is "${signal#*:}" && logged "update apply" && not_logged "compose" && [[ -e $PENDING_FILE ]]; }
    { STUB_APPLY_KILL=${signal%:*} run_wrapper --yes; } 2>/dev/null
    expect_case "SIG${signal%:*} after apply keeps the restart pending and exits ${signal#*:}" interrupted
done

for code in 1 3 4 5 6; do
    check_error() {
        rc_is "$code" && not_logged "update apply" && not_logged "compose" && ! grep -q "neuere Version" "$WORK/out"
    }
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

locked_out() { rc_is 3 && not_logged "update expect" && not_logged "update apply" && [[ -e $PENDING_FILE ]]; }
exec 8> "$WORK/dir/.update-script.lock"
flock 8
PENDING=1 run_wrapper --yes
exec 8>&-
expect_case "a second script exits 3 and leaves the restart marker alone" locked_out

json_alone() { rc_is 2 && not_logged "run "; }
run_wrapper --json
expect_case "--json without --check exits 2" json_alone

# A released script, stamped as stamp-installer.sh does (with a tag instead of a digest).
STAMPED="$WORK/update-2.2.3"
sed -e 's|^EDULUTION_INSTALLER_IMAGE=.*|EDULUTION_INSTALLER_IMAGE="ghcr.io/edulution-io/edulution-installer:2.2.3"|' \
    -e 's|^EDULUTION_INSTALLER_VERSION=.*|EDULUTION_INSTALLER_VERSION="2.2.3"|' "$WRAPPER" > "$STAMPED"

run_stamped() {
    reset
    PATH="$WORK/bin:$PATH" STUB_LOG="$LOG" EDULUTION_UPDATE_DIR="$WORK/dir" \
        EDULUTION_UPDATE_SKIP_ROOT_CHECK=1 bash "$STAMPED" "$@" > "$WORK/out" 2>&1 || RC=$?
}

records_version() { rc_is 0 && [[ $(cat "$PENDING_FILE") == 2.2.3 ]]; }
run_stamped --compose-only --yes
expect_case "--compose-only records the script's version in the restart marker" records_version

restart_failed_records() { rc_is 1 && [[ $(cat "$PENDING_FILE") == 2.2.3 ]]; }
STUB_COMPOSE_RC=1 run_stamped --yes
expect_case "a failed restart leaves the marker with the script's version" restart_failed_records

# The check before the restart runs with the newer of the two releases, here the script's own.
follows_recorded() {
    rc_is 0 && logged "pull ghcr.io/edulution-io/edulution-installer:2.2.2" \
        && logged "edulution-installer:2.2.2 python -m update check$" \
        && not_logged "edulution-installer:2.2.3 python -m update check" && not_logged "update apply" \
        && logged "edulution-installer:2.2.3 python -m update restart-check" \
        && logged "compose --project-directory $WORK/dir/ up -d" && [[ ! -e $PENDING_FILE ]]
}
PENDING=2.2.2 STUB_CHECK_RC=0 run_stamped --yes
expect_case "a pending restart from 2.2.2 is finished with 2.2.2, not the newer release" follows_recorded

check_follows_recorded() { rc_is 10 && logged "pull ghcr.io/edulution-io/edulution-installer:2.2.2" && logged "update check --restart-pending"; }
PENDING=2.2.2 run_stamped --check
expect_case "--check with a pending restart checks against the recorded release" check_follows_recorded

other_version_refused() {
    rc_is 2 && not_logged "pull" && not_logged "run " && grep -q -- "--version 2.2.2" "$WORK/out" \
        && grep -q -- "--version 2.2.4 --compose-only" "$WORK/out" && [[ $(cat "$PENDING_FILE") == 2.2.2 ]]
}
PENDING=2.2.2 run_stamped --version 2.2.4 --yes
expect_case "--version other than the recorded one is refused while a restart is pending" other_version_refused

same_version() { rc_is 0 && logged "pull ghcr.io/edulution-io/edulution-installer:2.2.2" && [[ ! -e $PENDING_FILE ]]; }
PENDING=2.2.2 STUB_CHECK_RC=0 run_stamped --version 2.2.2 --yes
expect_case "--version equal to the recorded one finishes the restart" same_version

own_version() { rc_is 0 && logged "pull ghcr.io/edulution-io/edulution-installer:2.2.3"; }
PENDING=1 STUB_CHECK_RC=0 run_stamped --yes
expect_case "an empty marker from an earlier script uses the script's own release" own_version
PENDING='2.2.2;x' STUB_CHECK_RC=0 run_stamped --yes
expect_case "a marker that names no release is ignored" own_version

hint_clears_marker() { grep -q "up -d && rm -f $WORK/dir/.update-restart-pending" "$WORK/out"; }
run_stamped --compose-only --yes
expect_case "the restart hint removes the marker as well" hint_clears_marker

names_newer() { follows_recorded && grep -q "Version 2.2.3 ist verfügbar" "$WORK/out"; }
PENDING=2.2.2 STUB_CHECK_RC=0 run_stamped --yes
expect_case "finishing an older pending restart names the newer release" names_newer

compose_only_own() {
    rc_is 0 && logged "pull ghcr.io/edulution-io/edulution-installer:2.2.3" && not_logged "edulution-installer:2.2.2" \
        && logged "update apply" && [[ $(cat "$PENDING_FILE") == 2.2.3 ]]
}
PENDING=2.2.2 run_stamped --compose-only --yes
expect_case "--compose-only writes its own release despite an older marker" compose_only_own

check_other_version() { rc_is 10 && logged "pull ghcr.io/edulution-io/edulution-installer:2.2.4"; }
PENDING=2.2.2 run_stamped --version 2.2.4 --check --json
expect_case "--check with another --version checks that release" check_other_version

PENDING=$'2.2.2\r' STUB_CHECK_RC=0 run_stamped --yes
expect_case "a marker with CRLF is read" follows_recorded

restored() { rc_is 4 && [[ -e $PENDING_FILE && ! -s $PENDING_FILE ]]; }
PENDING=1 STUB_APPLY_RC=4 run_stamped --yes
expect_case "an apply that wrote nothing restores the earlier marker" restored

restored_release() { rc_is 4 && logged "update apply" && [[ $(cat "$PENDING_FILE") == 2.2.2 ]]; }
PENDING=2.2.2 STUB_APPLY_RC=4 run_stamped --compose-only --yes
expect_case "an apply that wrote nothing restores the release the earlier marker names" restored_release

locked_before_marker() {
    rc_is 3 && not_logged "pull" && ! grep -q "steht noch aus" "$WORK/out" && [[ $(cat "$PENDING_FILE") == 2.2.2 ]]
}
exec 8> "$WORK/dir/.update-script.lock"
flock 8
PENDING=2.2.2 run_stamped --yes
exec 8>&-
expect_case "the lock is taken before the marker is read" locked_before_marker

pending_no_db_user() { rc_is 6 && not_logged "compose" && [[ -e $PENDING_FILE ]] && grep -q "MONGODB_USERNAME" "$WORK/out"; }
PENDING=1 STUB_CHECK_RC=0 STUB_RESTART_CHECK_RC=6 run_wrapper --yes
expect_case "a pending restart without a database user is not carried out" pending_no_db_user

pending_with_db_user() { rc_is 0 && logged "update restart-check" && logged "compose --project-directory $WORK/dir/ up -d"; }
PENDING=1 STUB_CHECK_RC=0 run_wrapper --yes
expect_case "a pending restart is checked once more and then carried out" pending_with_db_user

apply_refused_6() { rc_is 6 && not_logged "compose" && [[ ! -e $PENDING_FILE ]]; }
STUB_APPLY_RC=6 run_wrapper --yes
expect_case "apply refusing with 6 leaves no pending restart" apply_refused_6

CONFIG_ENV="-e EDULUTION_UPDATE_RESOLVED_CONFIG=/edulution-ui/.update-resolved-config."
no_config_left() { ! compgen -G "$WORK/dir/.update-resolved-config*" > /dev/null; }
# Every container run that got the file found it readable by root only and filled.
config_seen() {
    [[ $(grep -c "" "$LOG.seen") -eq $1 ]] && ! grep -qv "^seen 600 {" "$LOG.seen"
}

passes_resolved_config() {
    rc_is 0 && logged "$CONFIG_ENV.* update check$" && logged "$CONFIG_ENV.* update apply --yes --expect=a:b$" \
        && logged "$CONFIG_ENV.* update restart-check$" && config_seen 3 && no_config_left
}
run_wrapper --yes
expect_case "the resolved Compose config reaches check, apply and the restart check, and is removed" passes_resolved_config

no_option() { ! grep -q -- "--resolved-config" "$LOG"; }
no_option_for_old_images() { rc_is 0 && no_option; }
run_wrapper --yes
expect_case "the resolved Compose config goes in the environment, not as an option older images reject" \
    no_option_for_old_images

check_passes_config() { logged "$CONFIG_ENV.* update check$" && config_seen 1 && no_config_left; }
STUB_CHECK_RC=0 run_wrapper --check
expect_case "--check passes the resolved Compose config" check_passes_config

no_config() {
    rc_is 0 && not_logged "EDULUTION_UPDATE_RESOLVED_CONFIG" && config_seen 0 && no_config_left \
        && logged "compose --project-directory $WORK/dir/ up -d"
}
STUB_RESOLVED_CONFIG_RC=1 run_wrapper --yes
expect_case "without a Compose config the container gets no resolved config" no_config

touch "$WORK/dir/.update-resolved-config.json"
foreign_file_kept() { rc_is 0 && [[ -e "$WORK/dir/.update-resolved-config.json" ]]; }
STUB_CHECK_RC=0 run_wrapper --check
expect_case "a run leaves the resolved config of another run alone" foreign_file_kept
rm -f "$WORK/dir/.update-resolved-config.json"

restart_check_blocks() { rc_is 6 && logged "update apply" && not_logged "compose" && [[ -e $PENDING_FILE ]]; }
STUB_RESTART_CHECK_RC=6 run_wrapper --yes
expect_case "a restart check that reports 6 after apply keeps the restart pending" restart_check_blocks

preflight_failed() { rc_is 125 && not_logged "compose" && [[ -e $PENDING_FILE ]] && grep -q "Code 125" "$WORK/out"; }
PENDING=1 STUB_CHECK_RC=0 STUB_RESTART_CHECK_RC=125 run_wrapper --yes
expect_case "a restart check that does not run keeps the restart pending" preflight_failed

# An older release that wrote the files may not know the database check; this script's release does.
older_pending_no_db_user() {
    rc_is 6 && logged "edulution-installer:2.2.3 python -m update restart-check" \
        && not_logged "edulution-installer:2.2.2 python -m update restart-check" \
        && not_logged "compose" && [[ $(cat "$PENDING_FILE") == 2.2.2 ]]
}
PENDING=2.2.2 STUB_CHECK_RC=0 STUB_RESTART_CHECK_RC=6 run_stamped --yes
expect_case "a pending restart from an older release is checked by the script's own release" older_pending_no_db_user

older_version_no_db_user() {
    rc_is 6 && logged "edulution-installer:2.2.2 python -m update apply" \
        && logged "edulution-installer:2.2.3 python -m update restart-check" && not_logged "compose" \
        && [[ $(cat "$PENDING_FILE") == 2.2.2 ]]
}
STUB_RESTART_CHECK_RC=6 run_stamped --version 2.2.2 --yes
expect_case "--version with an older release is checked by the script's own release before the restart" \
    older_version_no_db_user

newer_checks_itself() {
    rc_is 0 && logged "edulution-installer:2.2.4 python -m update restart-check" && not_logged "edulution-installer:2.2.3" \
        && logged "compose --project-directory $WORK/dir/ up -d"
}
run_stamped --version 2.2.4 --yes
expect_case "--version with a newer release checks with that release" newer_checks_itself

own_image_missing() {
    rc_is 1 && not_logged "restart-check" && not_logged "compose" && [[ $(cat "$PENDING_FILE") == 2.2.2 ]] \
        && grep -q "Prüfung vor dem Neustart" "$WORK/out"
}
PENDING=2.2.2 STUB_CHECK_RC=0 STUB_PULL_FAIL=:2.2.3 STUB_INSPECT_RC=1 run_stamped --yes
expect_case "without the script's own image the restart is not carried out" own_image_missing

newer_pending() {
    rc_is 0 && logged "edulution-installer:2.3.0 python -m update restart-check" && not_logged "edulution-installer:2.2.3" \
        && ! grep -q "ist verfügbar" "$WORK/out"
}
PENDING=2.3.0 STUB_CHECK_RC=0 run_stamped --yes
expect_case "finishing a newer pending restart names no older release" newer_pending

# A --check races with a running update that removes the marker; an unreadable one stands in for that.
unreadable_marker() { rc_is 10 && [[ "$(cat "$WORK/stdout")" == report ]]; }
PENDING=2.2.2 reset
chmod 000 "$PENDING_FILE"
PATH="$WORK/bin:$PATH" STUB_LOG="$LOG" EDULUTION_UPDATE_DIR="$WORK/dir" EDULUTION_UPDATE_SKIP_ROOT_CHECK=1 \
    bash "$STAMPED" --check --json > "$WORK/stdout" 2> "$WORK/stderr" || RC=$?
cat "$WORK/stdout" "$WORK/stderr" > "$WORK/out"
chmod 600 "$PENDING_FILE"
expect_case "--check --json reports even if the marker cannot be read" unreadable_marker

compose_only_other() {
    rc_is 0 && logged "edulution-installer:2.2.4 python -m update apply" && not_logged "edulution-installer:2.2.2" \
        && [[ $(cat "$PENDING_FILE") == 2.2.4 ]]
}
PENDING=2.2.2 run_stamped --version 2.2.4 --compose-only --yes
expect_case "--compose-only with another --version replaces a pending restart, as the refusal says" compose_only_other

own_image_first() { rc_is 1 && not_logged "update expect" && not_logged "update apply" && [[ $(cat "$PENDING_FILE") == 2.2.2 ]]; }
PENDING=2.2.2 STUB_PULL_FAIL=:2.2.3 STUB_INSPECT_RC=1 run_stamped --yes
expect_case "without the script's own image nothing is written" own_image_first
own_image_first_version() { rc_is 1 && not_logged "update apply" && [[ ! -e $PENDING_FILE ]]; }
STUB_PULL_FAIL=:2.2.3 STUB_INSPECT_RC=1 run_stamped --version 2.2.2 --yes
expect_case "without the script's own image an older --version writes nothing" own_image_first_version

run_stamped_split() {
    reset
    PATH="$WORK/bin:$PATH" STUB_LOG="$LOG" EDULUTION_UPDATE_DIR="$WORK/dir" \
        EDULUTION_UPDATE_SKIP_ROOT_CHECK=1 bash "$STAMPED" "$@" > "$WORK/stdout" 2> "$WORK/stderr" || RC=$?
    cat "$WORK/stdout" "$WORK/stderr" > "$WORK/out"
}

check_older_blocked() {
    rc_is 6 && [[ "$(cat "$WORK/stdout")" == report ]] && grep -q "MONGODB_USERNAME" "$WORK/stderr" \
        && logged "edulution-installer:2.2.2 python -m update check --json --restart-pending" \
        && logged "edulution-installer:2.2.3 python -m update restart-check"
}
PENDING=2.2.2 STUB_RESTART_CHECK_RC=6 run_stamped_split --check --json
expect_case "--check with an older pending release reports 6 if the restart would be blocked" check_older_blocked

check_older_ok() { rc_is 10 && logged "edulution-installer:2.2.3 python -m update restart-check"; }
PENDING=2.2.2 run_stamped --check
expect_case "--check with an older pending release and a database user reports 10" check_older_ok

check_own_release() { rc_is 10 && not_logged "restart-check"; }
PENDING=1 run_stamped --check
expect_case "--check with the script's own release leaves the database user to its check" check_own_release

stale_marker() { rc_is 5 && grep -q "rm -f $WORK/dir/.update-restart-pending" "$WORK/out" && not_logged "update apply"; }
PENDING=2.2.2 STUB_CHECK_RC=5 run_stamped --yes
expect_case "a marker older than the files names its removal" stale_marker
PENDING=2.2.2 STUB_CHECK_RC=5 run_stamped --check
expect_case "--check with a marker older than the files names its removal" stale_marker

migrate_recorded() {
    rc_is 0 && logged "edulution-installer:2.2.2 python -m update migrate --id X" \
        && logged "edulution-installer:2.2.3 python -m update restart-check" && [[ ! -e $PENDING_FILE ]]
}
PENDING=2.2.2 STUB_CHECK_RC=30 run_stamped --migration X --yes
expect_case "--migration with a pending older restart migrates with that release and checks with its own" migrate_recorded

# As released: the script's own image is pinned by digest, not by tag.
DIGEST="sha256:$(printf '%064d' 0)"
DIGEST_SCRIPT="$WORK/update-digest"
sed -e "s|^EDULUTION_INSTALLER_IMAGE=.*|EDULUTION_INSTALLER_IMAGE=\"ghcr.io/edulution-io/edulution-installer@${DIGEST}\"|" \
    -e 's|^EDULUTION_INSTALLER_VERSION=.*|EDULUTION_INSTALLER_VERSION="2.2.3"|' "$WRAPPER" > "$DIGEST_SCRIPT"
run_digest() {
    reset
    PATH="$WORK/bin:$PATH" STUB_LOG="$LOG" EDULUTION_UPDATE_DIR="$WORK/dir" \
        EDULUTION_UPDATE_SKIP_ROOT_CHECK=1 bash "$DIGEST_SCRIPT" "$@" > "$WORK/out" 2>&1 || RC=$?
}
digest_check() { rc_is 0 && logged "pull ghcr.io/edulution-io/edulution-installer@$DIGEST" && logged "@$DIGEST python -m update restart-check"; }
PENDING=2.2.2 STUB_CHECK_RC=0 run_digest --yes
expect_case "a released script checks an older pending restart with its pinned image" digest_check
digest_same() { rc_is 0 && not_logged "@sha256" && logged "edulution-installer:2.2.3 python -m update restart-check"; }
run_digest --version 2.2.3 --yes
expect_case "--version naming the script's own release uses that tag alone" digest_same

if [[ $fails -ne 0 ]]; then
    echo "$fails case(s) failed"
    exit 1
fi
echo "all cases passed"
