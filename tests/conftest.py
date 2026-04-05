import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "catalogs"


def load_catalog(source_id: str, version: str) -> dict:
    path = FIXTURES / source_id / version / "activity-catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))
