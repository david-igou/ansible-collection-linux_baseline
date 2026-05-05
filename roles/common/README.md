# david_igou.linux_baseline.common

## Description

Common security hardening baseline settings for Linux systems. Configures locale, timeout, umask, core dumps, PAM faillock, and auditd.

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `common_locale` | `"en_US.UTF-8"` | System locale setting |
| `common_tmout` | `900` | Shell timeout in seconds (TMOUT) |
| `common_umask` | `"0077"` | Default umask value |
| `common_core_dump_enabled` | `false` | Enable core dump collection |
| `common_pam_faillock_deny` | `5` | PAM faillock deny threshold |
| `common_pam_faillock_unlock_time` | `900` | PAM faillock unlock time in seconds |
| `common_auditd_enabled` | `true` | Enable auditd service |

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  roles:
    - david_igou.linux_baseline.common
```
