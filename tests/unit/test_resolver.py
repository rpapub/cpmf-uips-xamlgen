"""Unit tests for catalog resolution logic."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from cpmf_uips_xamlgen._config import CatalogSource, Config, ResolutionConfig
from cpmf_uips_xamlgen._version import parse_nuget_version
from cpmf_uips_xamlgen.resolver import (
    CatalogResolutionError,
    ResolvedCatalog,
    _enumerate_local_versions,
    resolve_catalog,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_CATALOG: dict[str, Any] = {
    "schema": {"id": "activity-catalog", "version": "v0.2"},
    "source": {"kind": "nuget-package", "id": "Pkg.A", "version": "1.0.0"},
    "generatedAt": "2026-01-01T00:00:00Z",
    "activities": [],
    "enums": [],
    "namespaceMappings": [],
}


def make_catalog(source_id: str, version: str) -> dict[str, Any]:
    return {
        "schema": {"id": "activity-catalog", "version": "v0.2"},
        "source": {"kind": "nuget-package", "id": source_id, "version": version},
        "generatedAt": "2026-01-01T00:00:00Z",
        "activities": [],
        "enums": [],
        "namespaceMappings": [],
    }


def make_local_source_tree(base: Path, source_id: str, versions: list[str]) -> Path:
    """Create a local catalog source tree under base. Returns the source root."""
    for version in versions:
        vdir = base / source_id / version
        vdir.mkdir(parents=True)
        (vdir / "activity-catalog.json").write_text(
            json.dumps(make_catalog(source_id, version)), encoding="utf-8"
        )
    return base


def local_config(base: Path, strategy: str = "semver") -> Config:
    return Config(
        catalog_sources=[CatalogSource(kind="local", path=str(base))],
        resolution=ResolutionConfig(strategy=strategy),
    )


# ---------------------------------------------------------------------------
# parse_nuget_version tests (covered here for locality)
# ---------------------------------------------------------------------------


def test_parse_nuget_version_valid() -> None:
    assert parse_nuget_version("25.10.11") == (25, 10, 11)


def test_parse_nuget_version_invalid() -> None:
    with pytest.raises(ValueError):
        parse_nuget_version("not-a-version")


def test_parse_nuget_version_four_segments() -> None:
    assert parse_nuget_version("1.2.3.4") == (1, 2, 3, 4)


# ---------------------------------------------------------------------------
# Injected catalog tests
# ---------------------------------------------------------------------------


def test_resolve_exact_match_from_injected() -> None:
    cat = make_catalog("Pkg.A", "1.0.0")
    cfg = Config()
    result = resolve_catalog("Pkg.A", "1.0.0", cfg, injected_catalogs=[cat])
    assert isinstance(result, ResolvedCatalog)
    assert result.resolved_version == "1.0.0"
    assert result.source_id == "Pkg.A"
    assert result.data is cat


def test_injected_takes_precedence_over_local_source(tmp_path: Path) -> None:
    make_local_source_tree(tmp_path, "Pkg.A", ["1.0.0"])
    injected = make_catalog("Pkg.A", "1.0.0")
    injected["_marker"] = "injected"  # type: ignore[assignment]
    cfg = local_config(tmp_path)
    result = resolve_catalog("Pkg.A", "1.0.0", cfg, injected_catalogs=[injected])
    assert result.data.get("_marker") == "injected"


# ---------------------------------------------------------------------------
# Local resolution tests
# ---------------------------------------------------------------------------


def test_resolve_exact_match_local(tmp_path: Path) -> None:
    make_local_source_tree(tmp_path, "Pkg.A", ["25.10.11"])
    cfg = local_config(tmp_path)
    result = resolve_catalog("Pkg.A", "25.10.11", cfg)
    assert result.resolved_version == "25.10.11"


def test_resolve_patch_fallback(tmp_path: Path) -> None:
    make_local_source_tree(tmp_path, "Pkg.A", ["25.10.9", "25.10.12"])
    cfg = local_config(tmp_path, strategy="semver")
    result = resolve_catalog("Pkg.A", "25.10.11", cfg)
    assert result.resolved_version == "25.10.12"


def test_resolve_minor_fallback(tmp_path: Path) -> None:
    make_local_source_tree(tmp_path, "Pkg.A", ["25.9.5", "25.11.0"])
    cfg = local_config(tmp_path, strategy="semver")
    # requesting 25.10.0 — no 25.10.*, minor fallback picks latest 25.*
    result = resolve_catalog("Pkg.A", "25.10.0", cfg)
    assert result.resolved_version == "25.11.0"


def test_resolve_no_match_raises(tmp_path: Path) -> None:
    make_local_source_tree(tmp_path, "Pkg.A", ["24.1.0"])
    cfg = local_config(tmp_path, strategy="semver")
    with pytest.raises(CatalogResolutionError, match="Pkg.A"):
        resolve_catalog("Pkg.A", "25.10.0", cfg)


def test_exact_strategy_skips_fallback(tmp_path: Path) -> None:
    make_local_source_tree(tmp_path, "Pkg.A", ["25.10.12"])
    cfg = local_config(tmp_path, strategy="exact")
    with pytest.raises(CatalogResolutionError):
        resolve_catalog("Pkg.A", "25.10.11", cfg)


# ---------------------------------------------------------------------------
# _enumerate_local_versions tests
# ---------------------------------------------------------------------------


def test_enumerate_skips_dirs_without_catalog_json(tmp_path: Path) -> None:
    (tmp_path / "25.10.11").mkdir()
    # No activity-catalog.json inside
    result = _enumerate_local_versions(tmp_path)
    assert result == []


def test_enumerate_skips_non_version_dirs(tmp_path: Path) -> None:
    bad = tmp_path / "__pycache__"
    bad.mkdir()
    (bad / "activity-catalog.json").write_text("{}", encoding="utf-8")
    result = _enumerate_local_versions(tmp_path)
    assert result == []


# ---------------------------------------------------------------------------
# URL resolution tests
# ---------------------------------------------------------------------------


def _mock_urlopen(responses: dict[str, Any]) -> Any:
    """Return a context manager mock for urllib.request.urlopen.

    responses: mapping of URL -> dict to return as JSON body.
    """

    def side_effect(url: str, timeout: int = 10) -> Any:
        if url not in responses:
            from urllib.error import URLError

            raise URLError(f"404 Not Found: {url}")
        body = json.dumps(responses[url]).encode()
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read = MagicMock(return_value=body)
        return mock_resp

    return side_effect


def url_config(base_url: str, strategy: str = "semver") -> Config:
    return Config(
        catalog_sources=[CatalogSource(kind="url", path=base_url)],
        resolution=ResolutionConfig(strategy=strategy),
    )


def test_resolve_url_exact_match() -> None:
    base = "https://example.com/catalogs"
    source_id = "Pkg.A"
    version = "25.10.11"
    index = {"versions": [version]}
    catalog = make_catalog(source_id, version)
    responses = {
        f"{base}/{source_id}/index.json": index,
        f"{base}/{source_id}/{version}/activity-catalog.json": catalog,
    }
    cfg = url_config(base)
    with patch("urllib.request.urlopen", side_effect=_mock_urlopen(responses)):
        result = resolve_catalog(source_id, version, cfg)
    assert result.resolved_version == version
    assert result.source_id == source_id


def test_resolve_url_patch_fallback() -> None:
    base = "https://example.com/catalogs"
    source_id = "Pkg.A"
    available_version = "25.10.12"
    index = {"versions": [available_version]}
    catalog = make_catalog(source_id, available_version)
    responses = {
        f"{base}/{source_id}/index.json": index,
        f"{base}/{source_id}/{available_version}/activity-catalog.json": catalog,
    }
    cfg = url_config(base, strategy="semver")
    with patch("urllib.request.urlopen", side_effect=_mock_urlopen(responses)):
        result = resolve_catalog(source_id, "25.10.11", cfg)
    assert result.resolved_version == available_version


def test_resolve_url_index_fetch_failure() -> None:
    base = "https://example.com/catalogs"
    cfg = url_config(base)
    with patch(
        "urllib.request.urlopen",
        side_effect=_mock_urlopen({}),  # no responses → URLError for all
    ):
        with pytest.raises(CatalogResolutionError):
            resolve_catalog("Pkg.A", "25.10.11", cfg)
