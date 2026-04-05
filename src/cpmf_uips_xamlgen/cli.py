import json
import tomllib
import typer
from pathlib import Path

from . import generate

app = typer.Typer()


def load_input(value: str) -> dict:
    """Accept a .json path, .toml path, or inline JSON string."""
    path = Path(value)
    if path.exists():
        if path.suffix == ".toml":
            return tomllib.loads(path.read_text(encoding="utf-8"))
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


@app.command()
def main(
    ast: str = typer.Argument(..., help="Input AST: .json path, .toml path, or inline JSON string"),
    engine_results: list[str] = typer.Option(..., "--engine-result", "-e", help="Engine-result: .json path or inline JSON (repeatable)"),
    policy_file: Path | None = typer.Option(None, "--policy", help="Policy TOML file (merged over built-in defaults)"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file (default: stdout)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Include inputProvenance in output envelope"),
):
    ast_data = load_input(ast)
    results = [load_input(r) for r in engine_results]
    policy_path = str(policy_file) if policy_file else None

    envelope = generate(ast_data, results, policy_file=policy_path, verbose=verbose)

    out = json.dumps(envelope, indent=2)
    if output:
        output.write_text(out, encoding="utf-8")
    else:
        typer.echo(out)
