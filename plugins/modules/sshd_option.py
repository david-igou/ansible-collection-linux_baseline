#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: sshd_option
short_description: Set or remove sshd_config directives
version_added: "1.0.0"
description:
    - Set or remove individual sshd_config directives.
options:
    settings:
        description:
            - Dict of sshd directive key-value pairs.
              Keys match sshd_config option names (e.g., C(PermitRootLogin)).
        required: true
        type: dict
    path:
        description:
            - Path to the sshd configuration file.
        type: str
        default: /etc/ssh/sshd_config
    backup:
        description:
            - Whether to create a .bak backup of the file before modification.
        type: bool
        default: false
    state:
        description:
            - C(present) sets directives; C(absent) removes them from the file.
        type: str
        default: present
        choices: [present, absent]
author:
    - IGOU (@igou)
"""

EXAMPLES = r"""
- name: Set sshd options
  david_igou.linux_baseline.sshd_option:
    settings:
      PermitRootLogin: "no"
      MaxAuthTries: "3"
      PasswordAuthentication: "no"
    state: present

- name: Remove sshd option
  david_igou.linux_baseline.sshd_option:
    settings:
      X11Forwarding: null
    state: absent
"""

RETURN = r"""
changed:
    description: Whether any settings were modified.
    type: bool
    returned: always
changed_keys:
    description: Keys that were actually changed on this run.
    type: list
    elements: str
    returned: always
unchanged_keys:
    description: Keys already matching desired state.
    type: list
    elements: str
    returned: always
removed_keys:
    description: Keys removed when state=absent.
    type: list
    elements: str
    returned: always
file:
    description: Path to the modified configuration file.
    type: str
    returned: changed
"""
ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["stableinterface"],
    "supported_by": "community",
}

import os
import re
import shutil

from ansible.module_utils.basic import AnsibleModule

argument_spec = dict(
    settings=dict(type="dict", required=True),
    path=dict(type="str", default="/etc/ssh/sshd_config"),
    backup=dict(type="bool", default=False),
    state=dict(type="str", default="present", choices=["present", "absent"]),
)


def read_sshd_config(file_path):
    """Read the sshd_config file and return lines."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r") as f:
        return f.readlines()


def parse_sshd_config(lines):
    """Parse sshd_config lines into a dict of key -> value.

    Returns dict like {'PermitRootLogin': 'yes', 'MaxAuthTries': '4'}
    Handles comments and blank lines.
    """
    config = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        if len(parts) == 2:
            key, value = parts
            config[key] = value
    return config


def build_line(key, value):
    """Build a properly formatted sshd_config line."""
    return "{0} {1}".format(key, value)


def apply_settings(file_path, settings, state, backup, check_mode, diff_lines_before):
    """Apply settings to the sshd_config file using lineinfile logic.

    Returns (changed_keys, unchanged_keys, removed_keys, modified_lines).
    """
    lines = read_sshd_config(file_path)
    config = parse_sshd_config(lines)

    changed_keys = []
    unchanged_keys = []
    removed_keys = []
    new_lines = list(lines)

    for key, value in settings.items():
        if state == "absent":
            # Remove the directive
            if key in config:
                removed_keys.append(key)
                changed_keys.append(key)
                new_lines = [l for l in new_lines if not re.match(r"^\s*" + re.escape(key) + r"\b", l)]
            else:
                # Already absent — idempotent
                unchanged_keys.append(key)
        else:
            # state == "present"
            line = build_line(key, value)
            if key in config and config[key] == str(value):
                # Already matches — idempotent
                unchanged_keys.append(key)
            else:
                changed_keys.append(key)
                if key in config:
                    # Replace existing line
                    new_lines = [re.sub(r"^\s*" + re.escape(key) + r"\b.*", line, l) for l in new_lines]
                else:
                    # Add new directive at the end (before trailing comments)
                    new_lines.append(line + "\n")

    # Write file if changed and not in check_mode
    if changed_keys or removed_keys:
        if not check_mode:
            if backup and os.path.exists(file_path):
                shutil.copy2(file_path, file_path + ".bak")
            with open(file_path, "w") as f:
                f.writelines(new_lines)

    return changed_keys, unchanged_keys, removed_keys


def main():
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    settings = module.params["settings"]
    file_path = module.params["path"]
    backup = module.params["backup"]
    state = module.params["state"]
    check_mode = module.check_mode

    if not settings:
        module.fail_json(msg="settings parameter is required and must be a non-empty dict.")

    changed_keys, unchanged_keys, removed_keys = apply_settings(
        file_path=file_path,
        settings=settings,
        state=state,
        backup=backup,
        check_mode=check_mode,
        diff_lines_before=None,
    )

    any_changed = bool(changed_keys or removed_keys)

    result = dict(
        changed=any_changed,
        changed_keys=changed_keys,
        unchanged_keys=unchanged_keys,
        removed_keys=removed_keys,
    )

    if any_changed:
        result["file"] = file_path

    module.exit_json(**result)


if __name__ == "__main__":
    main()
