# david_igou.linux_baseline.journald

## Description

Configure systemd journal logging settings via the `journald_option` module. Sets storage, compression, split mode, file rotation, retention, rate limiting, and memory limits.

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `journald_enabled` | `true` | Enable journald role |
| `journald_settings` | Dict of settings | Journald configuration directives |
| `journald_config_path` | `"/etc/systemd/journald.conf"` | Path to journald.conf |
| `journald_backup` | `false` | Create backup of config before changes |

Default `journald_settings`:

```yaml
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
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  roles:
    - david_igou.linux_baseline.journald
```
