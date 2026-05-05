# david_igou.linux_baseline.sudoers

## Description

Configure sudo security defaults and privileged access policies. Sets sudo defaults (env_keep, passwd_tries, timeout, logfile) and deploys drop-in configuration files.

## Role Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `sudoers_enabled` | `true` | Enable sudoers role |
| `sudoers_defaults` | Dict of defaults | Sudo defaults configuration |
| `sudoers_dropins` | `[]` | List of drop-in files to deploy |

Default `sudoers_defaults`:

```yaml
sudoers_defaults:
  env_keep: "BLOCKS_COLORS DISPLAY HOSTNAME KDEDIR LS_COLORS PATH PATH_LOCALE PS1 PS2 QTDIR QT_PLUGIN_PATH SELINUX_INIT SESSION_MANAGER TERMINAL USER LANG"
  passwd_tries: 3
  timeout: 5
  logfile: "/var/log/sudo.log"
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  roles:
    - david_igou.linux_baseline.sudoers
```
