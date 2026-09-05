"""
Additional tests for icd10-ccsr-mapper security and validation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from cli import _parse_bool, _validate_input_path, _validate_output_path


class TestParseBool:
    def test_true_values(self):
        assert _parse_bool(True) is True
        assert _parse_bool("true") is True
        assert _parse_bool("True") is True
        assert _parse_bool("TRUE") is True
        assert _parse_bool("1") is True
        assert _parse_bool("yes") is True
        assert _parse_bool("YES") is True
        assert _parse_bool("on") is True
        assert _parse_bool("ON") is True
        assert _parse_bool(1) is True
        assert _parse_bool(1.0) is True

    def test_false_values(self):
        assert _parse_bool(False) is False
        assert _parse_bool("false") is False
        assert _parse_bool("False") is False
        assert _parse_bool("FALSE") is False
        assert _parse_bool("0") is False
        assert _parse_bool("no") is False
        assert _parse_bool("NO") is False
        assert _parse_bool("off") is False
        assert _parse_bool("OFF") is False
        assert _parse_bool(0) is False
        assert _parse_bool(0.0) is False
        assert _parse_bool("") is False
        assert _parse_bool(None) is False

    def test_non_empty_string_true(self):
        """Any non-empty, non-recognized string returns False (safe default)."""
        assert _parse_bool("random") is False
        assert _parse_bool("2") is False


class TestValidateInputPath:
    def test_valid_file(self, tmp_path):
        test_file = tmp_path / "test_input.csv"
        test_file.write_text("query,name\ntest,sample\n")
        result = _validate_input_path(str(test_file))
        assert result == test_file.resolve()

    def test_nonexistent_file(self, tmp_path):
        with pytest.raises(Exception, match="does not exist"):
            _validate_input_path(str(tmp_path / "nonexistent.csv"))

    def test_directory_not_file(self, tmp_path):
        with pytest.raises(Exception, match="is not a file"):
            _validate_input_path(str(tmp_path))

    def test_path_traversal_prevented(self):
        with pytest.raises(Exception, match="traversal"):
            _validate_input_path("../etc/passwd")

    def test_absolute_traversal_prevented(self):
        with pytest.raises(Exception, match="traversal"):
            _validate_input_path("/etc/../etc/passwd")


class TestValidateOutputPath:
    def test_valid_csv_output(self, tmp_path):
        result = _validate_output_path(str(tmp_path / "output.csv"))
        assert result == (tmp_path / "output.csv").resolve()

    def test_valid_json_output(self, tmp_path):
        result = _validate_output_path(str(tmp_path / "output.json"))
        assert result == (tmp_path / "output.json").resolve()

    def test_valid_txt_output(self, tmp_path):
        result = _validate_output_path(str(tmp_path / "output.txt"))
        assert result == (tmp_path / "output.txt").resolve()

    def test_invalid_extension(self, tmp_path):
        with pytest.raises(Exception, match="not allowed"):
            _validate_output_path(str(tmp_path / "output.exe"))

    def test_invalid_extension_sh(self, tmp_path):
        with pytest.raises(Exception, match="not allowed"):
            _validate_output_path(str(tmp_path / "script.sh"))

    def test_path_traversal_prevented(self):
        with pytest.raises(Exception, match="traversal"):
            _validate_output_path("../tmp/evil.sh")

    def test_path_traversal_with_dotdot_middle(self):
        with pytest.raises(Exception, match="traversal"):
            _validate_output_path("foo/../../../etc/passwd")
