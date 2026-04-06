import pytest
from conftest import load_catalog

from cpmf_uips_xamlgen import generate
from cpmf_uips_xamlgen.generator import SUPPORTED_CATALOG_SCHEMA_VERSION


def test_generate_returns_none_stub():
    catalog = load_catalog("UiPath.System.Activities", "25.10.11")
    ast_doc = {
        "expressionLanguage": "VisualBasic",
        "root": {
            "kind": "Activity",
            "activityId": "UiPath.Core.Activities.LogMessage@UiPath.System.Activities/25.10.11",
            "arguments": {"Level": "LogLevel.Info", "Message": '"Hello"'},
        },
    }
    result = generate(ast_doc, [catalog])
    # stub — generation not yet implemented
    assert result is None


def test_generate_rejects_wrong_catalog_version():
    bad_catalog = {"schema": {"id": "activity-catalog", "version": "v0.1"}}
    ast_doc = {"expressionLanguage": "VisualBasic", "root": {"kind": "Sequence", "children": []}}
    with pytest.raises(ValueError, match="Unsupported catalog schema version"):
        generate(ast_doc, [bad_catalog])


def test_supported_version_constant():
    assert SUPPORTED_CATALOG_SCHEMA_VERSION == "v0.2"
