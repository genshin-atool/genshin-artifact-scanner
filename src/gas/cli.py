import argparse
import os

from . import artifact
from . import config
from . import scan
from .exporters import EXPORTERS, detect_format, exporter_for
from .log import Log


def main():
    parser = argparse.ArgumentParser(
        prog="gas",
        description="Scan the genshin artifact inventory from the game window.",
    )
    parser.add_argument(
        "--file",
        type=str,
        help=f"Artifact file (default: ./{config.DEFAULT_FILE}).",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=list(EXPORTERS),
        help=f"File format (default: {config.DEFAULT_FORMAT}).",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append mode: dedupe against existing artifacts, stop at the first known one.",
    )
    args = parser.parse_args()

    try:
        _run(args)
    except (ValueError, FileNotFoundError) as e:
        Log.error(e)


def _run(args: argparse.Namespace) -> None:
    file_path = args.file or config.DEFAULT_FILE

    if args.format is not None:
        format = args.format
        exporter = exporter_for(format)
        if os.path.isfile(file_path):
            try:
                actual_format = detect_format(file_path)
            except ValueError as e:
                Log.warning(f"{e}; proceeding with --format {format}")
                actual_format = None
            if actual_format is not None and actual_format != format:
                Log.error(
                    f"Format mismatch: {file_path} is {actual_format}, but --format {format} was specified; use --file to point to a different file"
                )
                return
    else:
        format = (
            detect_format(file_path)
            if os.path.isfile(file_path)
            else config.DEFAULT_FORMAT
        )
        exporter = exporter_for(format)

    existing_artifacts = exporter.load(file_path) if args.append else []
    existing_hashes = (
        artifact.hash_artifacts(existing_artifacts) if args.append else set()
    )

    artifacts = scan.start(existing_hashes)
    if artifacts is None:
        Log.error("No artifacts found")
        return

    for art in artifacts:
        artifact.round_stats(art)

    merged = artifacts + existing_artifacts if args.append else artifacts
    exporter.dump(file_path, merged)
    Log.info(f"Saved to {os.path.abspath(file_path)}")


if __name__ == "__main__":
    main()
