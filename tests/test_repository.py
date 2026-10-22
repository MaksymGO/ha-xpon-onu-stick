"""Catch missing repository licenses before the remote HACS validation runs."""

import pytest

from tools.validate_repository import ROOT, validate_repository


def test_repository_passes_local_validation():
    validate_repository(ROOT)


@pytest.mark.parametrize("license_text", [None, "", " \n\t"])
def test_missing_or_empty_license_fails_validation(tmp_path, license_text):
    if license_text is not None:
        (tmp_path / "LICENSE").write_text(license_text)
    with pytest.raises(ValueError, match="HACS requires a nonempty LICENSE file"):
        validate_repository(tmp_path)
