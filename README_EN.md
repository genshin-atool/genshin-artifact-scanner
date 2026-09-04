# gas

Genshin Impact artifact scanner.

[中文](README.md) | [English](README_EN.md)

## Installation

```sh
uv sync
```

## Usage

1. Open a console with **administrator privileges** (otherwise you may not be able to control the Genshin Impact window).
2. Make sure the Genshin Impact client window is open and showing the **artifact inventory screen**.
3. The game must run in **windowed mode** (not fullscreen); otherwise the window position cannot be retrieved.
4. The game resolution must be **1920x1080** (the current `assets/scan.toml` only supports this resolution; to support another resolution, add the corresponding config to that file).

```sh
# Scan and save to the default file ./gas.toml (gatool-artifacts format)
uv run gas

# Scan and save to a specified file
uv run gas --file mybag.toml

# Append mode: load the file for dedupe, stop at the first already-known artifact, then merge results back into the same file
uv run gas --file mybag.toml --append

# Specify the GOOD (Genshin Optimizer) JSON format
uv run gas --file good.json --format good

# When --format is not specified, the format is auto-detected from the file content (gatool-artifacts files carry a format field; GOOD files carry their own format marker)
uv run gas --file good.json --append
```

## Supported formats

| Format             | Description                           | Reference                                                                                                                 |
| ------------------ | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `gatool-artifacts` | The tool's own format (TOML), default | No external spec                                                                                                          |
| `good`          | Genshin Optimizer GOOD v3 JSON        | <https://frzyc.github.io/genshin-optimizer>                                                                               |
| `mona`          | Mona artifact JSON                    | <https://github.com/wormtql/genshin_artifact> (consumer)<br><https://github.com/wormtql/yas> (YAS scanner, format source) |
