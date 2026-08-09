import os
import tomllib

import tomlkit

from .. import artifact

_SCHEME = "genshin-atool"
_VERSION = 1


class GenshinAToolExporter:
    def load(self, path: str) -> list[artifact.Artifact]:
        if not os.path.isfile(path):
            return []

        with open(path, "rb") as f:
            data = tomllib.load(f)

        format = data.get("format")
        if format is not None and format != _SCHEME:
            raise ValueError(f"Unsupported format: {format!r}")

        version = data.get("version")
        if version is not None and version != _VERSION:
            raise ValueError(f"Unsupported version: {version!r}")

        return artifact.from_dict_list(data.get("artifacts", []))

    @classmethod
    def detect(cls, content: bytes) -> bool:
        try:
            data = tomllib.loads(content.decode("utf-8"))
        except Exception:
            return False
        return isinstance(data, dict) and data.get("format") == _SCHEME

    def dump(self, path: str, artifacts: list[artifact.Artifact]) -> None:
        doc = tomlkit.document()
        doc.add("format", _SCHEME)
        doc.add("version", _VERSION)
        doc.add("artifacts", _dumps_artifacts(artifacts))

        toml_content = tomlkit.dumps(doc)
        toml_content = toml_content.replace("{", "{ ").replace("}", " }")

        with open(path, "w", encoding="utf-8") as f:
            f.write(toml_content)


def _dumps_inline_table(dict_: dict):
    inline_table = tomlkit.inline_table()
    inline_table.update(dict_)
    return inline_table


def _dumps_artifacts(artifacts: list[artifact.Artifact]):
    arr = tomlkit.aot()

    for art in artifacts:
        artifact_dict = artifact.to_dict(art)
        artifact_table = tomlkit.table()
        for name, value in artifact_dict.items():
            if name == "main_attr":
                artifact_table.add(name, _dumps_inline_table(value))
            elif name in ("sub_attrs", "inactive_sub_attrs"):
                sub_attrs_arr = tomlkit.array()
                for sub_attr in value:
                    sub_attrs_arr.add_line(_dumps_inline_table(sub_attr))
                sub_attrs_arr.add_line(indent="")
                artifact_table.add(name, sub_attrs_arr)
            else:
                artifact_table.add(name, value)

        arr.append(artifact_table)

    return arr
