from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path


@dataclass(frozen=True)
class LineageRecord:
    dataset: str
    source: str
    source_version: str
    transform: str
    destination: str
    collected_at: str


def build_lineage(
    *,
    dataset: str,
    source: str,
    source_version: str,
    transform: str,
    destination: str,
    collected_at: datetime | None = None,
) -> LineageRecord:
    timestamp = (collected_at or datetime.now(UTC)).astimezone(UTC).isoformat()
    return LineageRecord(
        dataset=dataset,
        source=source,
        source_version=source_version,
        transform=transform,
        destination=destination,
        collected_at=timestamp,
    )


def append_lineage(path: Path, record: LineageRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")
