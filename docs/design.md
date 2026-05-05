---
title: david_igou.linux_baseline — Design Specification
date: 2026-05-05
status: approved
---

# david_igou.linux_baseline Collection — Design Specification

## 1. Overview

This collection provides Ansible modules and roles for applying a security-focused baseline configuration across three Linux distributions: **Fedora 41**, **RHEL 9 UBI**, and **CentOS Stream 10**.

It includes three config-management modules (`sshd_option`, `journald_option`, `sysctl_profile`) and seven roles (`common`, `chrony`, `sshd`, `sudoers`, `firewalld`, `journald`, `auto_updates`). All roles are fully standalone with no inter-role dependencies.

## 2. Modules

All three modules share a common pattern: accept a `settings` dict, loop over entries using `ansible.builtin.lineinfile`, and report per-key change status in the return value.

### 2.1 `sshd_option`

Sets or removes individual sshd_config directives.

#### argument_spec

```python
argument_spec = dict(
    settings=dict(type="dict", required=True),
    path=dict(type="str", default="/etc/ssh/sshd_config"),
    backup=dict(type="bool", default=False),
    state=dict(type="str", default="present", choices=["present", "absent"]),
)
```

| Parameter | Type   | Required | Default              | Description                          |
|-----------|--------|----------|----------------------|--------------------------------------|
| `settings`| dict   | yes      | —                    | Dict of sshd directive key-value pairs. Keys match sshd_config option names (e.g., `PermitRootLogin`). |
| `path`    | str    | no       | `/etc/ssh/sshd_config` | Path to the sshd configuration file. |
| `backup`  | bool   | no       | `false`              | Whether to create a `.bak` backup of the file before modification. |
| `state`   | str    | no       | `present`            | `present` sets directives; `absent` removes them from the file. |

#### return contract

```python
return_data = dict(
    changed=dict(type="bool", description="Whether any settings were modified."),
    changed_keys=dict(type="list", elements="str", description="Keys that were actually changed on this run.", returned="always"),
    unchanged_keys=dict(type="list", elements="str", description="Keys already matching desired state.", returned="always"),
    removed_keys=dict(type="list", elements="str", description="Keys removed when state=absent.", returned="always"),
    file=dict(type="str", description="Path to the modified configuration file.", returned="changed"),
)
```

#### check_mode / diff support

- **check_mode**: Supported. `lineinfile` operates in check mode; no file is written. Module reports `changed_keys` accurately.
- **diff**: Supported. Each `lineinfile` call includes `diff=True`, producing a unified diff for every changed key.

#### idempotency invariant

Running the module twice with identical `settings` produces `changed: false` and `changed_keys: []`. The file content after first run matches the desired state exactly.

#### validation command before reload

```bash
sshd -t
```

If validation fails, the module returns `failed: true` without triggering a reload handler. On success, triggers `systemctl reload sshd`.

---

### 2.2 `journald_option`

Sets or removes individual journald.conf directives under `[Journal]`, `[Runtime], and `[Persistent]` sections.

#### argument_spec

```python
argument_spec = dict(
    settings=dict(type="dict", required=True),
    path=dict(type="str", default="/etc/systemd/journald.conf"),
    backup=dict(type="bool", default=False),
    state=dict(type="str", default="present", choices=["present", "absent"]),
)
```

| Parameter | Type   | Required | Default                            | Description                                        |
|-----------|--------|----------|------------------------------------|----------------------------------------------------|
| `settings`| dict   | yes      | —                                  | Dict of journald directive key-value pairs. Keys match journald.conf option names (e.g., `Storage`, `MaxFileSec`). |
| `path`    | str    | no       | `/etc/systemd/journald.conf`       | Path to the journald configuration file.           |
| `backup`  | bool   | no       | `false`                            | Whether to create a `.bak` backup before modification. |
| `state`   | str    | no       | `present`                          | `present` sets directives; `absent` removes them.  |

#### return contract

```python
return_data = dict(
    changed=dict(type="bool", description="Whether any settings were modified."),
    changed_keys=dict(type="list", elements="str", description="Keys that were actually changed on this run.", returned="always"),
    unchanged_keys=dict(type="list", elements="str", description="Keys already matching desired state.", returned="always"),
    removed_keys=dict(type="list", elements="str", description="Keys removed when state=absent.", returned="always"),
    file=dict(type="str", description="Path to the modified configuration file.", returned="changed"),
)
```

#### check_mode / diff support

- **check_mode**: Supported. `lineinfile` operates in check mode; no file is written. Module reports `changed_keys` accurately.
- **diff**: Supported. Each `lineinfile` call includes `diff=True`, producing a unified diff for every changed key.

#### idempotency invariant

Running the module twice with identical `settings` produces `changed: false` and `changed_keys: []`. The file content after first run matches the desired state exactly.

#### validation command before reload

```bash
journalctl --verify 2>/dev/null || true
```

journald does not have a dedicated config test flag. The module verifies the file is valid systemd.conf-format by checking that all modified keys are recognized options (validated against the man page). On success, triggers `systemctl daemon-reload && systemctl restart systemd-journald`.

---

### 2.3 `sysctl_profile`

Creates or manages drop-in files in `/etc/sysctl.d/` for kernel parameter tuning.

#### argument_spec

```python
argument_spec = dict(
    settings=dict(type="dict", required=True),
    prefix=dict(type="str", default="99-custom"),
    order=dict(type="int", default=1, description="Load order number appended to filename."),
    backup=dict(type="bool", default=False),
    state=dict(type="str", default="present", choices=["present", "absent"]),
)
```

| Parameter | Type   | Required | Default        | Description                                            |
|-----------|--------|----------|----------------|--------------------------------------------------------|
| `settings`| dict   | yes      | —              | Dict of sysctl key-value pairs. Keys are dot-notation (e.g., `net.ipv4.ip_forward`). |
| `prefix`  | str    | no       | `99-custom`    | Filename prefix for the drop-in file under `/etc/sysctl.d/`. |
| `order`   | int    | no       | `1`            | Numeric suffix appended to filename (e.g., `99-custom_1_custom.conf`). Load order determines precedence. |
| `backup`  | bool   | no       | `false`        | Whether to create a `.bak` backup before modification. |
| `state`   | str    | no       | `present`      | `present` sets directives; `absent` removes them from the file. |

#### return contract

```python
return_data = dict(
    changed=dict(type="bool", description="Whether any settings were modified."),
    changed_keys=dict(type="list", elements="str", description="Keys that were actually changed on this run.", returned="always"),
    unchanged_keys=dict(type="list", elements="str", description="Keys already matching desired state.", returned="always"),
    removed_keys=dict(type="list", elements="str", description="Keys removed when state=absent.", returned="always"),
    file=dict(type="str", description="Path to the created/modified sysctl drop-in file.", returned="changed"),
)
```

#### check_mode / diff support

- **check_mode**: Supported. `lineinfile` operates in check mode; no file is written. Module reports `changed_keys` accurately.
- **diff**: Supported. Each `lineinfile` call includes `diff=True`, producing a unified diff for every changed key.

#### idempotency invariant

Running the module twice with identical `settings` produces `changed: false` and `changed_keys: []`. The drop-in file content after first run matches the desired state exactly.

#### validation command before reload

```bash
sysctl --system --strict 2>&1 | grep -i "error\|invalid" || true
```

The module also validates each key against `/usr/lib/sysctl.d/` defaults and known sysctl names (from `sysctl -a` output). On success, triggers `sysctl -p /etc/sysctl.d/<filename>.conf`.

---

## 3. Roles

All roles are fully standalone — no meta dependencies between them. Users orchestrate ordering in their playbooks. Variable names follow the `<role>_` prefix convention.

### 3.1 `common`

Applies baseline system hardening: locale, PAM password policy, session timeout, core dumps, umask.

#### Variables with defaults

```yaml
---
# roles/common/defaults/main.yml
common_locale: "en_US.UTF-8"
common_tmout: 900                    # idle timeout in seconds
common_umask: "0077"
common_core_dump_enabled: false
common_pam_faillock_deny: 5          # PAM faillock deny threshold
common_pam_faillock_unlock_time: 900 # PAM faillock unlock time (seconds)
common_auditd_enabled: true
```

#### Handler list

```yaml
# roles/common/handlers/main.yml
- name: restart auditd
  ansible.builtin.service:
    name: auditd
    state: restarted
  listen: "restart services"
```

#### Distro guards

| Task / Variable | Guard condition | Notes |
|-----------------|-----------------|-------|
| `auditd` config | `ansible_facts['distribution'] in ['RedHat', 'CentOS', 'Fedora']` | auditd available on all three distros, but package name differs (`audit` vs `auditd`) |
| PAM faillock     | `ansible_facts['os_family'] == 'RedHat'` | Uses `pam_faillock.so` which is RHEL-family specific |
| locale config    | `true` (all distros) | Uses `ansible_facts['locale']` for detection |

---

### 3.2 `chrony`

Configures NTP time synchronization via chrony.

#### Variables with defaults

```yaml
---
# roles/chrony/defaults/main.yml
chrony_enabled: true
chrony_pool_servers:
  - "0.pool.ntp.org"
  - "1.pool.ntp.org"
  - "2.pool.ntp.org"
  - "3.pool.ntp.org"
chrony_drift_file: "/var/lib/chrony/drift"
chrony_makestep: "1.0 3"        # allow up to 3 steps of 1s on first sync
chrony_leapsecmode: "software"
chrony_log_interval: -1          # auto-adapt logging interval
chrony_access_network: "10.0.0.0/8"
chrony_access_mask: "/16"
chrony_access_ro: true
```

#### Handler list

```yaml
# roles/chrony/handlers/main.yml
- name: restart chronyd
  ansible.builtin.service:
    name: chronyd
    state: restarted
  listen: "restart services"
```

#### Distro guards

| Task / Variable | Guard condition | Notes |
|-----------------|-----------------|-------|
| Install chrony package | `ansible_facts['distribution'] == 'RedHat'` → `chrony`; `ansible_facts['distribution'] == 'Fedora'` → `chrony`; `ansible_facts['distribution'] == 'CentOS'` → `chrony` | Same package name on all three distros |
| Service name | All three: `chronyd` | Consistent across target distros |
| `/etc/chrony.conf` vs `/etc/chrony/chrony.conf` | `ansible_facts['distribution'] == 'Fedora'` → `/etc/chrony/chrony.conf`; others → `/etc/chrony.conf` | Fedora 41 uses the split directory layout |

---

### 3.3 `sshd`

Hardens the SSH daemon using the `david_igou.linux_baseline.sshd_option` module.

#### Variables with defaults

```yaml
---
# roles/sshd/defaults/main.yml
sshd_enabled: true
sshd_settings:
  PermitRootLogin: "no"
  PasswordAuthentication: "no"
  PubkeyAuthentication: "yes"
  ChallengeResponseAuthentication: "no"
  UsePAM: "yes"
  X11Forwarding: "no"
  MaxAuthTries: 3
  MaxSessions: 5
  ClientAliveInterval: 300
  ClientAliveCountMax: 2
  LoginGraceTime: 60
  PermitEmptyPasswords: "no"
  AllowTcpForwarding: "no"
  StrictModes: "yes"
  IgnoreRhosts: "yes"
sshd_config_path: "/etc/ssh/sshd_config"
sshd_backup: false
```

#### Handler list

```yaml
# roles/sshd/handlers/main.yml
- name: reload sshd
  ansible.builtin.service:
    name: sshd
    state: reloaded
  listen: "reload sshd"
```

#### Distro guards

| Task / Variable | Guard condition | Notes |
|-----------------|-----------------|-------|
| Enable sshd service | `sshd_enabled == true` | Service name `sshd` is consistent across all three distros |
| Config path override | `true` (user variable) | Default `/etc/ssh/sshd_config` is consistent; guard exists only if distro-specific override needed |

---

### 3.4 `sudoers`

Manages sudo configuration and drop-in files under `/etc/sudoers.d/`.

#### Variables with defaults

```yaml
---
# roles/sudoers/defaults/main.yml
sudoers_enabled: true
sudoers_defaults:
  - "authenticate"
  - "timestamp_type=cred"
  - "fail_badpass"
  - "passwd_tries 3"
  - "passwd_timeout 5"
sudoers_dropins: []
# Example dropin:
#   - name: "wheel-restrict"
#     content: |
#       %wheel ALL=(ALL) NOPASSWD: ALL
```

#### Handler list

```yaml
# roles/sudoers/handlers/main.yml
- name: validate sudoers
  ansible.builtin.command:
    cmd: visudo -c
  listen: "validate sudoers"
```

#### Distro guards

| Task / Variable | Guard condition | Notes |
|-----------------|-----------------|-------|
| Install sudo package | `true` (all distros) | Package name `sudo` is consistent across all three distros |
| `/etc/sudoers.d/` directory | `true` (all distros) | Standard location on all three distros |

---

### 3.5 `firewalld`

Configures firewall zones, services, and rich rules via firewalld.

#### Variables with defaults

```yaml
---
# roles/firewalld/defaults/main.yml
firewalld_enabled: true
firewalld_default_zone: "public"
firewalld_zones: {}
# Example zone:
#   dmz:
#     ports:
#       - "22/tcp"
#     services: ["ssh"]
#     rich_rules:
#       - 'rule family="ipv4" source address="10.0.0.0/8" accept'
firewalld_services: []
firewalld_masquerade: false
firewalld_forward_ports: []
```

#### Handler list

```yaml
# roles/firewalld/handlers/main.yml
- name: reload firewalld
  ansible.builtin.service:
    name: firewalld
    state: reloaded
  listen: "reload firewalld"
```

#### Distro guards

| Task / Variable | Guard condition | Notes |
|-----------------|-----------------|-------|
| Install firewalld | `true` (all distros) | Package name `firewalld` is consistent across all three distros |
| Service name | All three: `firewalld` | Consistent across target distros |

---

### 3.6 `journald`

Configures systemd journal behavior using the `david_igou.linux_baseline.journald_option` module.

#### Variables with defaults

```yaml
---
# roles/journald/defaults/main.yml
journald_enabled: true
journald_settings:
  Storage: "persistent"
  Compress: "yes"
  Split: "auto"
  MaxFileSec: "1day"
  MaxRetentionSec: "1year"
  ForwardToSyslog: "no"
  SystemMaxUse: "256M"
  SystemKeepFree: "1G"
  RuntimeMaxUse: "64M"
  RuntimeKeepFree: "512M"
  RateLimitInterval: "30s"
  RateLimitBurst: "10000"
journald_config_path: "/etc/systemd/journald.conf"
journald_backup: false
```

#### Handler list

```yaml
# roles/journald/handlers/main.yml
- name: restart journald
  ansible.builtin.command:
    cmd: systemctl daemon-reload && systemctl restart systemd-journald
  listen: "restart journald"
```

#### Distro guards

| Task / Variable | Guard condition | Notes |
|-----------------|-----------------|-------|
| Enable journald service | `true` (all distros) | `systemd-journald` is the init system on all three target distros |
| Config path override | `true` (user variable) | Default `/etc/systemd/journald.conf` is consistent; guard exists only if distro-specific override needed |

---

### 3.7 `auto_updates`

Configures unattended security updates via `dnf-automatic`.

#### Variables with defaults

```yaml
---
# roles/auto_updates/defaults/main.yml
auto_updates_enabled: true
auto_updates_apply_when: "always"      # always, reboot, never
auto_updates_randomize_timer: true     # jitter the timer to avoid thundering herd
auto_updates_email_report: false
auto_updates_email_to: ""              # required if email_report is true
auto_updates_download_updates: true
auto_updates_upgrade_type: "security"  # security (default) or all
```

#### Handler list

```yaml
# roles/auto_updates/handlers/main.yml
- name: restart dnf-automatic timer
  ansible.builtin.service:
    name: dnf-automatic.timer
    state: restarted
  listen: "restart dnf-automatic"
```

#### Distro guards

| Task / Variable | Guard condition | Notes |
|-----------------|-----------------|-------|
| Install dnf-automatic | All three distros use `dnf-automatic` package | Package name is consistent across RHEL 9 UBI, Fedora 41, CentOS Stream 10 |
| Config file path | `/etc/dnf/automatic.conf` on all three | Consistent location |
| Timer name | `dnf-automatic.timer` on all three | Consistent timer unit name |

---

## 4. Distro Detection Strategy

All distro-specific logic uses the following detection pattern:

```yaml
# RHEL 9 UBI
ansible_distribution == "RedHat" and ansible_distribution_major_version == "9"

# Fedora 41
ansible_distribution == "Fedora" and ansible_distribution_major_version == "41"

# CentOS Stream 10
ansible_distribution == "CentOS" and ansible_distribution_major_version == "Stream"
```

For cross-distro operations where behavior is identical, guards use the combined form:

```yaml
when: ansible_facts['distribution'] in ['RedHat', 'Fedora', 'CentOS']
```

---

## 5. Module Implementation Notes

### 5.1 Common module structure

All three modules follow this pattern:

1. Define `argument_spec` with shared parameters (`settings`, `path`, `backup`, `state`)
2. Read existing file content (if it exists)
3. Loop over `settings.items()`:
   - Call `ansible.builtin.lineinfile` for each key-value pair
   - Track which keys changed vs were already correct
4. Build return data with `changed_keys`, `unchanged_keys`, and `removed_keys` lists
5. On success, set `meta: notify` to trigger the appropriate handler

### 5.2 Error handling

- If a key in `settings` does not correspond to a recognized directive for the target config format, the module returns `failed: true` with a descriptive message listing unrecognized keys.
- If the validation command (e.g., `sshd -t`) fails, the module returns `failed: true` without notifying handlers.
- File permission errors are caught and returned as `module.fail_json()`.

### 5.3 Absent state behavior

When `state: absent`, each module removes the matching line from the config file using `lineinfile(state=absent)`. Removed keys appear in the `removed_keys` return field. A reload handler is triggered only if at least one key was removed.

---

## 6. Testing Strategy

- **Unit tests**: Per-module unit tests under `tests/unit/` verifying argument parsing, check_mode behavior, and return value structure.
- **Integration tests**: Per-role integration targets under `tests/integration/targets/<role>/` exercising idempotency (run twice, verify second run reports no changes).
- **Linting**: `ansible-lint --profile=production` on all roles; module code linted via `pylint`.
