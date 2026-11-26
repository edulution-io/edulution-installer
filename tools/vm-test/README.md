# vm-test: try the installer on throwaway VMs

`vm-test` sets up two local KVM machines for a manual end-to-end test of the installer, including the linuxmuster part that the E2E workflow cannot cover:

| VM | Address | Role |
|---|---|---|
| `edutest-edu` | 10.77.0.20 | edulution server: runs `installer` and the web installer |
| `edutest-lmn` | 10.77.0.10 | linuxmuster server: the web installer installs linuxmuster.net 7.4 here |

Both run the Ubuntu 26.04 cloud image in their own libvirt NAT network `edutest` (10.77.0.0/24, no DHCP). The host reaches them directly, so the browser on the host opens the web installer.

Use it for every pull request that touches the installer flow: the `installer` script, the web installer, the LMN installer or the playbooks. It tests a branch **before** a release: `vm-test build` builds the installer image from the checkout on the edu VM, as the E2E workflow does on its runner.

## Requirements

- Linux with KVM, libvirt and access to `qemu:///system` (user in the `libvirt` group)
- `xorriso`, `genisoimage` or `cloud-localds` for the cloud-init seed
- About 11 GB free RAM (edu 6 GiB, lmn 4.5 GiB; set `VM_TEST_EDU_MEMORY` / `VM_TEST_LMN_MEMORY` in MiB)
- About 40 GB free in the libvirt pool `default`, or the directory pool that `VM_TEST_POOL` names. The disks are thin, so a full run uses about that much. Their nominal size is 80 GB.

Nothing is installed on the host. The tool creates only libvirt objects whose names start with `edutest`, plus its own directory `~/.local/state/edulution-vm-test`. Two things stay after `down`, as libvirt handles them: IPv4 forwarding, which libvirt turns on for a NAT network and leaves on (the protocol records it with the command that turns it off again, and the comparison after `down` shows it), and the VM logs in `/var/log/libvirt/qemu/edutest-*.log`.

## Quick start

Test a released version:

```bash
tools/vm-test/vm-test up                  # network, both VMs; about 2 minutes
tools/vm-test/vm-test install --version 2.2.3
# open the printed URL, run the web installer (values below)
tools/vm-test/vm-test down
```

Test the current branch:

```bash
tools/vm-test/vm-test up
tools/vm-test/vm-test build               # working tree incl. uncommitted changes to tracked files
tools/vm-test/vm-test install --local
# ...
tools/vm-test/vm-test down
```

`build <git-ref>` builds a branch, tag or commit instead of the working tree. Each build gets its own source directory on the VM; if a build fails, `install --local` keeps using the last good one. A successful build removes the sources of earlier ones, so do not build while an `install --local` runs. Untracked files are not part of a build; `git add` them first. A build installs Docker on the edu VM, so the installer takes its "Docker is already installed" path there.

Other commands:

```bash
tools/vm-test/vm-test status              # addresses, state, linuxmuster login, installer URL
tools/vm-test/vm-test ssh lmn             # shell as edutest (sudo without password)
# a command runs in the VM's shell: quote it as one argument if it holds quotes or escapes
tools/vm-test/vm-test ssh edu sudo tail -f /root/installer.log
```

## Web installer values

| Field | Value |
|---|---|
| linuxmuster server | `10.77.0.10` |
| SSH user | `root` |
| SSH password | printed by `install` and `status` |
| Admin password | any password that meets the linuxmuster rules, e.g. upper and lower case, a digit and a special character |

After `linuxmuster-setup`, the root password on the lmn VM is the admin password from the web installer. `vm-test ssh lmn` uses its key and keeps working. When the web installer asks to restart the linuxmuster server, run `vm-test ssh lmn 'sudo systemctl reboot'`, wait until `vm-test ssh lmn true` answers again, then continue with "Next". The edulution address is the edu VM's, `10.77.0.20` unless `VM_TEST_SUBNET` says otherwise (`vm-test status` shows it). The VMs have no QEMU guest agent channel, so the playbook's task that starts the agent waits 90 seconds and is then ignored.

## What to test

The basic run: install, linuxmuster setup, edulution stack up, login works. Depending on the change, also:

- **Lost connection:** close the browser tab while `linuxmuster-setup` runs and open `https://<edu address>/lmn-install` again (the URL with the token leads to the start page). The page continues the same run, shows the full log once without duplicate lines, and does not start a second run. Check with `vm-test ssh lmn "sudo grep -c 'POST /api/playbook/linuxmuster.yml/start' /opt/edulution-installer/api.log"` (expected: 1).
- **Reload after the run:** reload the page after the run finished and before "Next". The configuration is fetched again. The LMN installer API stops only on "Next".
- **Second run on the same server:** run the installer again against the installed lmn VM. `install` starts only one run per environment; for a second one, remove its log first: `vm-test ssh edu 'sudo rm /root/installer.log /root/installer.rc'`, then `vm-test install` again. Existing configuration such as `/etc/edulution-fileproxy/config.yml` stays as it was.
- **fileproxy:** `vm-test ssh lmn "curl -sk -o /dev/null -w '%{http_code}\n' https://127.0.0.1/webdav/"` answers `401`.
- **Update:** after an install with an older version, `vm-test ssh edu 'curl -fsSL https://get.edulution.io/update | sudo bash -s -- --check'`.

For a browser test with Playwright, ignore certificate errors: the web installer uses a self-signed certificate. With the Chrome DevTools Protocol that is `Security.setIgnoreCertificateErrors`.

## Logs

| Where | What |
|---|---|
| edu: `/root/installer.log` | output of the `installer` script, including the URL with token |
| edu: `sudo docker logs edulution-installer` | web installer API, including the proxy to the LMN installer |
| lmn: `/opt/edulution-installer/api.log` | LMN installer API: playbook starts, WebSocket connections |
| lmn: `/opt/edulution-installer/ansible/artifacts/*/stdout` | playbook output; `grep '^TASK'` shows the progress |

## Cleanup and protocol

`vm-test up` writes a protocol. It lists the host state before the run and every change to the host, each with the command that undoes it. `vm-test down`:

1. stops and removes the VMs, volumes and network that this run's `up` created, and nothing else
2. compares the host with the state recorded before `up` and writes the result into the protocol
3. deletes the SSH key, the passwords and the cloud-init files, and with them the downloaded cloud image (`--keep-image` keeps the image for the next run)
4. keeps the protocol as `~/.local/state/edulution-vm-test/protocol-<date>.md`

`up` records each object as soon as it exists, so `down` also cleans up after an `up` that stopped half way. Volume names carry an id of the run, and VMs and the network are recorded with their UUIDs, so `down` leaves an object alone that another run has created under the same name since. If something cannot be removed, `down` keeps its record and can be run again. Objects named `edutest` that the run did not create, for example from another user's run or a run whose state directory is gone, stay; `down` names them, and `down --all` removes everything named `edutest`. A difference in the comparison can come from the host itself, for example a VPN that changed its routes.

## Pitfalls

- **Idle web installer:** the web installer ends itself after 2 hours without use, and the `installer` script with it. An image from before 2.2.4 (`--version`) has no such limit; a script from before 2.2.4 gives up 60 minutes after the web installer started.
- **One environment per host:** the names and the network are fixed. Run `down` before the next `up`; `up` refuses if anything named `edutest` exists.
- **Gateway without DNS:** `VM_TEST_DNS=9.9.9.9 vm-test up` turns DNS off on the gateway (10.77.0.1) and gives the VMs that server instead, as on a network whose firewall answers no DNS (#178): the linuxmuster installation then stops with a message before it changes the server. The server has to be reachable from the host.
- **Network in use:** `up` refuses if a route on the host covers 10.77.0.0/24 or lies inside it (VPN, other libvirt network); choose another with `VM_TEST_SUBNET=10.78.0`. The run keeps its subnet and `VM_TEST_POOL`, so the later commands need neither.
- **No virt-install:** `up` defines the VMs with `virsh` and its own seed ISO. `virt-install --cloud-init` needs `meta-data`, or cloud-init does not run. It also creates the persistent pool `boot-scratch` and files under `~/.cache/virt-manager`.
- **Host keys:** `vm-test ssh` does not check or store host keys. The VMs exist only in the local NAT network, and `linuxmuster-setup` replaces the keys of the lmn VM.
