#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: sysctl_profile
short_description: Manage sysctl drop-in files in /etc/sysctl.d/
version_added: "1.0.0"
description:
    - Creates or manages drop-in files in /etc/sysctl.d/ for kernel parameter tuning.
options:
    settings:
        description:
            - Dict of sysctl key-value pairs.
              Keys are dot-notation (e.g., C(net.ipv4.ip_forward)).
        required: true
        type: dict
    path:
        description:
            - Full path to the sysctl drop-in file.
              If not specified, it is derived from C(prefix) and C(order).
        type: str
        default: null
    prefix:
        description:
            - Filename prefix for the drop-in file under /etc/sysctl.d/.
        type: str
        default: 99-custom
    order:
        description:
            - Numeric suffix appended to filename. Load order determines precedence.
        type: int
        default: 1
    backup:
        description:
            - Whether to create a .bak backup before modification.
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
- name: Set sysctl parameters
  david_igou.linux_baseline.sysctl_profile:
    settings:
      net.ipv4.ip_forward: "1"
      net.ipv4.conf.all.rp_filter: "1"
      kernel.pid_max: "65536"
    prefix: 50-hardening
    order: 1

- name: Remove a sysctl parameter
  david_igou.linux_baseline.sysctl_profile:
    settings:
      net.ipv4.ip_forward: null
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
    description: Path to the created/modified sysctl drop-in file.
    type: str
    returned: changed
backup_file:
    description: Path to the backup file if backup was enabled.
    type: str
    returned: changed,backup
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


def build_sysctl_path(prefix, order):
    """Build the full path to the sysctl drop-in file."""
    filename = "{0}_{1}_custom.conf".format(prefix, order)
    return "/etc/sysctl.d/{0}".format(filename)


def read_sysctl_file(file_path):
    """Read the sysctl drop-in file and return lines."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r") as f:
        return f.readlines()


def parse_sysctl_file(lines):
    """Parse sysctl file lines into a dict of key -> value.

    Returns dict like {'net.ipv4.ip_forward': '1', 'kernel.pid_max': '65536'}
    Handles comments and blank lines.
    """
    config = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split("=", 1)
        if len(parts) == 2:
            key, value = parts[0].strip(), parts[1].strip()
            config[key] = value
    return config


def build_sysctl_line(key, value):
    """Build a properly formatted sysctl line."""
    return "{0} = {1}".format(key, value)


def apply_settings(file_path, settings, state, backup, check_mode):
    """Apply settings to the sysctl drop-in file.

    Returns (changed_keys, unchanged_keys, removed_keys, modified_lines).
    """
    lines = read_sysctl_file(file_path)
    config = parse_sysctl_file(lines)

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
                new_lines = [l for l in new_lines if not re.match(
                    r"^\s*" + re.escape(key) + r"\s*=", l)]
            else:
                # Already absent — idempotent
                unchanged_keys.append(key)
        else:
            # state == "present"
            line = build_sysctl_line(key, value)
            if key in config and config[key] == str(value):
                # Already matches — idempotent
                unchanged_keys.append(key)
            else:
                changed_keys.append(key)
                if key in config:
                    # Replace existing line
                    new_lines = [re.sub(
                        r"^\s*" + re.escape(key) + r"\s*=.*", line, l)
                        for l in new_lines]
                else:
                    # Add new directive at the end
                    new_lines.append(line + "\n")

    # Write file if changed and not in check_mode
    if changed_keys or removed_keys:
        if not check_mode:
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            if backup and os.path.exists(file_path):
                shutil.copy2(file_path, file_path + ".bak")
            with open(file_path, "w") as f:
                f.writelines(new_lines)

    return changed_keys, unchanged_keys, removed_keys


def main():
    module_args = dict(
        settings=dict(type="dict", required=True),
        path=dict(type="str", default=None),
        prefix=dict(type="str", default="99-custom"),
        order=dict(type="int", default=1),
        backup=dict(type="bool", default=False),
        state=dict(type="str", default="present", choices=["present", "absent"]),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    settings = module.params["settings"]
    path = module.params["path"]
    prefix = module.params["prefix"]
    order = module.params["order"]
    backup = module.params["backup"]
    state = module.params["state"]
    check_mode = module.check_mode

    if not settings:
        module.fail_json(msg="settings parameter is required and must be a non-empty dict.")

    if path is None:
        file_path = build_sysctl_path(prefix, order)
    else:
        file_path = path

    changed_keys, unchanged_keys, removed_keys = apply_settings(
        file_path=file_path,
        settings=settings,
        state=state,
        backup=backup,
        check_mode=check_mode,
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
        if backup:
            result["backup_file"] = file_path + ".bak"

    module.exit_json(**result)


if __name__ == "__main__":
    main()
