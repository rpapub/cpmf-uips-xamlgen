import json
import tomllib
from pathlib import Path
from typing import Any

import typer

from . import generate

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


@app.command()
def main(
    ast: str = typer.Argument(
        ..., help="Input AST document: .json path, .toml path, or inline JSON string"
    ),
    catalogs: list[str] = typer.Option(
        ..., "--catalog", "-c", help="Activity catalog: .json path or inline JSON (repeatable)"
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
    catalog_list = [load_input(c) for c in catalogs]
    policy_path = str(policy_file) if policy_file else None

    envelope = generate(ast_doc, catalog_list, policy_file=policy_path, verbose=verbose)

    out = json.dumps(envelope, indent=2)
    if output:
        output.write_text(out, encoding="utf-8")
    else:
        typer.echo(out)
