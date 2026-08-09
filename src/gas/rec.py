import hashlib
import json
import math
import os
import urllib.request
from importlib.resources import as_file
from importlib.resources.abc import Traversable
from pathlib import Path

import numpy as np
import onnxruntime as ort

from .config import OCR_MODEL_CONFIG, OCR_MODEL_REGION, OCR_MODEL_ROOT
from .log import Log

# Target input image height of the model (48px for the current model)
IMAGE_HEIGHT = 48
# Maximum tensor width allowed to feed into the model
MAXIMUM_IMAGE_WIDTH = 640
# Standard input width for short text lines (padded with 0 on the right)
STANDARD_TENSOR_WIDTH = 320
# Width alignment step for extra-wide text
TENSOR_WIDTH_ALIGNMENT = 32
# CTC blank placeholder index (dictionary index 0)
BLANK_INDEX = 0

PathLike = str | Path | Traversable


def _as_path(path: PathLike) -> Path:
    """Convert str / Path / Traversable to a Path."""
    if isinstance(path, Path):
        return path
    if isinstance(path, Traversable):
        # Resources are installed on the filesystem; as_file() yields the
        # underlying path (zipped resources are extracted to a temp file).
        with as_file(path) as file:
            return file
    return Path(path)


def _model_files() -> tuple[Path, Path]:
    """Resolve the model and dict files, downloading them on first use.

    Files are downloaded to ``~/.genshin-artifact-scan/ocr/<config-name>``
    following the active region of the JSON config shipped in assets.
    """
    config_path = _as_path(OCR_MODEL_CONFIG)
    with config_path.open(encoding="utf-8") as f:
        config = json.load(f)

    entries = [config["model"], config["dict"]]
    regions = set().union(*(entry["urls"] for entry in entries))
    # Fall back to the global region when the detected region is not configured
    region = OCR_MODEL_REGION if OCR_MODEL_REGION in regions else "global"
    if region not in regions:
        raise ValueError(
            f"Unknown OCR model region: {region!r}; "
            f"available: {', '.join(sorted(regions))}"
        )

    model_dir = OCR_MODEL_ROOT / config["name"]
    model_target = model_dir / config["model"]["name"]
    dict_target = model_dir / config["dict"]["name"]

    if model_target.is_file() and dict_target.is_file():
        Log.info(f"Loading model from {model_dir}")
    else:
        Log.info(f"Downloading model to {model_dir}")
        _download_files(entries, region, model_dir)
        Log.info(f"Loading model from {model_dir}")

    return model_target, dict_target


def _download_files(entries: list[dict], region: str, model_dir: Path) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        target = model_dir / entry["name"]
        if target.is_file():
            continue
        url = entry["urls"][region]
        Log.info(f"Downloading {entry['name']} from {url}")

        # Download to a temp file, verify the checksum, then atomically
        # rename; an interrupted download only leaves a .part file behind,
        # so the final target is either a complete file or absent.
        part = target.with_suffix(target.suffix + ".part")
        try:
            urllib.request.urlretrieve(url, part)
            expected_sha256 = entry.get("sha256")
            if expected_sha256:
                actual = hashlib.sha256(part.read_bytes()).hexdigest()
                if actual != expected_sha256:
                    raise ValueError(
                        f"Checksum mismatch for {target.name}: "
                        f"expected {expected_sha256}, got {actual}"
                    )
            os.replace(part, target)
        except Exception:
            part.unlink(missing_ok=True)
            raise


class TextRecognizer:
    """Text recognition model running directly on ONNX Runtime.

    The model and dictionary files are downloaded on first use from the
    JSON config shipped in assets to ``~/.genshin-artifact-scan/ocr/<name>``.
    """

    def __init__(self):
        model_path, dict_path = _model_files()
        if not model_path.is_file():
            raise FileNotFoundError(f"OCR model does not exist: {model_path}")
        if not dict_path.is_file():
            raise FileNotFoundError(f"OCR dict does not exist: {dict_path}")

        # Character table: index 0 is blank, a space is appended at the end
        self.characters = _load_characters(dict_path)

        # Prefer DirectML (GPU), fall back to CPU
        self.session = ort.InferenceSession(
            str(model_path),
            providers=[
                "DmlExecutionProvider",
                "CPUExecutionProvider",
            ],
            provider_options=[
                {"device_id": 0},
                {},
            ],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        # Verify the model class count matches the loaded character table
        output_classes = self.session.get_outputs()[0].shape[-1]
        if output_classes not in (None, "?") and output_classes != len(self.characters):
            raise ValueError(
                f"OCR model has {output_classes} classes, but "
                f"{len(self.characters)} characters were loaded"
            )

    def recognize(self, images: list[np.ndarray]) -> list[tuple[str, float]]:
        """Recognize a list of RGB images; returns (text, confidence) in input order."""
        if not images:
            return []

        # Group images by computed tensor width so each batch shares one width
        grouped: dict[int, list[tuple[int, np.ndarray]]] = {}
        for index, image in enumerate(images):
            grouped.setdefault(_tensor_width(image), []).append((index, image))

        results: list[tuple[str, float] | None] = [None] * len(images)
        for tensor_width, entries in grouped.items():
            batch_results = self._recognize_batch(
                [image for _, image in entries], tensor_width
            )
            # Write each group's results back to the original positions
            for (index, _), result in zip(entries, batch_results):
                results[index] = result

        return results  # type: ignore[return-value]

    def _recognize_batch(
        self, images: list[np.ndarray], tensor_width: int
    ) -> list[tuple[str, float]]:
        tensor = _preprocess(images, tensor_width)
        output = self.session.run([self.output_name], {self.input_name: tensor})[0]
        # Output shape (Batch, Timestep, Class), decode each sequence with CTC
        return [_decode_sequence(sequence, self.characters) for sequence in output]


def _tensor_width(image: np.ndarray) -> int:
    """Compute the aligned tensor width from the image aspect ratio."""
    height, width = image.shape[:2]
    required = round(width * IMAGE_HEIGHT / height)
    required = min(max(required, 1), MAXIMUM_IMAGE_WIDTH)
    # Short lines use the standard width (padded to 320); extra-wide lines
    # are rounded up to a multiple of the alignment step
    if required <= STANDARD_TENSOR_WIDTH:
        return STANDARD_TENSOR_WIDTH
    return min(
        math.ceil(required / TENSOR_WIDTH_ALIGNMENT) * TENSOR_WIDTH_ALIGNMENT,
        MAXIMUM_IMAGE_WIDTH,
    )


def _preprocess(images: list[np.ndarray], tensor_width: int) -> np.ndarray:
    """Preprocess images: resize + normalize + arrange as NCHW float32.

    :return: tensor of shape (Batch, 3, IMAGE_HEIGHT, tensor_width)
    """
    batch = np.zeros((len(images), 3, IMAGE_HEIGHT, tensor_width), dtype=np.float32)

    for batch_index, image in enumerate(images):
        height, width = image.shape[:2]
        # Keep the aspect ratio when resizing to height 48; the remaining
        # width in the tensor is padded with 0
        resized_width = min(
            tensor_width,
            max(1, round(width * IMAGE_HEIGHT / height)),
        )
        resized = _resize_bilinear(image, resized_width, IMAGE_HEIGHT)
        # Normalize to [-1.0, 1.0]
        normalized = (resized / 255.0 - 0.5) / 0.5
        # Fill in channel order (B, C, H, W)
        for channel in range(3):
            batch[batch_index, channel, :, :resized_width] = normalized[:, :, channel]

    return batch


def _resize_bilinear(
    image: np.ndarray, target_width: int, target_height: int
) -> np.ndarray:
    """Bilinear resize of an RGB (H, W, 3) image, returning float [0, 255]."""
    height, width = image.shape[:2]

    # Map target pixel centers back to source coordinates (+0.5 aligns
    # pixel centers, -0.5 corrects the coordinate system)
    src_x = (np.arange(target_width) + 0.5) * width / target_width - 0.5
    src_y = (np.arange(target_height) + 0.5) * height / target_height - 0.5
    src_x = np.clip(src_x, 0.0, width - 1)
    src_y = np.clip(src_y, 0.0, height - 1)

    # Neighboring source pixels and interpolation weights
    x0 = np.floor(src_x).astype(np.int32)
    y0 = np.floor(src_y).astype(np.int32)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)

    weight_x = (src_x - x0)[None, :, None]
    weight_y = (src_y - y0)[:, None, None]

    # Interpolate horizontally first, then vertically
    top = image[y0][:, x0] * (1.0 - weight_x) + image[y0][:, x1] * weight_x
    bottom = image[y1][:, x0] * (1.0 - weight_x) + image[y1][:, x1] * weight_x
    return top * (1.0 - weight_y) + bottom * weight_y


def _decode_sequence(sequence: np.ndarray, characters: list[str]) -> tuple[str, float]:
    """CTC greedy decode of a timestep sequence; returns (text, avg confidence).

    At each step the most probable class is taken; blanks are skipped and
    adjacent duplicate characters are merged.
    """
    text = []
    previous_index = -1
    confidence_sum = 0.0
    character_count = 0

    for timestep in sequence:
        best_index = int(np.argmax(timestep))
        if (
            best_index != BLANK_INDEX
            and best_index != previous_index
            and best_index < len(characters)
        ):
            text.append(characters[best_index])
            confidence_sum += _probability_of_best(timestep, best_index)
            character_count += 1
        previous_index = best_index

    confidence = confidence_sum / character_count if character_count else 0.0
    return "".join(text), confidence


def _probability_of_best(values: np.ndarray, best_index: int) -> float:
    """Probability of the best character; handles both probabilities and logits."""
    values = values.astype(np.float64)
    # Directly use the value when the output already looks like a
    # probability distribution (values in [0, 1] and sum close to 1)
    if np.all((values >= 0.0) & (values <= 1.0)):
        total = values.sum()
        if 0.98 <= total <= 1.02:
            return float(values[best_index])

    # Otherwise treat as logits and compute a numerically stable softmax
    maximum = float(values[best_index])
    exponential_sum = np.exp(values - maximum).sum()
    return float(1.0 / exponential_sum)


def _load_characters(dict_path: Path) -> list[str]:
    """Parse the character dictionary from the yml config.

    The dictionary is listed as ``character_dict:`` followed by
    ``  - '<char>'`` lines; index 0 is blank and a space is appended at the end.
    """
    characters = []
    reading_dictionary = False
    for line in dict_path.read_text(encoding="utf-8").splitlines():
        if not reading_dictionary:
            if line.strip() == "character_dict:":
                reading_dictionary = True
            continue
        if not line.startswith("  - "):
            continue
        characters.append(_decode_yaml_scalar(line.removeprefix("  - ")))

    if not characters:
        raise ValueError(f"OCR character dictionary is empty: {dict_path}")
    return [""] + characters + [" "]


def _decode_yaml_scalar(value: str) -> str:
    """Decode a YAML string literal (single quotes escape as '', double quotes
    use JSON escaping)."""
    if len(value) >= 2 and value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    return value
