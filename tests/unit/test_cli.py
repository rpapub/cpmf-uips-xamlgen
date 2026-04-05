import json

from typer.testing import CliRunner

from cpmf_uips_xamlgen.cli import app

runner = CliRunner()

MINIMAL_AST = json.dumps({
    "expressionLanguage": "VisualBasic",
    "root": {
        "kind": "Activity",
        "activityId": "UiPath.Core.Activities.LogMessage@UiPath.System.Activities/25.10.11",
        "arguments": {},
    },
})
MINIMAL_CATALOG = json.dumps({
    "schema": {"id": "activity-catalog", "version": "v0.2"},
    "source": {
        "kind": "nuget-package",
        "id": "UiPath.System.Activities",
        "version": "25.10.11",
        "feedUrl": None,
        "authors": None,
        "projectUrl": None,
        "description": None,
        "license": None,
        "tags": None,
        "packageTypes": [],
    },
    "generatedAt": "2026-01-01T00:00:00Z",
    "activities": [],
    "enums": [],
    "namespaceMappings": [],
})


def test_cli_exits_without_error():
    result = runner.invoke(app, [MINIMAL_AST, "-c", MINIMAL_CATALOG])
    assert result.exit_code == 0


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--catalog" in result.output
