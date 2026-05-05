# david_igou.linux_baseline.sshd

## Description

Configure SSH daemon security hardening settings and access controls. Sets sshd_config directives via the `sshd_option` module and enables the service.

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `sshd_enabled` | `true` | Enable sshd role |
| `sshd_settings` | Dict of hardened values | SSH daemon configuration directives |
| `sshd_config_path` | `"/etc/ssh/sshd_config"` | Path to sshd_config |
| `sshd_backup` | `false` | Create backup of config before changes |

Default `sshd_settings`:

```yaml
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
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  roles:
    - david_igou.linux_baseline.sshd
```
