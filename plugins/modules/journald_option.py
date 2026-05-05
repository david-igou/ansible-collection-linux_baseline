#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: journald_option
short_version_alternatives: []
long_version: ""
version_added: "1.0.0"
description:
    - Set or remove individual journald.conf directives under C([Journal]), C([Runtime]), and C([Persistent]) sections.
options:
    settings:
        description:
            - Dict of journald directive key-value pairs.
              Keys can be simple names (default to C([Journal]) section) or section-qualified with a dot, e.g., C(Journal.Storage), C(Persistent.Storage).
        required: true
        type: dict
    path:
        description:
            - Path to the journald configuration file.
        type: str
        default: /etc/systemd/journald.conf
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
- name: Set journald options
  david_igou.linux_baseline.journald_option:
    settings:
      Storage: "persistent"
      Compress: "yes"
      MaxFileSec: "1day"
    state: present

- name: Set option in specific section
  david_igou.linux_baseline.journald_option:
    settings:
      Journal.Storage: "volatile"
      Persistent.Storage: "persistent"
    state: present

- name: Remove journald option
  david_igou.linux_baseline.journald_option:
    settings:
      Split: null
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

import os
import re
import shutil

from ansible.module_utils.basic import AnsibleModule


# Default section for unqualified keys
DEFAULT_SECTION = "Journal"

# Known sections in journald.conf
KNOWN_SECTIONS = ["Journal", "Runtime", "Persistent"]


def read_journald_config(file_path):
    """Read the journald.conf file and return lines."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r") as f:
        return f.readlines()


def parse_journald_config(lines):
    """Parse journald.conf lines into a nested dict of section -> {key: value}.

    Returns dict like:
    {
        'Journal': {'Storage': 'volatile', 'Compress': 'yes'},
        'Persistent': {'Storage': 'persistent'},
    }
    """
    config = {}
    current_section = None

    for line in lines:
        stripped = line.strip()

        # Detect section header
        section_match = re.match(r"^\[([A-Za-z]+)\]", stripped)
        if section_match:
            current_section = section_match.group(1)
            if current_section not in config:
                config[current_section] = {}
            continue

        # Parse key=value within a section
        if current_section and "=" in stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip()
            config[current_section][key] = value

    return config


def get_section_and_key(setting_key):
    """Parse a setting key into (section, option_key).

    Supports dotted notation: 'Journal.Storage' -> ('Journal', 'Storage')
    Falls back to default section for simple names: 'Storage' -> ('Journal', 'Storage')
    """
    if "." in setting_key:
        section, _, key = setting_key.partition(".")
        return section, key
    return DEFAULT_SECTION, setting_key


def build_ini_line(key, value):
    """Build a properly formatted INI-style line."""
    return "{0}={1}".format(key, value)


def ensure_section(lines, section_name):
    """Ensure the given section header exists in the lines.

    Appends the section header at the end if it doesn't exist.
    Returns (new_lines, section_index).
    """
    for i, line in enumerate(lines):
        if re.match(r"^\s*\[{0}\]\s*$".format(re.escape(section_name)), line.strip()):
            return lines, i

    # Section not found — append it at the end
    new_lines = list(lines)
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines.append("\n")
    new_lines.append("[{0}]\n".format(section_name))
    return new_lines, len(new_lines) - 1


def apply_settings(file_path, settings, state, backup, check_mode, diff_lines_before):
    """Apply settings to the journald.conf file using section-aware logic.

    Returns (changed_keys, unchanged_keys, removed_keys).
    """
    lines = read_journald_config(file_path)
    config = parse_journald_config(lines)

    changed_keys = []
    unchanged_keys = []
    removed_keys = []

    # Group settings by section for efficient processing
    settings_by_section = {}
    for setting_key, value in settings.items():
        section, key = get_section_and_key(setting_key)
        if section not in settings_by_section:
            settings_by_section[section] = {}
        settings_by_section[section][key] = value

    new_lines = list(lines)

    for section, section_settings in settings_by_section.items():
        # Ensure section header exists
        new_lines, section_start_idx = ensure_section(new_lines, section)

        # Get existing keys in this section from the parsed config
        section_config = config.get(section, {})

        for key, value in section_settings.items():
            if state == "absent":
                # Remove the directive
                if key in section_config:
                    removed_keys.append(key)
                    changed_keys.append(key)
                    pattern = r"^\s*" + re.escape(key) + r"\s*="
                    new_lines = [l for l in new_lines if not re.match(pattern, l.strip())]
                else:
                    # Already absent — idempotent
                    unchanged_keys.append(key)
            else:
                # state == "present"
                line = build_ini_line(key, str(value))
                pattern = r"^\s*" + re.escape(key) + r"\s*="

                # Find existing line in new_lines within this section
                found_idx = None
                for i in range(section_start_idx + 1, len(new_lines)):
                    s = new_lines[i].strip()
                    if not s or s.startswith("#") or re.match(r"^\[", s):
                        break
                    if re.match(pattern, s):
                        found_idx = i
                        break

                current_value = section_config.get(key)

                if found_idx is not None and current_value == str(value):
                    # Already matches — idempotent
                    unchanged_keys.append(key)
                else:
                    changed_keys.append(key)
                    if found_idx is not None:
                        # Replace existing line
                        new_lines[found_idx] = line + "\n"
                    else:
                        # Add new directive at end of section (before next section or EOF)
                        insert_at = len(new_lines)
                        for i in range(section_start_idx + 1, len(new_lines)):
                            s = new_lines[i].strip()
                            if re.match(r"^\[", s):
                                insert_at = i
                                break
                        new_lines.insert(insert_at, line + "\n")

    # Write file if changed and not in check_mode
    if changed_keys or removed_keys:
        if not check_mode:
            if backup and os.path.exists(file_path):
                shutil.copy2(file_path, file_path + ".bak")
            with open(file_path, "w") as f:
                f.writelines(new_lines)

    return changed_keys, unchanged_keys, removed_keys


def main():
    module_args = dict(
        settings=dict(type="dict", required=True),
        path=dict(type="str", default="/etc/systemd/journald.conf"),
        backup=dict(type="bool", default=False),
        state=dict(type="str", default="present", choices=["present", "absent"]),
    )

    module = AnsibleModule(
        argument_spec=module_args,
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
