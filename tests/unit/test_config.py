"""Unit tests for config loading."""

from pathlib import Path

from cpmf_uips_xamlgen._config import Config, load_config


def test_load_config_defaults() -> None:
    cfg = load_config(None)
    assert isinstance(cfg, Config)
    assert cfg.catalog_sources == []
    assert cfg.resolution.strategy == "semver"


def test_load_config_merges_local_source(tmp_path: Path) -> None:
    toml = tmp_path / "my-config.toml"
    toml.write_text(
        '[[catalogSources]]\nkind = "local"\npath = "/data/catalogs"\n',
        encoding="utf-8",
    )
    cfg = load_config(toml)
    assert len(cfg.catalog_sources) == 1
    assert cfg.catalog_sources[0].kind == "local"
    assert cfg.catalog_sources[0].path == "/data/catalogs"
    assert cfg.resolution.strategy == "semver"  # default preserved


def test_load_config_strategy_override(tmp_path: Path) -> None:
    toml = tmp_path / "my-config.toml"
    toml.write_text('[resolution]\nstrategy = "exact"\n', encoding="utf-8")
    cfg = load_config(toml)
    assert cfg.resolution.strategy == "exact"
    assert cfg.catalog_sources == []  # default preserved
