import json
from datetime import UTC, datetime
from pathlib import Path

from app.lineage import append_lineage, build_lineage


def test_lineage_record_is_append_only_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "lineage.jsonl"
    record = build_lineage(
        dataset="climate_daily",
        source="open-meteo",
        source_version="v1",
        transform="normalize-climate-v1",
        destination="sqlite://climate_daily",
        collected_at=datetime(2026, 8, 7, tzinfo=UTC),
    )
    append_lineage(path, record)
    append_lineage(path, record)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["dataset"] == "climate_daily"
    assert rows[0]["source"] == "open-meteo"
    assert rows[0]["collected_at"].startswith("2026-08-07T00:00:00")
