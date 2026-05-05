# Copyright (c) Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import sys

from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "plugins", "modules"))


def _make_mock_module(params=None, check_mode=False):
    """Create a mock AnsibleModule that captures exit_json/fail_json calls."""
    mock = MagicMock(spec=["params", "check_mode", "exit_json", "fail_json"])
    mock.check_mode = check_mode
    mock.params = params or {
        "settings": {"Storage": "persistent"},
        "path": "/etc/systemd/journald.conf",
        "backup": False,
        "state": "present",
    }
    mock.exit_json_calls = []
    mock.fail_json_calls = []

    def _exit_json(**kwargs):
        mock.exit_json_calls.append(kwargs)
        raise SystemExit(0)

    def _fail_json(**kwargs):
        mock.fail_json_calls.append(kwargs)
        raise SystemExit(1)

    mock.exit_json.side_effect = _exit_json
    mock.fail_json.side_effect = _fail_json

    return mock


def _run_module(journald_option, params, check_mode=False):
    """Helper: patch AnsibleModule.__init__ and run journald_option.main()."""
    mock = _make_mock_module(params=params, check_mode=check_mode)

    captured_params = dict(params)

    def mock_init(self, *args, **kwargs):
        self.params = captured_params
        self.check_mode = check_mode

    with patch.object(journald_option.AnsibleModule, "__init__", mock_init):
        with patch.object(journald_option.AnsibleModule, "exit_json") as mock_exit:
            with patch.object(journald_option.AnsibleModule, "fail_json") as mock_fail:
                mock_exit.side_effect = mock.exit_json.side_effect
                mock_fail.side_effect = mock.fail_json.side_effect
                try:
                    journald_option.main()
                except SystemExit:
                    pass

    return mock


class TestJournaldOptionArgumentSpec:
    """Test argument_spec definition."""

    def test_module_has_main(self):
        """Module must define main function."""
        import journald_option

        assert hasattr(journald_option, "main")
        assert callable(journald_option.main)


class TestJournaldOptionSetSingleSetting:
    """Test setting a single journald.conf option in [Journal] section."""

    def test_sets_single_option_in_file(self, tmp_path):
        """Setting Storage to 'persistent' should write it under [Journal]."""
        import journald_option

        config = tmp_path / "journald.conf"
        config.write_text("[Journal]\nStorage=auto\nCompress=yes\n")

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Storage": "persistent"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        assert len(mock.exit_json_calls) == 1
        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        assert "Storage" in result.get("changed_keys", [])

    def test_returns_file_path(self, tmp_path):
        """Return value should include the file path."""
        import journald_option

        config = tmp_path / "journald.conf"
        config.write_text("[Journal]\nStorage=auto\n")

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Storage": "persistent"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert "file" in result
        assert result["file"] == str(config)


class TestJournaldOptionIdempotency:
    """Test idempotency: running twice produces changed=false."""

    def test_idempotent_on_second_run(self, tmp_path):
        """Second run with same settings should report no changes and unchanged_keys."""
        import journald_option

        config = tmp_path / "journald.conf"
        config.write_text("[Journal]\nStorage=persistent\nCompress=yes\n")

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Storage": "persistent"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is False
        assert "Storage" in result.get("unchanged_keys", [])


class TestJournaldOptionMultipleSettings:
    """Test setting multiple journald.conf options at once."""

    def test_sets_multiple_options(self, tmp_path):
        """Setting multiple options should change all of them."""
        import journald_option

        config = tmp_path / "journald.conf"
        config.write_text("[Journal]\nStorage=auto\nCompress=no\nMaxFileSec=1week\n")

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Storage": "persistent", "Compress": "yes"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        changed = result.get("changed_keys", [])
        assert "Storage" in changed
        assert "Compress" in changed


class TestJournaldOptionStateAbsent:
    """Test state=absent removes options from config."""

    def test_removes_option_when_state_absent(self, tmp_path):
        """state=absent should remove the directive from journald.conf."""
        import journald_option

        config = tmp_path / "journald.conf"
        config.write_text("[Journal]\nStorage=persistent\nCompress=yes\n")

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Compress": None},
                "path": str(config),
                "backup": False,
                "state": "absent",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        assert "Compress" in result.get("removed_keys", [])


class TestJournaldOptionValidation:
    """Test input validation."""

    def test_fails_without_settings(self):
        """Module should fail if settings is not provided."""
        import journald_option

        mock = _run_module(
            journald_option,
            params={
                "settings": None,
                "path": "/etc/systemd/journald.conf",
                "backup": False,
                "state": "present",
            },
        )

        assert len(mock.fail_json_calls) == 1


class TestJournaldOptionCheckMode:
    """Test check_mode support."""

    def test_check_mode_reports_changes_without_modifying(self, tmp_path):
        """In check_mode, module reports changed=True but does not modify file."""
        import journald_option

        config = tmp_path / "journald.conf"
        original_content = "[Journal]\nStorage=auto\nCompress=no\n"
        config.write_text(original_content)

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Storage": "persistent", "Compress": "yes"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
            check_mode=True,
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        assert config.read_text() == original_content


class TestJournaldOptionBackup:
    """Test backup functionality."""

    def test_creates_backup_when_enabled(self, tmp_path):
        """backup=True should create a .bak file before modification."""
        import journald_option

        config = tmp_path / "journald.conf"
        config.write_text("[Journal]\nStorage=auto\nCompress=no\n")

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Storage": "persistent", "Compress": "yes"},
                "path": str(config),
                "backup": True,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        backup_path = str(config) + ".bak"
        assert os.path.exists(backup_path)


class TestJournaldOptionNewSection:
    """Test adding options to a section that doesn't exist yet."""

    def test_creates_new_section(self, tmp_path):
        """Adding Persistent.Storage when [Persistent] doesn't exist should create the section."""
        import journald_option

        config = tmp_path / "journald.conf"
        config.write_text("[Journal]\nStorage=auto\n")

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Persistent.Storage": "persistent"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        content = config.read_text()
        assert "[Persistent]" in content
        assert "Storage=persistent" in content


class TestJournaldOptionAbsentIdempotent:
    """Test state=absent idempotency."""

    def test_absent_idempotent_when_already_removed(self, tmp_path):
        """state=absent on already-removed key should be idempotent."""
        import journald_option

        config = tmp_path / "journald.conf"
        config.write_text("[Journal]\nStorage=persistent\n")

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Compress": None},
                "path": str(config),
                "backup": False,
                "state": "absent",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is False
        assert "Compress" in result.get("unchanged_keys", [])


class TestJournaldOptionDottedSection:
    """Test dotted notation for cross-section settings."""

    def test_sets_option_in_different_section(self, tmp_path):
        """Using Journal.MaxLevelFile should set it under [Journal]."""
        import journald_option

        config = tmp_path / "journald.conf"
        config.write_text("[Journal]\nStorage=auto\n")

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Journal.MaxLevelFile": "debug"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        content = config.read_text()
        assert "[Journal]" in content
        assert "MaxLevelFile=debug" in content


class TestJournaldOptionPreservesComments:
    """Test that comments and formatting are preserved."""

    def test_preserves_comments_in_file(self, tmp_path):
        """Modifying one directive should preserve other comments."""
        import journald_option

        config = tmp_path / "journald.conf"
        original = "# Journal Configuration\n[Journal]\n# Storage backend\nStorage=auto\nCompress=yes\n# End of file\n"
        config.write_text(original)

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Storage": "persistent"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        content = config.read_text()
        assert "# Journal Configuration" in content
        assert "# Storage backend" in content
        assert "# End of file" in content


class TestJournaldOptionEmptyFile:
    """Test setting options on an empty/new config file."""

    def test_works_on_empty_file(self, tmp_path):
        """Setting options on an empty file should create the [Journal] section."""
        import journald_option

        config = tmp_path / "journald.conf"
        config.write_text("")

        mock = _run_module(
            journald_option,
            params={
                "settings": {"Storage": "persistent", "Compress": "yes"},
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        content = config.read_text()
        assert "[Journal]" in content
        assert "Storage=persistent" in content
        assert "Compress=yes" in content


class TestJournaldOptionMixedSections:
    """Test setting options across multiple sections in one call."""

    def test_sets_options_in_multiple_sections(self, tmp_path):
        """Setting Journal.Storage and Runtime.MaxFileSec should work together."""
        import journald_option

        config = tmp_path / "journald.conf"
        config.write_text("[Journal]\nStorage=auto\n")

        mock = _run_module(
            journald_option,
            params={
                "settings": {
                    "Journal.Storage": "persistent",
                    "Runtime.MaxFileSec": "1day",
                },
                "path": str(config),
                "backup": False,
                "state": "present",
            },
        )

        result = mock.exit_json_calls[0]
        assert result.get("changed") is True
        content = config.read_text()
        assert "[Journal]" in content
        assert "[Runtime]" in content
        assert "Storage=persistent" in content
        assert "MaxFileSec=1day" in content
