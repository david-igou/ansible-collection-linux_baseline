# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import sys

import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "plugins", "modules"))


def _make_mock_module(params=None, check_mode=False):
    """Create a mock AnsibleModule that captures exit_json/fail_json calls."""
    mock = MagicMock(spec=["params", "check_mode", "exit_json", "fail_json"])
    mock.check_mode = check_mode
    mock.params = params or {
        "settings": {"PermitRootLogin": "no"},
        "path": "/etc/ssh/sshd_config",
        "backup": False,
        "state": "present",
    }
    mock.exit_json_calls = []
    mock.fail_json_calls = []

    def _exit_json(**kwargs):
        mock.exit_json_calls.append(kwargs)

    def _fail_json(**kwargs):
        mock.fail_json_calls.append(kwargs)
        raise SystemExit(1)

    def _exit_json(**kwargs):
        mock.exit_json_calls.append(kwargs)
        raise SystemExit(0)

    mock.exit_json_side_effect = _exit_json
    mock.fail_json_side_effect = _fail_json
    mock.exit_json.side_effect = _exit_json
    mock.fail_json.side_effect = _fail_json

    return mock


def _run_module(sshd_option, params, check_mode=False):
    """Helper: patch AnsibleModule.__init__ and run sshd_option.main()."""
    mock = _make_mock_module(params=params, check_mode=check_mode)

    captured_params = dict(params)

    # Mock __init__ to prevent real AnsibleModule from reading stdin
    def mock_init(self, *args, **kwargs):
        self.params = captured_params
        self.check_mode = check_mode

    with patch.object(sshd_option.AnsibleModule, "__init__", mock_init):
        with patch.object(sshd_option.AnsibleModule, "exit_json") as mock_exit:
            with patch.object(sshd_option.AnsibleModule, "fail_json") as mock_fail:
                mock_exit.side_effect = mock.exit_json_side_effect
                mock_fail.side_effect = mock.fail_json_side_effect
                try:
                    sshd_option.main()
                except SystemExit:
                    pass

    return mock


class TestSshdOptionArgumentSpec:
    """Test argument_spec definition."""

    def test_module_has_main(self):
        """Module must define main function."""
        import sshd_option

        assert hasattr(sshd_option, "main")
        assert callable(sshd_option.main)


class TestSshdOptionSetSingleSetting:
    """Test setting a single sshd_config option."""

    def test_sets_single_option_in_file(self, tmp_path):
        """Setting PermitRootLogin to 'no' should write it to the config file."""
        import sshd_option

        config = tmp_path / "sshd_config"
        config.write_text("# sshd config\nPermitRootLogin yes\nMaxAuthTries 4\n")

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"PermitRootLogin": "no"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        assert len(mock.exit_json_calls) == 1
        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        assert "PermitRootLogin" in result.get("changed_keys", [])

    def test_returns_file_path(self, tmp_path):
        """Return value should include the file path."""
        import sshd_option

        config = tmp_path / "sshd_config"
        config.write_text("# sshd config\nPermitRootLogin yes\n")

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"PermitRootLogin": "no"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert "file" in result
        assert result["file"] == str(config)


class TestSshdOptionIdempotency:
    """Test idempotency: running twice produces changed=false."""

    def test_idempotent_on_second_run(self, tmp_path):
        """Second run with same settings should report no changes and unchanged_keys."""
        import sshd_option

        config = tmp_path / "sshd_config"
        config.write_text("# sshd config\nPermitRootLogin no\n")

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"PermitRootLogin": "no"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is False
        assert "PermitRootLogin" in result.get("unchanged_keys", [])


class TestSshdOptionMultipleSettings:
    """Test setting multiple sshd_config options at once."""

    def test_sets_multiple_options(self, tmp_path):
        """Setting multiple options should change all of them."""
        import sshd_option

        config = tmp_path / "sshd_config"
        config.write_text("# sshd config\nPermitRootLogin yes\nMaxAuthTries 4\nPasswordAuthentication yes\n")

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"PermitRootLogin": "no", "MaxAuthTries": "3"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        changed = result.get("changed_keys", [])
        assert "PermitRootLogin" in changed
        assert "MaxAuthTries" in changed


class TestSshdOptionStateAbsent:
    """Test state=absent removes options from config."""

    def test_removes_option_when_state_absent(self, tmp_path):
        """state=absent should remove the directive from sshd_config."""
        import sshd_option

        config = tmp_path / "sshd_config"
        config.write_text("# sshd config\nPermitRootLogin yes\nMaxAuthTries 4\n")

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"PermitRootLogin": None},
                "path": str(config),
                "backup": False,
                "state": "absent",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        assert "PermitRootLogin" in result.get("removed_keys", [])


class TestSshdOptionValidation:
    """Test input validation."""

    def test_fails_without_settings(self):
        """Module should fail if settings is not provided."""
        import sshd_option

        mock = _run_module(
            sshd_option,
            params={
                "settings": None,
                "path": "/etc/ssh/sshd_config",
                "backup": False,
                "state": "present",
            },
        )

        assert len(mock.fail_json_calls) == 1


class TestSshdOptionCheckMode:
    """Test check_mode support."""

    def test_check_mode_reports_changes_without_modifying(self, tmp_path):
        """In check_mode, module reports changed=True but does not modify file."""
        import sshd_option

        config = tmp_path / "sshd_config"
        original_content = "# sshd config\nPermitRootLogin yes\n"
        config.write_text(original_content)

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"PermitRootLogin": "no"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
            check_mode=True,
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        assert config.read_text() == original_content


class TestSshdOptionBackup:
    """Test backup functionality."""

    def test_creates_backup_when_enabled(self, tmp_path):
        """backup=True should create a .bak file before modification."""
        import sshd_option

        config = tmp_path / "sshd_config"
        config.write_text("# sshd config\nPermitRootLogin yes\n")

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"PermitRootLogin": "no"},
                "path": str(config),
                "backup": True,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        backup_path = str(config) + ".bak"
        assert os.path.exists(backup_path)


class TestSshdOptionNewOption:
    """Test adding a new option not currently in the config."""

    def test_adds_new_option_to_file(self, tmp_path):
        """Adding an option not present in the file should create it."""
        import sshd_option

        config = tmp_path / "sshd_config"
        config.write_text("# sshd config\nPermitRootLogin yes\n")

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"X11Forwarding": "no"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        assert "X11Forwarding" in result.get("changed_keys", [])


class TestSshdOptionAbsentIdempotent:
    """Test state=absent idempotency."""

    def test_absent_idempotent_when_already_removed(self, tmp_path):
        """state=absent on already-removed key should be idempotent."""
        import sshd_option

        config = tmp_path / "sshd_config"
        config.write_text("# sshd config\nMaxAuthTries 4\n")

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"PermitRootLogin": None},
                "path": str(config),
                "backup": False,
                "state": "absent",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is False
        assert "PermitRootLogin" in result.get("unchanged_keys", [])


class TestSshdOptionValueTypes:
    """Test that values are properly stringified."""

    def test_numeric_values_work(self, tmp_path):
        """Numeric string values should be written as-is."""
        import sshd_option

        config = tmp_path / "sshd_config"
        config.write_text("# sshd config\nMaxAuthTries 4\n")

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"MaxAuthTries": "6"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        content = config.read_text()
        assert "MaxAuthTries 6" in content


class TestSshdOptionPreservesComments:
    """Test that comments and formatting are preserved."""

    def test_preserves_comments_in_file(self, tmp_path):
        """Modifying one directive should preserve other comments."""
        import sshd_option

        config = tmp_path / "sshd_config"
        original = "# SSH Server Configuration\n# Security settings\nPermitRootLogin yes\n# End of file\n"
        config.write_text(original)

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"PermitRootLogin": "no"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        content = config.read_text()
        assert "# SSH Server Configuration" in content
        assert "# Security settings" in content
        assert "# End of file" in content


class TestSshdOptionNewOptionWithComment:
    """Test adding new option with comment header."""

    def test_adds_new_option_with_proper_formatting(self, tmp_path):
        """Adding a new option should append it properly."""
        import sshd_option

        config = tmp_path / "sshd_config"
        config.write_text("# sshd config\nPermitRootLogin yes\n")

        mock = _run_module(
            sshd_option,
            params={
                "settings": {"X11Forwarding": "no"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        content = config.read_text()
        assert "X11Forwarding no" in content
