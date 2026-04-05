from conftest import load_engine_result
from cpmf_uips_xamlgen import generate


def test_generate_returns_none_stub():
    engine_result = load_engine_result("UiPath.System.Activities", "25.10.11")
    ast = {
        "kind": "Activity",
        "activityId": "UiPath.Core.Activities.LogMessage@UiPath.System.Activities/25.10.11",
        "arguments": {"Level": "Info", "Message": '"Hello"'},
    }
    result = generate(ast, [engine_result])
    # stub — not yet implemented
    assert result is None
