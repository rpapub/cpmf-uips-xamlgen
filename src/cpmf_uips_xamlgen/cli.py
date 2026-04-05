import json
import tomllib
from pathlib import Path
from typing import Any

import typer

from . import generate
from ._config import load_config
from .resolver import CatalogResolutionError, resolve_catalog

app = typer.Typer()


def load_input(value: str) -> dict[str, Any]:
    """Accept a .json path, .toml path, or inline JSON string."""
    path = Path(value)
    result: dict[str, Any]
    if path.exists():
        if path.suffix == ".toml":
            result = tomllib.loads(path.read_text(encoding="utf-8"))
        else:
            result = json.loads(path.read_text(encoding="utf-8"))
    else:
        result = json.loads(value)
    return result


def _collect_required_sources(ast_doc: dict[str, Any]) -> set[tuple[str, str]]:
    """Walk the AST and return all (sourceId, version) pairs referenced by ActivityNodes."""
    found: set[tuple[str, str]] = set()
    _walk_node(ast_doc.get("root"), found)
    for workflow in ast_doc.get("workflows", []):
        _walk_node(workflow.get("root"), found)
    return found


def _walk_node(node: Any, found: set[tuple[str, str]]) -> None:
    if not isinstance(node, dict):
        return
    kind = node.get("kind")
    if kind == "Activity":
        activity_id = node.get("activityId", "")
        parts = str(activity_id).split("@", 1)
        if len(parts) == 2:
            source_parts = parts[1].split("/", 1)
            if len(source_parts) == 2:
                found.add((source_parts[0], source_parts[1]))
    for child in node.get("children", []):
        _walk_node(child, found)
    for slot in node.get("slots", {}).values():
        _walk_node(slot, found)
    if "root" in node:
        _walk_node(node["root"], found)


def _injected_covers(
    injected: list[dict[str, Any]], source_id: str, version: str
) -> bool:
    for cat in injected:
        src = cat.get("source", {})
        if src.get("id") == source_id and src.get("version") == version:
            return True
    return False


@app.command()
def main(
    ast: str = typer.Argument(
        ..., help="Input AST document: .json path, .toml path, or inline JSON string"
    ),
    catalogs: list[str] = typer.Option(
        [], "--catalog", "-c", help="Activity catalog: .json path or inline JSON (repeatable)"
    ),
    config_file: Path | None = typer.Option(
        None, "--config", help="Config TOML file (catalog sources, resolution strategy)"
    ),
    policy_file: Path | None = typer.Option(
        None, "--policy", help="Policy TOML file (merged over built-in defaults)"
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file (default: stdout)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Include inputProvenance in output envelope"
    ),
) -> None:
    ast_doc = load_input(ast)
    injected: list[dict[str, Any]] = [load_input(c) for c in catalogs]
    cfg = load_config(config_file)

    resolved_list: list[dict[str, Any]] = list(injected)
    required = _collect_required_sources(ast_doc)
    for source_id, version in required:
        if not _injected_covers(injected, source_id, version):
            try:
                rc = resolve_catalog(source_id, version, cfg, injected_catalogs=injected)
                resolved_list.append(rc.data)
            except CatalogResolutionError as exc:
                typer.echo(f"Error: {exc}", err=True)
                raise typer.Exit(code=1) from exc

    policy_path = str(policy_file) if policy_file else None
    envelope = generate(ast_doc, resolved_list, policy_file=policy_path, verbose=verbose)

    out = json.dumps(envelope, indent=2)
    if output:
        output.write_text(out, encoding="utf-8")
    else:
        typer.echo(out)
