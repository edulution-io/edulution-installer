#!/bin/bash
# Runs vm-test against stub virsh, ip and ssh; creates no VMs. Usage: bash vm-test.test.sh
set -u

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# build takes REPO_ROOT from the script's place, so the script gets a repository of its own.
REPO="$WORK/repo"
mkdir -p "$REPO/tools/vm-test" "$WORK/bin"
cp "$HERE/vm-test" "$REPO/tools/vm-test/vm-test"
VMTEST="$REPO/tools/vm-test/vm-test"
git -C "$REPO" init -q
git -C "$REPO" -c user.name=t -c user.email=t@t commit -q --allow-empty -m a
COMMIT_A=$(git -C "$REPO" rev-parse --short HEAD)
git -C "$REPO" -c user.name=t -c user.email=t@t commit -q --allow-empty -m b
COMMIT_B=$(git -C "$REPO" rev-parse --short HEAD)

cat > "$WORK/bin/virsh" <<'STUB'
#!/bin/bash
[[ $1 != -c ]] || shift 2
echo "virsh $*" >> "$STUB_LOG"
d=$STUB_VIRT
case $1 in
    list) ls "$d/domains" ;;
    net-list) ls "$d/networks" ;;
    pool-list) ls "$d/volumes" ;;
    pool-info) [[ -d $d/volumes/$2 ]] ;;
    vol-list)
        printf ' Name Path\n----------\n'
        for f in "$d/volumes/$2"/*; do [[ ! -e $f ]] || echo " ${f##*/} /x"; done
        ;;
    domstate) [[ -e $d/domains/$2 ]] && echo running ;;
    destroy) [[ -e $d/domains/$2 ]] ;;
    undefine) rm "$d/domains/$2" ;;
    vol-info) [[ -e $d/volumes/$3/$4 ]] ;;
    vol-delete) rm "$d/volumes/$3/$4" ;;
    net-info) [[ -e $d/networks/$2 ]] ;;
    net-destroy) true ;;
    net-undefine) rm "$d/networks/$2" ;;
    *) exit 99 ;;
esac
STUB

cat > "$WORK/bin/ip" <<'STUB'
#!/bin/bash
case "$*" in
    *"route show table all match"*) [[ -z ${STUB_ROUTE_MATCH:-} ]] || echo "$STUB_ROUTE_MATCH" ;;
esac
exit 0
STUB

cat > "$WORK/bin/ssh" <<'STUB'
#!/bin/bash
host=""
while [[ $# -gt 0 && $1 != edutest@* ]]; do shift; done
host=$1
shift
echo "ssh $host $*" >> "$STUB_LOG"
case "$*" in
    *"tar -x"*) cat > /dev/null ;;
    *"bash -s --"*node:*) cat > /dev/null; exit "${STUB_BUILD_RC:-0}" ;;
    *"test -e /root/installer.log"*) exit 1 ;;
    *"test -e /root/installer.rc"*) exit 1 ;;
    *"bash -s --"*) cat > /dev/null ;;
    *"grep -m1"*) echo "https://${host#edutest@}:443/?token=abc" ;;
esac
exit 0
STUB
# up must never get as far as downloading the cloud image.
cat > "$WORK/bin/curl" <<'STUB'
#!/bin/bash
echo "curl $*" >> "$STUB_LOG"
exit 1
STUB
chmod +x "$WORK/bin/"*

fails=0
LOG="$WORK/log"
RC=0
STATE_DIR="$WORK/state"
RUN_DIR="$STATE_DIR/run"

# reset <domains...> -- <volumes in pool default...>: an empty host with these libvirt objects.
reset() {
    : > "$LOG"
    RC=0
    rm -rf "$WORK/virt" "$STATE_DIR"
    mkdir -p "$WORK/virt/domains" "$WORK/virt/networks" "$WORK/virt/volumes/default" "$WORK/virt/volumes/testing"
    local in_volumes=0 item
    for item in "$@"; do
        if [[ $item == -- ]]; then in_volumes=1; continue; fi
        if [[ $in_volumes -eq 1 ]]; then touch "$WORK/virt/volumes/$item"; else touch "$WORK/virt/domains/$item"; fi
    done
}

# own_run <resource lines...>: a run of this state directory that created these objects.
own_run() {
    mkdir -p "$RUN_DIR"
    touch "$RUN_DIR/id_ed25519"
    printf '%s\n' "$@" > "$RUN_DIR/resources"
}

run_vmtest() {
    RC=0
    PATH="$WORK/bin:$PATH" STUB_LOG="$LOG" STUB_VIRT="$WORK/virt" VM_TEST_HOME="$STATE_DIR" \
        bash "$VMTEST" "$@" > "$WORK/out" 2>&1 || RC=$?
}

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
exists() { [[ -e "$WORK/virt/$1" ]]; }

foreign_kept() {
    [[ $RC -ne 0 ]] && not_logged "undefine" && not_logged "vol-delete" && exists domains/edutest-edu \
        && exists volumes/default/edutest-base.qcow2 && grep -q -- "--all" "$WORK/out"
}
reset edutest-edu -- default/edutest-base.qcow2
run_vmtest down
expect_case "down without a run of its own leaves objects named edutest alone" foreign_kept

only_recorded() {
    [[ $RC -eq 0 ]] && ! exists domains/edutest-edu && ! exists volumes/default/edutest-edu.qcow2 \
        && ! exists volumes/default/edutest-base.qcow2 && exists volumes/default/edutest-other.qcow2 \
        && exists domains/edutest-foreign && [[ ! -e $RUN_DIR ]] \
        && [[ $(grep -n "vol-delete" "$LOG" | head -1) == *edutest-edu.qcow2* ]]
}
reset edutest-edu edutest-foreign -- default/edutest-base.qcow2 default/edutest-edu.qcow2 default/edutest-other.qcow2
own_run "volume default edutest-base.qcow2" "volume default edutest-edu.qcow2" "domain edutest-edu"
run_vmtest down
expect_case "down removes what the run recorded, overlays before the base image, and nothing else" only_recorded

partial() { [[ $RC -eq 0 ]] && ! exists volumes/default/edutest-base.qcow2 && not_logged "undefine"; }
reset -- default/edutest-base.qcow2
own_run "volume default edutest-base.qcow2" "volume default edutest-edu.qcow2"
run_vmtest down
expect_case "down after a partial up removes what exists of the recorded objects" partial

early_stop() { [[ $RC -eq 0 ]] && exists domains/edutest-edu && not_logged "undefine" && [[ ! -e $RUN_DIR ]]; }
reset edutest-edu
mkdir -p "$RUN_DIR"
run_vmtest down
expect_case "down after an up that created nothing removes the run's files and leaves other objects" early_stop

recorded_pool() { [[ $RC -eq 0 ]] && ! exists volumes/testing/edutest-edu.qcow2 && logged "vol-delete --pool testing"; }
reset -- testing/edutest-edu.qcow2
own_run "volume testing edutest-edu.qcow2"
printf 'subnet=10.77.0\npool=testing\n' > "$RUN_DIR/settings"
run_vmtest down
expect_case "down uses the pool the run recorded, without VM_TEST_POOL" recorded_pool

all_removes() {
    [[ $RC -eq 0 ]] && ! exists domains/edutest-edu && ! exists volumes/default/edutest-base.qcow2 \
        && ! exists volumes/default/edutest-edu.qcow2 \
        && [[ $(grep -n "vol-delete" "$LOG" | tail -1) == *edutest-base.qcow2* ]]
}
reset edutest-edu -- default/edutest-base.qcow2 default/edutest-edu.qcow2
run_vmtest down --all
expect_case "down --all removes everything named edutest, the base image last" all_removes

settings_subnet() { [[ $RC -eq 0 ]] && grep -q "10.78.0.20" "$WORK/out" && ! grep -q "10.77.0" "$WORK/out"; }
reset
own_run
printf 'subnet=10.78.0\npool=default\n' > "$RUN_DIR/settings"
echo pw > "$RUN_DIR/lmn-root-password"
run_vmtest status
expect_case "status uses the subnet of the run, without VM_TEST_SUBNET" settings_subnet

covering_route() {
    [[ $RC -ne 0 ]] && grep -q "10.0.0.0/8 dev tun0" "$WORK/out" && [[ ! -e $RUN_DIR ]] && not_logged "virsh" && not_logged "curl"
}
reset
STUB_ROUTE_MATCH="10.0.0.0/8 dev tun0 scope link" run_vmtest up
expect_case "up refuses a subnet that a wider route covers" covering_route

bad_subnet() { [[ $RC -ne 0 ]] && grep -q "three octets" "$WORK/out"; }
reset
VM_TEST_SUBNET=10.78 run_vmtest up
expect_case "up refuses a malformed VM_TEST_SUBNET" bad_subnet

failed_rebuild() {
    [[ $RC -eq 0 ]] && [[ $(cat "$RUN_DIR/image-tag") == "vmtest-$COMMIT_A" ]] \
        && logged "/root/vm-test-src/vmtest-$COMMIT_A/apps/public-page/public/installer.*--version.*vmtest-$COMMIT_A" \
        && not_logged "$COMMIT_B"
}
reset
own_run
echo pw > "$RUN_DIR/lmn-root-password"
run_vmtest build "$COMMIT_A"
first=$RC
STUB_BUILD_RC=1 run_vmtest build "$COMMIT_B"
second=$RC
: > "$LOG"
run_vmtest install --local
[[ $first -eq 0 && $second -ne 0 ]] || RC=1
expect_case "after a failed rebuild, install --local uses the last good build and its own sources" failed_rebuild

if [[ $fails -ne 0 ]]; then
    echo "$fails case(s) failed"
    exit 1
fi
echo "all cases passed"
