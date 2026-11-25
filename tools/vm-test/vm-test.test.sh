#!/bin/bash
# Runs vm-test against stub virsh, ip, ssh, curl and xorriso; creates no VMs. Usage: bash vm-test.test.sh
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

# A libvirt host in files: domains/<name> and networks/<name> hold the UUID, volumes/<pool>/<name>.
cat > "$WORK/bin/virsh" <<'STUB'
#!/bin/bash
[[ $1 != -c ]] || shift 2
echo "virsh $*" >> "$STUB_LOG"
[[ " ${STUB_VIRSH_FAIL:-} " != *" $1 "* ]] || exit 1
d=$STUB_VIRT
xml_name() { sed -n 's|.*<name>\(.*\)</name>.*|\1|p' "$1" | head -1; }
case $1 in
    list) ls "$d/domains" ;;
    net-list) ls "$d/networks" ;;
    pool-list) ls "$d/volumes" ;;
    pool-info) [[ -d $d/volumes/$2 ]] ;;
    pool-refresh) true ;;
    vol-list)
        printf ' Name Path\n----------\n'
        for f in "$d/volumes/$2"/*; do [[ ! -e $f ]] || echo " ${f##*/} /x"; done
        ;;
    vol-create-as) touch "$d/volumes/$2/$3" ;;
    vol-upload) true ;;
    vol-delete) rm "$d/volumes/$3/$4" ;;
    define) n=$(xml_name "$2"); echo "u-$n" > "$d/domains/$n" ;;
    start) true ;;
    domstate) [[ -e $d/domains/$2 ]] && echo running ;;
    domuuid) cat "$d/domains/$2" ;;
    destroy) [[ -e $d/domains/$2 ]] ;;
    undefine) rm "$d/domains/$2" ;;
    net-define) n=$(xml_name "$2"); echo "u-$n" > "$d/networks/$n" ;;
    net-start) true ;;
    net-uuid) cat "$d/networks/$2" ;;
    net-destroy) true ;;
    net-undefine) rm "$d/networks/$2" ;;
    *) exit 99 ;;
esac
STUB

cat > "$WORK/bin/ip" <<'STUB'
#!/bin/bash
case "$*" in
    *"route show table all match"*) [[ -z ${STUB_ROUTE_MATCH:-} ]] || echo "$STUB_ROUTE_MATCH" ;;
    *"route show table all root"*) [[ -z ${STUB_ROUTE_ROOT:-} ]] || echo "$STUB_ROUTE_ROOT" ;;
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
    *"cloud-init status"*) echo "status: done" ;;
esac
exit 0
STUB

# Only the checksum list comes from "the network", and only where a case provides one.
cat > "$WORK/bin/curl" <<'STUB'
#!/bin/bash
echo "curl $*" >> "$STUB_LOG"
[[ -n ${STUB_SUMS:-} && " $* " == *"/SHA256SUMS "* ]] || exit 1
while [[ $1 != -o ]]; do shift; done
cp "$STUB_SUMS" "$2"
STUB

cat > "$WORK/bin/xorriso" <<'STUB'
#!/bin/bash
while [[ $1 != -output ]]; do shift; done
touch "$2"
STUB
chmod +x "$WORK/bin/"*

fails=0
LOG="$WORK/log"
RC=0
STATE_DIR="$WORK/state"
RUN_DIR="$STATE_DIR/run"
IMAGE=ubuntu-26.04-server-cloudimg-amd64.img

# reset <domains...> -- <pool/volume...>: a host with these libvirt objects; a domain's UUID is u-<name>.
reset() {
    : > "$LOG"
    RC=0
    rm -rf "$WORK/virt" "$STATE_DIR"
    mkdir -p "$WORK/virt/domains" "$WORK/virt/networks" "$WORK/virt/volumes/default" "$WORK/virt/volumes/testing"
    local in_volumes=0 item
    for item in "$@"; do
        if [[ $item == -- ]]; then in_volumes=1; continue; fi
        if [[ $in_volumes -eq 1 ]]; then
            touch "$WORK/virt/volumes/$item"
        else
            echo "u-$item" > "$WORK/virt/domains/$item"
        fi
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
        VM_TEST_KVM_DEVICE="$WORK/kvm" bash "$VMTEST" "$@" > "$WORK/out" 2>&1 || RC=$?
}
touch "$WORK/kvm"

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
# line_of <pattern>: number of the first log line that matches.
line_of() { grep -n -- "$1" "$LOG" | head -1 | cut -d: -f1; }

foreign_kept() {
    [[ $RC -ne 0 ]] && not_logged "undefine" && not_logged "vol-delete" && exists domains/edutest-edu \
        && exists volumes/default/edutest-base.qcow2 && grep -q -- "--all" "$WORK/out"
}
reset edutest-edu -- default/edutest-base.qcow2
run_vmtest down
expect_case "down without a run of its own leaves objects named edutest alone" foreign_kept

only_recorded() {
    [[ $RC -eq 0 ]] && ! exists domains/edutest-edu && ! exists volumes/default/edutest-1-edu.qcow2 \
        && ! exists volumes/default/edutest-1-base.qcow2 && exists volumes/default/edutest-2-edu.qcow2 \
        && exists domains/edutest-foreign && [[ ! -e $RUN_DIR ]] \
        && [[ $(line_of "vol-delete.*edutest-1-edu") -lt $(line_of "vol-delete.*edutest-1-base") ]] \
        && grep -q "edutest-foreign" "$WORK/out"
}
reset edutest-edu edutest-foreign -- default/edutest-1-base.qcow2 default/edutest-1-edu.qcow2 default/edutest-2-edu.qcow2
own_run "volume default edutest-1-base.qcow2" "volume default edutest-1-edu.qcow2" "domain edutest-edu u-edutest-edu"
run_vmtest down
expect_case "down removes what the run recorded, overlays before the base image, and names the rest" only_recorded

replaced() { [[ $RC -eq 0 ]] && exists domains/edutest-edu && not_logged "undefine" && [[ ! -e $RUN_DIR ]]; }
reset edutest-edu
own_run "domain edutest-edu u-from-an-earlier-run"
run_vmtest down
expect_case "down leaves a VM of the recorded name that another run created since" replaced

partial() { [[ $RC -eq 0 ]] && ! exists volumes/default/edutest-1-base.qcow2 && not_logged "undefine"; }
reset -- default/edutest-1-base.qcow2
own_run "volume default edutest-1-base.qcow2" "volume default edutest-1-edu.qcow2"
run_vmtest down
expect_case "down after a partial up removes what exists of the recorded objects" partial

early_stop() { [[ $RC -eq 0 ]] && exists domains/edutest-edu && not_logged "undefine" && [[ ! -e $RUN_DIR ]]; }
reset edutest-edu
mkdir -p "$RUN_DIR"
run_vmtest down
expect_case "down after an up that created nothing removes the run's files and leaves other objects" early_stop

kept_record() { [[ $RC -ne 0 ]] && [[ -f $RUN_DIR/resources ]] && exists volumes/default/edutest-1-edu.qcow2; }
reset -- default/edutest-1-edu.qcow2
own_run "volume default edutest-1-edu.qcow2"
STUB_VIRSH_FAIL=vol-delete run_vmtest down
expect_case "down keeps the record if an object cannot be removed" kept_record
retried() { [[ $RC -eq 0 ]] && ! exists volumes/default/edutest-1-edu.qcow2 && [[ ! -e $RUN_DIR ]]; }
run_vmtest down
expect_case "a second down finishes the job" retried

unreachable() { [[ $RC -ne 0 ]] && [[ -f $RUN_DIR/resources ]] && exists domains/edutest-edu; }
reset edutest-edu
own_run "domain edutest-edu u-edutest-edu"
STUB_VIRSH_FAIL=list run_vmtest down
expect_case "down stops and keeps the record if libvirt cannot list the objects" unreachable

recorded_pool() { [[ $RC -eq 0 ]] && ! exists volumes/testing/edutest-1-edu.qcow2 && logged "vol-delete --pool testing"; }
reset -- testing/edutest-1-edu.qcow2
own_run "volume testing edutest-1-edu.qcow2"
printf 'run=1\nsubnet=10.77.0\npool=testing\n' > "$RUN_DIR/settings"
run_vmtest down
expect_case "down uses the pool the run recorded, without VM_TEST_POOL" recorded_pool

all_removes() {
    [[ $RC -eq 0 ]] && ! exists domains/edutest-edu && ! exists volumes/default/edutest-1-base.qcow2 \
        && ! exists volumes/default/edutest-1-edu.qcow2 \
        && [[ $(grep -n "vol-delete" "$LOG" | tail -1) == *edutest-1-base.qcow2* ]]
}
reset edutest-edu -- default/edutest-1-base.qcow2 default/edutest-1-edu.qcow2
run_vmtest down --all
expect_case "down --all removes everything named edutest, the base image last" all_removes

settings_subnet() { [[ $RC -eq 0 ]] && grep -q "10.78.0.20" "$WORK/out" && ! grep -q "10.77.0" "$WORK/out"; }
reset
own_run
printf 'run=1\nsubnet=10.78.0\npool=default\n' > "$RUN_DIR/settings"
echo pw > "$RUN_DIR/lmn-root-password"
run_vmtest status
expect_case "status uses the subnet of the run, without VM_TEST_SUBNET" settings_subnet

status_early() { [[ $RC -eq 0 ]] && ! grep -q "password" "$WORK/out"; }
reset
own_run
run_vmtest status
expect_case "status after an up that stopped before the password works" status_early

covering_route() {
    [[ $RC -ne 0 ]] && grep -q "10.0.0.0/8 dev tun0" "$WORK/out" && [[ ! -e $RUN_DIR ]] && not_logged "virsh" && not_logged "curl"
}
reset
STUB_ROUTE_MATCH="10.0.0.0/8 dev tun0 scope link" run_vmtest up
expect_case "up refuses a subnet that a wider route covers" covering_route

inner_route() { [[ $RC -ne 0 ]] && grep -q "10.77.0.128/25 dev wg0" "$WORK/out" && [[ ! -e $RUN_DIR ]]; }
reset
STUB_ROUTE_ROOT="10.77.0.128/25 dev wg0 scope link" run_vmtest up
expect_case "up refuses a subnet that holds a narrower route" inner_route

bad_subnet() { [[ $RC -ne 0 ]] && grep -q "three octets" "$WORK/out"; }
reset
VM_TEST_SUBNET=10.78 run_vmtest up
expect_case "up refuses a malformed VM_TEST_SUBNET" bad_subnet

# prepare_image: a cached cloud image and the checksum list that up fetches.
prepare_image() {
    mkdir -p "$STATE_DIR/cache"
    echo image > "$STATE_DIR/cache/$IMAGE"
    (cd "$STATE_DIR/cache" && sha256sum "$IMAGE" | sed 's/  / */') > "$WORK/sums"
}

recorded_up() {
    local id
    id=$(sed -n 's/^run=//p' "$RUN_DIR/settings")
    [[ $RC -eq 0 && -n $id ]] && [[ "$(cut -d' ' -f1-3 "$RUN_DIR/resources")" == "volume default edutest-$id-base.qcow2
volume default edutest-$id-edu.qcow2
volume default edutest-$id-lmn.qcow2
volume default edutest-$id-lmn-data.qcow2
network edutest u-edutest
volume default edutest-$id-lmn-seed.iso
domain edutest-lmn u-edutest-lmn
volume default edutest-$id-edu-seed.iso
domain edutest-edu u-edutest-edu" ]]
}
reset
prepare_image
STUB_SUMS="$WORK/sums" run_vmtest up
expect_case "up records every object right after creating it" recorded_up

teardown_order() {
    [[ $RC -eq 0 ]] && [[ -z $(find "$WORK/virt" -type f) ]] \
        && [[ $(line_of "undefine edutest-edu") -lt $(line_of "vol-delete.*edu-seed") ]] \
        && [[ $(line_of "vol-delete.*lmn-seed") -lt $(line_of "net-undefine") ]] \
        && [[ $(line_of "net-undefine") -lt $(line_of "vol-delete.*-lmn.qcow2") ]] \
        && [[ $(grep -n "vol-delete" "$LOG" | tail -1) == *-base.qcow2* ]]
}
: > "$LOG"
run_vmtest down
expect_case "down after a full up removes VMs, seeds, network and disks in that order" teardown_order

network_failed() {
    [[ $RC -eq 0 ]] && [[ -z $(find "$WORK/virt" -type f) ]] && logged "net-undefine edutest"
}
reset
prepare_image
STUB_SUMS="$WORK/sums" STUB_VIRSH_FAIL=net-start run_vmtest up
up_rc=$RC
grep -q "^network edutest" "$RUN_DIR/resources" || up_rc=0
run_vmtest down
[[ $up_rc -ne 0 ]] || RC=1
expect_case "an up that stops at net-start has recorded the network, and down removes it" network_failed

failed_rebuild() {
    [[ $RC -eq 0 ]] && [[ $(cat "$RUN_DIR/image-tag") == "vmtest-$COMMIT_A" ]] \
        && logged "/root/vm-test-src/vmtest-$COMMIT_A-[0-9-]*/apps/public-page/public/installer.*--version.*vmtest-$COMMIT_A" \
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

prune_after_record() {
    local src
    src=$(cat "$RUN_DIR/image-src")
    [[ $RC -eq 0 ]] && logged "find /root/vm-test-src .* ! -name ${src##*/} " \
        && [[ $(line_of "bash -s -- .*node:") -lt $(line_of "find /root/vm-test-src") ]]
}
reset
own_run
run_vmtest build "$COMMIT_A"
expect_case "older builds on the VM are removed only after the new one is recorded" prune_after_record

if [[ $fails -ne 0 ]]; then
    echo "$fails case(s) failed"
    exit 1
fi
echo "all cases passed"
