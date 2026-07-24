# alloy

Install [Grafana Alloy](https://grafana.com/docs/alloy/latest/) from the
Grafana package repositories and ship the host's systemd journal to a
central Loki push endpoint (the lab's log-gateway).

## Requirements

The target must reach the Grafana package repository
(rpm.grafana.com / apt.grafana.com) and the Loki push endpoint.

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `alloy_enabled` | `true` | Enable and start the service |
| `alloy_loki_url` | `""` | **Required.** Loki push endpoint, e.g. `http://syslog.igou.systems:3500/loki/api/v1/push` |
| `alloy_extra_labels` | `{}` | Static labels merged into `loki.write` `external_labels` |
| `alloy_journal_max_age` | `"12h"` | How far back to replay journal entries on first start |
| `alloy_config_path` | `/etc/alloy/config.alloy` | Rendered config location |

Streams carry `job="systemd-journal"` plus `host` and `unit` from the
journal metadata.

## Example Playbook

```yaml
- hosts: linux_logging
  become: true
  roles:
    - role: david_igou.linux_baseline.alloy
      vars:
        alloy_loki_url: http://syslog.igou.systems:3500/loki/api/v1/push
```

## License

MIT
