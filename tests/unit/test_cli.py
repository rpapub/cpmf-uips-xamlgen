from typer.testing import CliRunner
from cpmf_uips_xamlgen.cli import app

runner = CliRunner()

MINIMAL_AST = '{"kind":"Activity","activityId":"UiPath.Core.Activities.LogMessage@UiPath.System.Activities/25.10.11","arguments":{}}'
MINIMAL_ENGINE_RESULT = '{"schemaVersion":"1","invocationId":"00000000-0000-0000-0000-000000000001","generatedAt":"2026-01-01T00:00:00Z","sourceKind":"NugetPackage","sourceId":"UiPath.System.Activities","sourceVersion":"25.10.11","status":"Success","package":{},"resolvedDependencies":[],"activities":[],"enums":[],"namespaceMappings":[],"diagnostics":[]}'


def test_cli_exits_without_error():
    result = runner.invoke(app, [MINIMAL_AST, "-e", MINIMAL_ENGINE_RESULT])
    assert result.exit_code == 0
