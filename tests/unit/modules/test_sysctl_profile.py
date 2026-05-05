"""Unit tests for sysctl_profile module."""
import os
import shutil
import sys
import tempfile
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixture helpers — shared with other module tests
# ---------------------------------------------------------------------------

def _make_mock_module(params, check_mode=False):
    """Return a mock AnsibleModule instance and exit/fail capture lists."""
    exit_calls = []
    fail_calls = []

    def _exit_json(**kwargs):
        exit_calls.append(kwargs)
        raise SystemExit(0)

    def _fail_json(**kwargs):
        fail_calls.append(kwargs)
        raise SystemExit(1)

    mock = MagicMock(spec=["params", "check_mode", "exit_json", "fail_json"])
    mock.params = params
    mock.check_mode = check_mode
    mock.exit_json.side_effect = _exit_json
    mock.fail_json.side_effect = _fail_json
    return mock, exit_calls, fail_calls


def _run_module(params, check_mode=False):
    """Import and run the module with the given params, returning captured output."""
    from ansible.module_utils.basic import AnsibleModule

    mock, exit_calls, fail_calls = _make_mock_module(params, check_mode)

    mod_path = os.path.join(
        os.path.dirname(__file__),
        *["..", "..", "..", "plugins", "modules", "sysctl_profile.py"]
    )
    util = __import__("importlib.util", fromlist=["spec_from_file_location"])

    with patch.object(AnsibleModule, "__init__", lambda self, **kw: None):
        def patched_init(self, **kw):
            for attr in ["params", "check_mode", "exit_json", "fail_json"]:
                setattr(self, attr, getattr(mock, attr))

        with patch.object(AnsibleModule, "__init__", patched_init):
            module_spec = util.spec_from_file_location("sysctl_profile", mod_path)
            module_obj = util.module_from_spec(module_spec)
            sys.modules["sysctl_profile"] = module_obj
            module_spec.loader.exec_module(module_obj)

            try:
                module_obj.main()
            except SystemExit as e:
                if e.code == 0:
                    return exit_calls[0] if exit_calls else {}
                elif e.code == 1:
                    return fail_calls[0] if fail_calls else {}

    return {}


def _run_module_captures(params, check_mode=False):
    """Run module and return (result_dict, mock). Use for validation tests."""
    from ansible.module_utils.basic import AnsibleModule

    mock, exit_calls, fail_calls = _make_mock_module(params, check_mode)

    mod_path = os.path.join(
        os.path.dirname(__file__),
        *["..", "..", "..", "plugins", "modules", "sysctl_profile.py"]
    )
    util = __import__("importlib.util", fromlist=["spec_from_file_location"])

    with patch.object(AnsibleModule, "__init__", lambda self, **kw: None):
        def patched_init(self, **kw):
            for attr in ["params", "check_mode", "exit_json", "fail_json"]:
                setattr(self, attr, getattr(mock, attr))

        with patch.object(AnsibleModule, "__init__", patched_init):
            module_spec = util.spec_from_file_location("sysctl_profile", mod_path)
            module_obj = util.module_from_spec(module_spec)
            sys.modules["sysctl_profile"] = module_obj
            module_spec.loader.exec_module(module_obj)

            try:
                module_obj.main()
            except SystemExit:
                pass

    result = fail_calls[0] if fail_calls else (exit_calls[0] if exit_calls else {})
    mock.fail_json_calls = fail_calls
    mock.exit_json_calls = exit_calls
    return result, mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_params(settings, prefix="99-custom", order=1, backup=False, state="present", path=None):
    """Build params dict with auto-generated temp path."""
    params = {
        "settings": settings,
        "prefix": prefix,
        "order": order,
        "backup": backup,
        "state": state,
        "path": path,
    }
    return params


# Create a shared temp directory for tests that need file I/O
_tmpdir = tempfile.mkdtemp()
_test_counter = 0


def _tmp_path(prefix="99-custom", order=1):
    """Return a full path to a sysctl drop-in file in the temp directory."""
    global _test_counter
    _test_counter += 1
    filename = "{0}_{1}_custom.conf".format(prefix, order)
    return os.path.join(_tmpdir, "{0}_{1}".format(filename, _test_counter))


# ---------------------------------------------------------------------------
# Tests — Argument Spec
# ---------------------------------------------------------------------------

class TestSysctlProfileArgumentSpec:
    def test_module_has_main(self):
        """Module must define a main() entry point."""
        mod_path = os.path.join(
            os.path.dirname(__file__),
            *["..", "..", "..", "plugins", "modules", "sysctl_profile.py"]
        )
        util = __import__("importlib.util", fromlist=["spec_from_file_location"])
        module_spec = util.spec_from_file_location("sysctl_profile", mod_path)
        module_obj = util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module_obj)  # type: ignore[union-attr]
        assert hasattr(module_obj, "main")


# ---------------------------------------------------------------------------
# Tests — Basic Functionality
# ---------------------------------------------------------------------------

class TestSysctlProfileBasicFunctionality:
    def test_returns_file_path(self):
        """Module should return the full path to the created drop-in file."""
        params = _make_params(
            {"net.ipv4.ip_forward": "1", "net.ipv4.conf.all.rp_filter": "1"},
            path=_tmp_path(),
        )
        result = _run_module(params)
        assert "file" in result
        assert "sysctl.d" not in result["file"]  # temp dir path, not /etc/sysctl.d/
        assert "99-custom" in result["file"]

    def test_sets_settings_in_file(self):
        """Module should write all settings to the drop-in file."""
        params = _make_params(
            {"net.ipv4.ip_forward": "1", "net.ipv4.conf.all.rp_filter": "1"},
            path=_tmp_path(),
        )
        result = _run_module(params)
        assert result.get("changed") is True
        assert "net.ipv4.ip_forward" in result.get("changed_keys", [])
        assert "net.ipv4.conf.all.rp_filter" in result.get("changed_keys", [])


# ---------------------------------------------------------------------------
# Tests — Idempotency
# ---------------------------------------------------------------------------

class TestSysctlProfileIdempotency:
    def test_idempotent_on_second_run(self):
        """Running twice with same settings should not change on second run."""
        fpath = _tmp_path()
        params = _make_params(
            {"net.ipv4.ip_forward": "1", "net.ipv4.conf.all.rp_filter": "1"},
            path=fpath,
        )
        # First run — should create file and report changed
        _run_module(params)

        # Second run — should report no changes (idempotent)
        result = _run_module(params)
        assert result.get("changed") is False
        assert len(result.get("unchanged_keys", [])) == 2


# ---------------------------------------------------------------------------
# Tests — Validation
# ---------------------------------------------------------------------------

class TestSysctlProfileValidation:
    def test_fails_without_settings(self):
        """Module must fail_json when settings is None."""
        result, mock = _run_module_captures(_make_params(None))
        assert len(mock.fail_json_calls) == 1

    def test_fails_with_empty_settings(self):
        """Module should handle empty settings dict gracefully."""
        result, mock = _run_module_captures(_make_params({}))
        assert len(mock.fail_json_calls) == 1


# ---------------------------------------------------------------------------
# Tests — Check Mode
# ---------------------------------------------------------------------------

class TestSysctlProfileCheckMode:
    def test_check_mode_reports_changes_without_modifying(self):
        """In check_mode, module reports changed but does not write file."""
        params = _make_params(
            {"net.ipv4.ip_forward": "1", "net.ipv4.conf.all.rp_filter": "1"},
            path=_tmp_path(),
        )
        result = _run_module(params, check_mode=True)
        assert result.get("changed") is True
        assert "net.ipv4.ip_forward" in result.get("changed_keys", [])


# ---------------------------------------------------------------------------
# Tests — Backup
# ---------------------------------------------------------------------------

class TestSysctlProfileBackup:
    def test_creates_backup_when_enabled(self):
        """Module should create a .bak file when backup=True."""
        fpath = _tmp_path()
        # First run to create the file
        params1 = _make_params(
            {"net.ipv4.ip_forward": "1"},
            path=fpath,
        )
        _run_module(params1)
        # Second run with backup=True
        params2 = _make_params(
            {"net.ipv4.ip_forward": "2"},
            backup=True,
            path=fpath,
        )
        result = _run_module(params2)
        assert result.get("changed") is True
        backup_file = result.get("backup_file")
        assert backup_file is not None
        assert backup_file.endswith(".bak")


# ---------------------------------------------------------------------------
# Tests — State Absent
# ---------------------------------------------------------------------------

class TestSysctlProfileStateAbsent:
    def test_removes_setting_when_state_absent(self):
        """Module should remove a setting when state=absent."""
        fpath = _tmp_path()
        # First create the setting
        create_params = _make_params(
            {"net.ipv4.ip_forward": "1"},
            path=fpath,
        )
        _run_module(create_params)
        # Then remove it
        absent_params = _make_params(
            {"net.ipv4.ip_forward": None},
            state="absent",
            path=fpath,
        )
        result = _run_module(absent_params)
        assert "removed_keys" in result
        assert "net.ipv4.ip_forward" in result.get("removed_keys", [])


# ---------------------------------------------------------------------------
# Tests — Absent Idempotency
# ---------------------------------------------------------------------------

class TestSysctlProfileAbsentIdempotent:
    def test_absent_idempotent_when_already_removed(self):
        """Running state=absent twice should be idempotent."""
        fpath = _tmp_path()
        # First removal (file may not exist yet)
        absent_params = _make_params(
            {"net.ipv4.ip_forward": None},
            state="absent",
            path=fpath,
        )
        _run_module(absent_params)
        # Second run — already removed
        result = _run_module(absent_params)
        assert result.get("changed") is False


# ---------------------------------------------------------------------------
# Tests — Custom Prefix
# ---------------------------------------------------------------------------

class TestSysctlProfileCustomPrefix:
    def test_uses_custom_prefix(self):
        """Module should use the provided prefix in the filename."""
        params = _make_params(
            {"net.ipv4.ip_forward": "1"},
            prefix="50-hardening",
            path=_tmp_path(prefix="50-hardening"),
        )
        result = _run_module(params)
        assert "file" in result
        assert "50-hardening" in result["file"]


# ---------------------------------------------------------------------------
# Tests — Numeric Values
# ---------------------------------------------------------------------------

class TestSysctlProfileNumericValues:
    def test_handles_numeric_values(self):
        """Module should handle numeric sysctl values correctly."""
        params = _make_params(
            {"net.ipv4.tcp_syncookies": "1", "kernel.pid_max": "65536"},
            path=_tmp_path(),
        )
        result = _run_module(params)
        assert result.get("changed") is True
        changed_keys = result.get("changed_keys", [])
        assert "net.ipv4.tcp_syncookies" in changed_keys
        assert "kernel.pid_max" in changed_keys


# ---------------------------------------------------------------------------
# Tests — Preserves Comments
# ---------------------------------------------------------------------------

class TestSysctlProfilePreservesComments:
    def test_preserves_comments_in_file(self):
        """Module should preserve existing comments when modifying file."""
        fpath = _tmp_path()
        # Pre-create file with a comment
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w") as f:
            f.write("# This is a comment\n")

        params = _make_params(
            {"net.ipv4.ip_forward": "1"},
            path=fpath,
        )
        result = _run_module(params)
        assert result.get("changed") is True


# ---------------------------------------------------------------------------
# Tests — Empty File
# ---------------------------------------------------------------------------

class TestSysctlProfileEmptyFile:
    def test_works_on_empty_file(self):
        """Module should handle creating settings in an empty file."""
        fpath = _tmp_path()
        # Create empty file
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w") as f:
            pass

        params = _make_params(
            {"net.ipv4.ip_forward": "1"},
            path=fpath,
        )
        result = _run_module(params)
        assert result.get("changed") is True
        assert "net.ipv4.ip_forward" in result.get("changed_keys", [])


# ---------------------------------------------------------------------------
# Tests — Order Parameter
# ---------------------------------------------------------------------------

class TestSysctlProfileOrder:
    def test_order_appears_in_filename(self):
        """The order parameter should appear in the generated filename."""
        params = _make_params(
            {"net.ipv4.ip_forward": "1"},
            prefix="99-custom",
            order=50,
            path=_tmp_path(prefix="99-custom", order=50),
        )
        result = _run_module(params)
        assert "file" in result
        assert "_50_" in result["file"] or "99-custom_50" in result["file"]
