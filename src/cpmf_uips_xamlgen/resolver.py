"""Catalog resolution: find and load the right activity-catalog for a given sourceId/version."""

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError

from ._config import CatalogSource, Config
from ._version import NuGetVersion, parse_nuget_version


@dataclass(frozen=True)
class ResolvedCatalog:
    data: dict[str, Any]
    source_id: str
    resolved_version: str


class CatalogResolutionError(Exception):
    """Raised when no catalog can be resolved for a given sourceId/version."""


_HTTP_TIMEOUT = 10  # seconds


def resolve_catalog(
    source_id: str,
    requested_version: str,
    config: Config,
    *,
    injected_catalogs: list[dict[str, Any]] | None = None,
) -> ResolvedCatalog:
    """Resolve a catalog for source_id/requested_version.

    Checks injected_catalogs first (exact sourceId+version match).
    Falls back to config.catalog_sources using the configured resolution strategy.
    Raises CatalogResolutionError if nothing resolves.
    """
    # 1. Check injected catalogs (direct --catalog flags); exact match only
    if injected_catalogs:
        for cat in injected_catalogs:
            src = cat.get("source", {})
            if src.get("id") == source_id and src.get("version") == requested_version:
                return ResolvedCatalog(
                    data=cat,
                    source_id=source_id,
                    resolved_version=requested_version,
                )

    # 2. Try each configured source
    target = parse_nuget_version(requested_version)
    strategy = config.resolution.strategy

    for source in config.catalog_sources:
        result = _resolve_from_source(source, source_id, requested_version, target, strategy)
        if result is not None:
            return result

    raise CatalogResolutionError(
        f"Could not resolve catalog for {source_id!r}/{requested_version!r}. "
        f"Strategy: {strategy!r}. Sources checked: {len(config.catalog_sources)}."
    )


def _resolve_from_source(
    source: CatalogSource,
    source_id: str,
    requested_version: str,
    target: NuGetVersion,
    strategy: str,
) -> ResolvedCatalog | None:
    if source.kind == "local":
        return _resolve_local(source, source_id, requested_version, target, strategy)
    if source.kind == "url":
        return _resolve_url(source, source_id, requested_version, target, strategy)
    return None


# ---------------------------------------------------------------------------
# Local resolution
# ---------------------------------------------------------------------------


def _resolve_local(
    source: CatalogSource,
    source_id: str,
    requested_version: str,
    target: NuGetVersion,
    strategy: str,
) -> ResolvedCatalog | None:
    base = Path(source.path) / source_id
    if not base.is_dir():
        return None

    # Always try exact match first
    exact_path = base / requested_version / "activity-catalog.json"
    if exact_path.is_file():
        data: dict[str, Any] = json.loads(exact_path.read_text(encoding="utf-8"))
        return ResolvedCatalog(data=data, source_id=source_id, resolved_version=requested_version)

    if strategy == "exact":
        return None

    # Semver fallback: enumerate available versions
    available = _enumerate_local_versions(base)
    return _pick_best(available, source_id, target, lambda vs: _load_local_catalog(base, vs))


def _enumerate_local_versions(base: Path) -> list[tuple[NuGetVersion, str]]:
    """Return (parsed_version, version_string) pairs for valid version subdirectories."""
    results: list[tuple[NuGetVersion, str]] = []
    for child in base.iterdir():
        if not child.is_dir():
            continue
        if not (child / "activity-catalog.json").is_file():
            continue
        try:
            parsed = parse_nuget_version(child.name)
        except ValueError:
            continue
        results.append((parsed, child.name))
    return results


def _load_local_catalog(base: Path, version_str: str) -> dict[str, Any]:
    path = base / version_str / "activity-catalog.json"
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------


def _resolve_url(
    source: CatalogSource,
    source_id: str,
    requested_version: str,
    target: NuGetVersion,
    strategy: str,
) -> ResolvedCatalog | None:
    index_url = f"{source.path.rstrip('/')}/{source_id}/index.json"
    try:
        versions = _fetch_version_index(index_url)
    except (URLError, OSError, ValueError):
        return None

    # Try exact match first
    if requested_version in versions:
        base_url = source.path.rstrip("/")
        catalog_url = f"{base_url}/{source_id}/{requested_version}/activity-catalog.json"
        try:
            data = _fetch_json(catalog_url)
            return ResolvedCatalog(
                data=data, source_id=source_id, resolved_version=requested_version
            )
        except (URLError, OSError, ValueError):
            pass

    if strategy == "exact":
        return None

    # Semver fallback against the index version list
    available = _parse_version_list(versions)
    return _pick_best(
        available,
        source_id,
        target,
        lambda vs: _fetch_json(
            f"{source.path.rstrip('/')}/{source_id}/{vs}/activity-catalog.json"
        ),
    )


def _fetch_version_index(url: str) -> list[str]:
    """Fetch and parse a catalog source index JSON. Returns the versions list."""
    data = _fetch_json(url)
    versions = data.get("versions")
    if not isinstance(versions, list):
        raise ValueError(f"Index at {url!r} missing 'versions' list.")
    return [str(v) for v in versions]


def _fetch_json(url: str) -> dict[str, Any]:
    """Fetch a URL and parse its body as JSON."""
    with urllib.request.urlopen(url, timeout=_HTTP_TIMEOUT) as response:  # noqa: S310
        body = response.read()
    result: dict[str, Any] = json.loads(body)
    return result


def _parse_version_list(versions: list[str]) -> list[tuple[NuGetVersion, str]]:
    """Parse a list of version strings, silently skipping invalid entries."""
    results: list[tuple[NuGetVersion, str]] = []
    for vs in versions:
        try:
            results.append((parse_nuget_version(vs), vs))
        except ValueError:
            continue
    return results


# ---------------------------------------------------------------------------
# Shared semver selection logic
# ---------------------------------------------------------------------------

from collections.abc import Callable  # noqa: E402  (import after helpers for clarity)


def _pick_best(
    available: list[tuple[NuGetVersion, str]],
    source_id: str,
    target: NuGetVersion,
    loader: Callable[[str], dict[str, Any]],
) -> ResolvedCatalog | None:
    """Select the best available version via semver fallback and load it."""
    if not available:
        return None

    # Patch fallback: same major.minor, highest patch
    patch_candidates = [
        (v, vs) for v, vs in available if v[:2] == target[:2] and v != target
    ]
    if patch_candidates:
        _, best_vs = max(patch_candidates, key=lambda x: x[0])
        return ResolvedCatalog(data=loader(best_vs), source_id=source_id, resolved_version=best_vs)

    # Minor fallback: same major, highest minor+patch
    minor_candidates = [
        (v, vs) for v, vs in available if v[0] == target[0] and v[:2] != target[:2]
    ]
    if minor_candidates:
        _, best_vs = max(minor_candidates, key=lambda x: x[0])
        return ResolvedCatalog(data=loader(best_vs), source_id=source_id, resolved_version=best_vs)

    return None
