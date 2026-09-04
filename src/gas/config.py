import ctypes
from importlib import resources
from pathlib import Path

ASSETS = resources.files(__package__).joinpath("assets")

DEFAULT_FILE = "gas.toml"
DEFAULT_FORMAT = "gatool-artifacts"

# OCR model download config (addresses) shipped with the package
OCR_MODEL_CONFIG = ASSETS.joinpath("model.json")
# Download root of OCR models, keyed by the config name
OCR_MODEL_ROOT = Path.home() / ".genshin-artifact-scan" / "ocr"


def _detect_region() -> str:
    """Detect the download region from the user locale (e.g. zh-CN, en-US)."""
    try:
        buffer = ctypes.create_unicode_buffer(85)  # LOCALE_NAME_MAX_LENGTH
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, 85):
            return buffer.value or "global"
    except Exception:
        pass
    return "global"


# Active download region, detected from the PC locale
OCR_MODEL_REGION = _detect_region()
