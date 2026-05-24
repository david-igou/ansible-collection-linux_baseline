# Molecule scenarios across all provisioners — design

## Goal

Add seven Molecule scenarios (one per role in this collection) such that every
scenario can be run and passes verification under any of the four backends
exposed by `david_igou.molecule_provisioners`:

```
PROVISIONER=podman   molecule test -s <role>
PROVISIONER=docker   molecule test -s <role>
PROVISIONER=kubevirt molecule test -s <role>
PROVISIONER=qemu     molecule test -s <role>
```

The seven roles: `auto_updates`, `chrony`, `common`, `firewalld`, `journald`,
`sshd`, `sudoers`.

## Layout

Per-scenario, under `extensions/molecule/<role>/`, matching the upstream
README and the upstream's own `extensions/molecule/default/` and `real-images/`
scenarios verbatim. No shared directory, no symlinks. The upstream README's
"Out of scope" list explicitly disclaims a shared-scenario pattern, so the
duplicated boilerplate is the documented contract.

```
extensions/molecule/<role>/
├── molecule.yml              # boilerplate (identical across scenarios)
├── create.yml                # one-liner FQCN import
├── destroy.yml               # one-liner FQCN import
├── prepare.yml               # one-liner FQCN import
├── converge.yml              # role-specific
├── verify.yml                # role-specific
├── requirements.yml          # molecule `dependency` step input
└── inventory/
    ├── hosts.yml             # single host with mp.{podman,docker,kubevirt,qemu} blocks
    └── group_vars/
        └── molecule.yml      # mp_backend lookup + mp_defaults (identical across scenarios)
```

### Why the provisioner collection is a molecule dependency, not a galaxy.yml dependency

A downstream consumer running `ansible-galaxy collection install
david_igou.linux_baseline` should not pull in
`david_igou.molecule_provisioners`. The provisioner collection is only needed
to run the tests, not to use the roles.

Mechanism: each scenario has a `requirements.yml` listing the provisioner
collection. Molecule's built-in `dependency` step (first item in
`test_sequence`) installs it before `create`. `galaxy.yml` keeps its existing
`ansible.utils` dependency only.

## Test platform

Single host per scenario, name `instance`, Rocky Linux 9 across all backends.
Rocky 9 is the closest free stand-in for the collection's stated RHEL 9
target.

| Backend  | Image                                                                                                              |
| -------- | ------------------------------------------------------------------------------------------------------------------ |
| podman   | `docker.io/geerlingguy/docker-rockylinux9-ansible:latest`                                                          |
| docker   | `docker.io/geerlingguy/docker-rockylinux9-ansible:latest`                                                          |
| kubevirt | `quay.io/containerdisks/rockylinux:9` (container_disk boot source)                                                 |
| qemu     | `https://dl.rockylinux.org/pub/rocky/9/images/x86_64/Rocky-9-GenericCloud-Base.latest.x86_64.qcow2`                |

KubeVirt boot source is fixed to `container_disk`: the test environment's
service account cannot create `DataVolume`s (`cdi.kubevirt.io` create is
denied), so the CDI-backed boot modes are infeasible here.

## Backend defaults (shared across scenarios)

`inventory/group_vars/molecule.yml`:

```yaml
mp_backend: "{{ lookup('env', 'PROVISIONER') | default('podman', true) }}"
mp_defaults:
  podman:
    command: /sbin/init
    privileged: true
    systemd: always
    cgroupns: host
  docker:
    command_handling: compatibility
    privileged: true
  kubevirt:
    namespace: molecule
    memory: 1Gi
    ssh_user: cloud-user
  qemu:
    cpus: 2
    memory: 1024
    ssh_user: cloud-user
```

`systemd: always` + `cgroupns: host` are what let systemd run as PID 1 inside
the podman container. Without them, service-state assertions reduce to file
artifacts.

## Capability detection

A small block at the top of each `verify.yml`:

```yaml
- name: Detect host capability
  ansible.builtin.set_fact:
    mp_has_systemd: "{{ ansible_service_mgr == 'systemd' }}"
    mp_is_container: "{{ ansible_virtualization_type in ['docker', 'podman', 'container'] }}"
    mp_backend: "{{ lookup('env', 'PROVISIONER') | default('podman', true) }}"

- name: Probe systemctl reachability
  ansible.builtin.command: systemctl is-system-running
  register: mp_systemctl_probe
  failed_when: false
  changed_when: false

- name: Refine — runtime systemd available
  ansible.builtin.set_fact:
    mp_systemd_runtime: >-
      {{ mp_has_systemd and (mp_systemctl_probe.rc in [0, 1])
         and ('offline' not in (mp_systemctl_probe.stdout | default(''))) }}
```

Gates drive `when:` on runtime assertions:

| Gate                 | Used to gate                                                       |
| -------------------- | ------------------------------------------------------------------ |
| `mp_systemd_runtime` | service active/enabled checks (sshd, chronyd, journald)            |
| `not mp_is_container`| auditd active, firewalld active, dnf-automatic.timer active        |
| (always)             | file artifact + package-installed + idempotency assertions         |

## Test sequence

`test_sequence` for every scenario:

```yaml
[dependency, syntax, create, prepare, converge, idempotence, verify, destroy]
```

`idempotence` is added on top of the upstream example (which omits it). Most
of these roles do non-trivial `lineinfile` work, where regressions to
non-idempotent are easy to miss without an explicit re-run.

## Per-scenario specifications

### common

**Converge variables:**
- `common_locale: C.UTF-8`
- `common_tmout: 600`
- `common_umask: "0027"`
- `common_core_dump_enabled: false`
- `common_pam_faillock_deny: 4`
- `common_pam_faillock_unlock_time: 600`
- `common_auditd_enabled: true`

**Verify (always):**
- `/etc/locale.conf` contains `LANG=C.UTF-8`
- `/etc/profile.d/tmout.sh` contains `TMOUT=600`
- `/etc/profile.d/umask.sh` contains `UMASK=0027`
- `/etc/systemd/coredump.conf` contains `CoreDumpStorage=none`
- `/etc/security/faillock.conf` contains `deny = 4` and `unlock_time = 600`
- `audit` package installed
- `/etc/audit/rules.d/audit.rules` contains the identity watch line

**Verify (gated `not mp_is_container`):**
- `auditd.service` is `running` per `ansible.builtin.service_facts`

### sshd

**Converge variables:**
- `sshd_settings: {PermitRootLogin: 'no', PasswordAuthentication: 'no', X11Forwarding: 'no', ClientAliveInterval: '300'}`
- `sshd_enabled: true`

Pre-task ensures `openssh-server` is present (geerlingguy Rocky 9 image
already ships it; pre-task is a safety belt and a no-op there).

**Verify (always):**
- `/etc/ssh/sshd_config` contains each `<Key> <Value>` line
- `sshd -t` exits 0

**Verify (gated `mp_systemd_runtime`):**
- `sshd.service` is `running` and `enabled`

### chrony

**Converge variables:**
- `chrony_pool_servers: ['0.pool.ntp.org']`
- `chrony_drift_file: /var/lib/chrony/drift`
- `chrony_makestep: '1.0 3'`
- `chrony_leapsecmode: ignore`
- `chrony_enabled: true`

**Verify (always):**
- `chrony` package installed
- `/etc/chrony.conf` contains the pool, drift, makestep, leapsecmode lines

**Verify (gated `mp_systemd_runtime`):**
- `chronyd.service` is `enabled`

**Verify (gated `not mp_is_container`):**
- `chronyd.service` is `running`

### firewalld

**Converge variables:**
- `firewalld_enabled: true`
- `firewalld_default_zone: public`
- `firewalld_services: ['ssh']`
- `firewalld_zones: {internal: {service: 'ssh'}}`

**Verify (always):**
- `firewalld` package installed
- `/etc/firewalld/zones/public.xml` exists
- `firewall-offline-cmd --get-default-zone` returns `public`

**Verify (gated `not mp_is_container`):**
- `firewalld.service` is `running`
- `firewall-cmd --get-default-zone` returns `public`
- `firewall-cmd --list-services` includes `ssh`

**Role-side change required (in scope of this branch):**

The current role calls `firewall-cmd --set-default-zone`,
`firewall-cmd --zone=...`, etc. unconditionally during converge — even on
hosts where `firewalld` is not yet running. The first run of the role on a
host without `firewalld.service` started will fail at these tasks, regardless
of backend (containers reproduce this most reliably).

The fix in this branch reorders the role so that:
1. `firewalld` package is installed
2. `firewalld.service` is started (when `firewalld_enabled`)
3. Runtime `firewall-cmd` tasks run only after the service is up

This matches the way `ansible.posix.firewalld` operates and is the only way
the role can be idempotent on a fresh host regardless of backend. Rationale
logged here, not as a comment in the task file (per the project's
"comments only for non-obvious why" guidance).

The role still cannot pass _runtime_ verification on container backends —
`firewalld` requires kernel netfilter access that an unprivileged container
namespace doesn't have. On podman/docker we assert package + zone XML only;
on kubevirt/qemu we assert the live daemon's state.

### journald

**Converge variables:**
- `journald_settings: {Storage: persistent, Compress: 'yes', SystemMaxUse: '500M', SystemKeepFree: '100M'}`
- `journald_enabled: true`

**Verify (always):**
- `/etc/systemd/journald.conf` contains each configured key

**Verify (gated `mp_systemd_runtime`):**
- `systemd-journald.service` is `running`

Idempotency for this role is exercised by molecule's built-in `idempotence`
step — re-running converge must report `changed=0`, which is exactly the
contract the `journald_option` custom module is meant to satisfy.

### auto_updates

**Converge variables:**
- `auto_updates_enabled: true`
- `auto_updates_upgrade_type: security`
- `auto_updates_download_updates: true`
- `auto_updates_apply_when: always`
- `auto_updates_randomize_timer: true`
- `auto_updates_email_report: false`

**Verify (always):**
- `dnf-automatic` package installed
- `/etc/dnf/automatic.conf` contains `upgrade_type = security`,
  `download_updates = yes`, `apply_updates = yes`,
  `randomized_delay_sec = 3600`

**Verify (gated `not mp_is_container`):**
- `dnf-automatic.timer` is enabled

### sudoers

**Converge variables:**
- `sudoers_enabled: true`
- `sudoers_defaults: {timestamp_timeout: 5, passwd_tries: 3, logfile: '/var/log/sudo.log'}`
- `sudoers_dropins: [{name: '10-wheel-nopasswd', content: '%wheel ALL=(ALL) NOPASSWD: ALL'}]`

**Verify (always):**
- `sudo` package installed
- `visudo -cf /etc/sudoers` exits 0
- `/etc/sudoers` contains each `Defaults <key>=<val>` line
- `/etc/sudoers.d/10-wheel-nopasswd` exists, mode `0440`, owner `root`,
  content matches
- `visudo -cf /etc/sudoers.d/10-wheel-nopasswd` exits 0

No service-state checks — sudoers has none.

## Branch and commit plan

Branch: `feature/molecule-scenarios`.

Commits, ordered:

1. `docs(spec): molecule scenarios across all provisioners`
2. `chore(molecule): scaffold extensions/molecule/<role>/ skeletons` (all 7)
3. `feat(molecule): converge + verify for <role>` × 7
4. `fix(role): firewalld gate runtime firewall-cmd on active daemon`
5. `docs(molecule): document PROVISIONER usage + scenario list`

## Assumptions

Each assumption is followed by a short rationale.

1. **Test platform is Rocky Linux 9, single host per scenario, host name
   `instance`.** Closest free stand-in for the collection's RHEL 9 target;
   avoids matrix blowup; matches upstream example shape.

2. **Containers must run systemd as PID 1.** `systemd: always` + `cgroupns:
   host` for podman; `command_handling: compatibility` for docker. Service
   state assertions are otherwise meaningless inside the container.

3. **Privileged containers.** Per upstream `mp_defaults` example. Required
   for systemd cgroup access. Acceptable for ephemeral test instances.

4. **KubeVirt boot source is `container_disk`.** The cluster's
   `ansible-molecule` SA cannot create DataVolumes; `container_disk` is the
   only feasible mode in this environment.

5. **No firewalld runtime assertions on container backends.** firewalld in a
   privileged container can't reliably interact with the host kernel's
   netfilter namespace; the role still writes the zone XML, which we verify
   on disk.

6. **No auditd runtime assertions on container backends.** auditd needs
   `CAP_AUDIT_CONTROL` against the host's audit namespace, which an
   unprivileged container namespace doesn't expose. File artifacts only on
   containers.

7. **No dnf-automatic.timer runtime assertion on container backends.**
   The timer unit gets installed; whether it starts is gated on systemd
   reachability + non-container.

8. **Per-scenario `mp_defaults` and `mp_backend` block is identical across
   the seven scenarios.** Diverging it would create scenario-specific
   provisioner behavior, defeating the "same scenarios, switch backends with
   one env var" property.

9. **Converge overrides at least one non-default value per role**, so verify
   asserts a real effect rather than tautologically asserting the default.

10. **Molecule's built-in `idempotence` step is in `test_sequence`** even
    though the upstream example omits it. Idempotency is a first-class
    expectation for this collection's roles.

11. **No CI workflow changes** — the user noted GitHub Actions are disabled
    for this repo.

12. **`oc auth can-i` is authoritative on OpenShift; `kubectl auth can-i`
    can mis-report.** Discovered while probing the test cluster. Logged for
    the upstream feedback issue (kubevirt README mentions only `kubectl`).

13. **The firewalld role itself is amended in this branch** to be runnable
    on a host without firewalld already running. Role behavior must converge
    cleanly before any verify can run; the existing ordering does not. This
    is the only role-side change in scope; the rest verify-as-is.

## Out of scope (deliberately)

- Multi-host scenarios.
- Multi-distribution matrix (Fedora 41, CentOS Stream 10).
- Changes to GitHub Actions / CI.
- Re-architecting the provisioner collection's shared-scenario gap.
- Adding new modules or refactoring existing role logic beyond the firewalld
  ordering fix.

## Upstream feedback (file at task end as an issue on
`david-igou/ansible-collection-molecule_provisioners`)

Positives:
- README boilerplate is copy-paste-and-go.
- One env var (`PROVISIONER`) swaps backends with no per-scenario edits — the
  abstraction held cleanly across seven roles.
- Migration guide's field-by-field table made the mental model quick to grasp.
- Per-backend prereq table is concise and accurate.

Friction (each tied to where it surfaced):
1. `docs/MIGRATION.md` "What this collection does NOT support" still lists
   docker as unsupported, but README v1.1 lists docker as a backend.
2. KubeVirt role hard-requires cluster-scoped `nodes [get,list]` with no
   opt-out (`roles/kubevirt/tasks/create.yml`). Suggest: per-host
   `kubevirt.connection_ip` override that skips the Node listing.
3. `mp_kubevirt_allowed_ssh_service_types` is hardcoded to `[NodePort]`.
   A `None`/`Skip` mode would unblock setups that ssh via pod-IP, Route, or
   Ingress.
4. README prereq table for kubevirt should call out the specific verbs the
   role needs in the target cluster (nodes get/list at cluster scope;
   services create/get/delete; VMs create/get/delete; secrets not required
   in container_disk mode).
5. No shared-scenario pattern. 7-scenario consumers like this collection
   carry 7× duplicated boilerplate. Document a recommended pattern (e.g.,
   symlinks to a `_shared/` peer) even if not implemented in-tree.
6. `kubectl auth can-i` mis-reports Service create perms on OpenShift for
   identities the cluster does in fact authorize. Worth a footnote in the
   kubevirt prereq table mentioning that `oc auth can-i` is authoritative
   when running against OpenShift.
