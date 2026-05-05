# david_igou.linux_baseline.auto_updates

## Description

Configure automatic security updates using dnf-automatic. Installs and configures the dnf-automatic package with download, install, and email reporting options. Works on RHEL/CentOS, Fedora, and Amazon Linux.

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `auto_updates_enabled` | `true` | Enable auto-updates role |
| `auto_updates_apply_when` | `"always"` | When to apply updates (always/immediate) |
| `auto_updates_randomize_timer` | `true` | Randomize dnf-automatic timer execution |
| `auto_updates_email_report` | `false` | Enable email reports |
| `auto_updates_email_to` | `""` | Email address for reports |
| `auto_updates_download_updates` | `true` | Automatically download updates |
| `auto_updates_upgrade_type` | `"security"` | Upgrade type (security/all) |

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  roles:
    - david_igou.linux_baseline.auto_updates
```
