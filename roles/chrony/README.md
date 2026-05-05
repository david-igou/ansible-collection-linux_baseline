# david_igou.linux_baseline.chrony

## Description

Configure chrony NTP service for time synchronization hardening. Sets pool servers, drift file, makestep, leapsec mode, and access controls.

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `chrony_enabled` | `true` | Enable chrony role |
| `chrony_pool_servers` | NTP pool list | List of NTP pool servers |
| `chrony_drift_file` | `"/var/lib/chrony/drift"` | Path to drift file |
| `chrony_makestep` | `"1.0 3"` | Makestep configuration |
| `chrony_leapsecmode` | `"software"` | Leap second handling mode |
| `chrony_log_interval` | `-1` | Logging interval |
| `chrony_access_network` | `"10.0.0.0/8"` | Network allowed for chrony access |
| `chrony_access_mask` | `"/16"` | Netmask for access control |
| `chrony_access_ro` | `true` | Allow read-only access to local clients |

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  roles:
    - david_igou.linux_baseline.chrony
```
