import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "engine-results"


def load_engine_result(source_id: str, version: str) -> dict:
    path = FIXTURES / source_id / version / "engine-result.json"
    return json.loads(path.read_text(encoding="utf-8"))
