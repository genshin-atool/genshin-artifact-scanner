import os
from typing import Protocol

from .. import artifact
from ..config import DEFAULT_FORMAT
from .genshin_atool import GenshinAToolExporter
from .good import GoodExporter


class Exporter(Protocol):
    """Format adapter between Artifact objects and a file."""

    def load(self, path: str) -> list[artifact.Artifact]:
        ...

    def dump(self, path: str, artifacts: list[artifact.Artifact]) -> None:
        ...

    def detect(self, content: bytes) -> bool:
        ...


EXPORTERS: dict[str, Exporter] = {
    DEFAULT_FORMAT: GenshinAToolExporter(),
    "good": GoodExporter(),
}


def exporter_for(format: str) -> Exporter:
    try:
        return EXPORTERS[format]
    except KeyError:
        raise ValueError(f"Unsupported export format: {format!r}") from None


def detect_format(path: str) -> str:
    """Detect the format name of an existing file from its content."""
    if not os.path.isfile(path):
        raise ValueError(f"File not found: {path}")

    with open(path, "rb") as f:
        content = f.read()

    for name, exporter in EXPORTERS.items():
        if exporter.detect(content):
            return name

    raise ValueError(f"Cannot detect format of {path!r}; specify --format")
