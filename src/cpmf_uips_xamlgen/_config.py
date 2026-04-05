"""Config loading and dataclasses for xamlgen operational configuration."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CatalogSource:
    kind: str  # "local" | "url"
    path: str


@dataclass(frozen=True)
class ResolutionConfig:
    strategy: str = "semver"  # "exact" | "semver"


@dataclass(frozen=True)
class Config:
    catalog_sources: list[CatalogSource] = field(default_factory=list)
    resolution: ResolutionConfig = field(default_factory=ResolutionConfig)


def _default_toml_path() -> Path:
    return Path(__file__).parent / "config" / "default.toml"


def load_config(config_file: Path | None = None) -> Config:
    """Load config, merging caller file over built-in defaults.

    If config_file is None, returns a Config built from built-in defaults only.
    """
    raw = _load_raw_toml(_default_toml_path())
    if config_file is not None:
        caller_raw = _load_raw_toml(config_file)
        raw = _deep_merge(raw, caller_raw)
    return _raw_to_config(raw)


def _load_raw_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge override into base recursively (nested dicts are merged, not replaced)."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _raw_to_config(raw: dict[str, Any]) -> Config:
    sources_raw: list[dict[str, Any]] = raw.get("catalogSources", [])
    sources = [CatalogSource(kind=str(s["kind"]), path=str(s["path"])) for s in sources_raw]
    resolution_raw: dict[str, Any] = raw.get("resolution", {})
    resolution = ResolutionConfig(strategy=str(resolution_raw.get("strategy", "semver")))
    return Config(catalog_sources=sources, resolution=resolution)
