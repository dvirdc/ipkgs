"""Tests for IpkgsManifest."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from ipkgs.core.manifest import IpkgsManifest
from ipkgs.exceptions import ManifestNotFoundError, ManifestValidationError


def test_round_trip(sample_manifest: IpkgsManifest, tmp_path: Path) -> None:
    path = tmp_path / "ipkgs.json"
    sample_manifest.save(path)
    loaded = IpkgsManifest.load(path)
    assert loaded.name == sample_manifest.name
    assert loaded.version == sample_manifest.version
    assert loaded.dependencies == sample_manifest.dependencies


def test_invalid_name_rejected() -> None:
    with pytest.raises(ValidationError, match="Invalid package name"):
        IpkgsManifest(name="Invalid_Name", version="1.0.0")


def test_invalid_version_rejected() -> None:
    with pytest.raises(ValidationError, match="Invalid version"):
        IpkgsManifest(name="valid-name", version="not-a-version")


def test_name_must_be_lowercase() -> None:
    with pytest.raises(ValidationError):
        IpkgsManifest(name="MyCore", version="1.0.0")


def test_missing_required_fields_raises() -> None:
    with pytest.raises(ValidationError):
        IpkgsManifest.model_validate({})


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ManifestNotFoundError):
        IpkgsManifest.load(tmp_path / "ipkgs.json")


def test_load_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "ipkgs.json"
    path.write_text("not valid json{{{")
    with pytest.raises(ManifestValidationError):
        IpkgsManifest.load(path)


def test_valid_semver_variants() -> None:
    for v in ["0.0.1", "1.0.0", "1.2.3-alpha.1", "2.0.0+build.1"]:
        m = IpkgsManifest(name="my-core", version=v)
        assert m.version == v
