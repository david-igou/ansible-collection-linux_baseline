# david_igou.linux_baseline.firewalld

## Description

Configure firewall rules and zones using firewalld for network security. Sets default zone, configures zones with ports/services/rich rules, masquerade, and forward ports.

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `firewalld_enabled` | `true` | Enable firewalld role |
| `firewalld_default_zone` | `"public"` | Default firewall zone |
| `firewalld_zones` | `{}` | Dict of zone configurations |
| `firewalld_services` | `[]` | List of services to add |
| `firewalld_masquerade` | `false` | Enable NAT masquerading |
| `firewalld_forward_ports` | `[]` | List of port forwarding rules |

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  roles:
    - david_igou.linux_baseline.firewalld
```
