import json
import re
import time
import tomllib

import pyautogui
import pygetwindow as gw
import win32gui

import numpy as np

from . import artifact
from . import config as app_config
from .image import hex_to_rgb, lower_quartile_luminance, similar_score_by_hist, similar_score_by_pixels
from .log import Log
from .rec import TextRecognizer
from .text import fuzzy_match, normalize

with app_config.ASSETS.joinpath("artifacts_index.json").open(encoding="utf-8") as file:
    _ARTIFACT_INDEX = json.load(file)

# Normalized name candidates merged from all languages, so whatever the OCR
# recognizes is matched (exact or fuzzy)
_SET_CANDIDATES: dict[str, artifact.ArtifactSet] = {}
_PIECE_CANDIDATES: dict[str, artifact.ArtifactPiece] = {}
for lang_index in _ARTIFACT_INDEX.values():
    for name, enum_name in lang_index["setNames"].items():
        _SET_CANDIDATES[normalize(name)] = artifact.ArtifactSet[enum_name]
    for name, enum_name in lang_index["aliases"].items():
        _SET_CANDIDATES[normalize(name)] = artifact.ArtifactSet[enum_name]
    for name, enum_name in lang_index["pieceNames"].items():
        _PIECE_CANDIDATES[normalize(name)] = artifact.ArtifactPiece[enum_name]

# Short piece labels shown in the artifact detail panel (EN); genshin-db
# only carries the full relic names (e.g. "Goblet of Eonothem")
_PIECE_CANDIDATES.update(
    {
        "flower": artifact.ArtifactPiece.FLOWER,
        "plume": artifact.ArtifactPiece.PLUME,
        "sands": artifact.ArtifactPiece.SANDS,
        "goblet": artifact.ArtifactPiece.GOBLET,
        "circlet": artifact.ArtifactPiece.CIRCLET,
    }
)

with app_config.ASSETS.joinpath("window_titles.json").open(encoding="utf-8") as file:
    _WINDOW_TITLES = json.load(file)["titles"]

OCR: TextRecognizer | None = None

INACTIVE_SUB_ATTR_PATTERN = re.compile(
    r"(?:[（(](?:待|未)(?:激(?:活)?)?[）)]?|(?:待|未)激(?:活)?[）)]?)$"
)


def _get_content_rect():
    """Locate the Genshin window and return its client area.

    :return: (left, top, width, height) in screen coordinates, or None
    """
    for title in _WINDOW_TITLES:
        target_windows = gw.getWindowsWithTitle(title)
        if target_windows:
            break
    else:
        return None

    window = target_windows[0]
    window.show()
    window.activate()
    hwnd = window._hWnd  # 获取窗口句柄

    # 获取客户区尺寸 (width, height)
    client_rect = win32gui.GetClientRect(hwnd)
    client_width = client_rect[2]
    client_height = client_rect[3]

    # 转换客户区左上角到屏幕坐标
    left, top = win32gui.ClientToScreen(hwnd, (0, 0))

    return (left, top, client_width, client_height)


def _load_rec_config(w, h):
    """Load the scan layout config matching the given client size."""
    with app_config.ASSETS.joinpath("scan.toml").open("rb") as file:
        scan_config = tomllib.load(file)

    for config in scan_config["resolution"]:
        if config["width"] == w and config["height"] == h:
            break
    else:
        return None

    return config


def _map_artifact_set(name: str):
    """Map an OCR set name (or piece alias) to an ArtifactSet, or UNKNOW."""
    return fuzzy_match(name, _SET_CANDIDATES) or artifact.ArtifactSet.UNKNOW


def _map_artifact_pos(name: str):
    """Map an OCR piece name to an ArtifactPiece, or None."""
    return fuzzy_match(name, _PIECE_CANDIDATES)


def _map_artifact_star(name: str):
    """Infer rarity from the star glyph count (e.g. ★★★★★ -> 5)."""
    star = len(name)
    if star < 4 or star > 5:
        return 0
    return star


_INACTIVE_MIN_LUMINANCE = 105.0
_INACTIVE_LUMINANCE_DIFFERENCE = 24.0


def _inactive_substat_indexes(images: list) -> set[int]:
    """Detect grayed-out (inactive) substat lines by text luminance.

    The darkest line is the active baseline; a line is inactive when its
    text is clearly brighter than the baseline (mirrors the compose
    ArtifactScanInactiveSubstatDetector).
    """
    if len(images) < 2:
        return set()

    scores = [lower_quartile_luminance(img) for img in images]
    active_baseline = min(scores)

    return {
        index
        for index, score in enumerate(scores)
        if score >= _INACTIVE_MIN_LUMINANCE
        and score - active_baseline >= _INACTIVE_LUMINANCE_DIFFERENCE
    }


_FLAT_TO_RATE_KINDS = {
    artifact.AttrKind.ATK: artifact.AttrKind.ATK_RATE,
    artifact.AttrKind.HP: artifact.AttrKind.HP_RATE,
    artifact.AttrKind.DEF: artifact.AttrKind.DEF_RATE,
}

_SEPARATOR_CHARS = set(".,，。·•⋅．")


def _parse_stat_value(value: str, is_percentage: bool) -> float | None:
    """Extract the numeric value from OCR text (mirrors compose).

    For percentage values, scan backwards: digits are kept and the first
    separator character becomes the decimal point (later ones are dropped).
    For flat values only digits are kept.
    """
    if not value:
        return None

    if is_percentage:
        has_decimal_point = False
        buffer: list[str] = []
        for char in reversed(value):
            if char.isdigit():
                buffer.append(char)
            elif char in _SEPARATOR_CHARS and not has_decimal_point:
                has_decimal_point = True
                buffer.append(".")
        cleaned = "".join(reversed(buffer))
    else:
        cleaned = "".join(char for char in value if char.isdigit())

    if not cleaned:
        return None
    return float(cleaned)

# Multi-language attribute name candidates (normalized name -> base kind)
with app_config.ASSETS.joinpath("attribute_names.json").open(encoding="utf-8") as file:
    _ATTRIBUTE_NAMES = json.load(file)
_ATTR_CANDIDATES: dict[str, artifact.AttrKind] = {
    name: artifact.AttrKind[kind] for name, kind in _ATTRIBUTE_NAMES.items()
}


def _map_attr(name: str, value: str) -> artifact.Attribute | None:
    """Parse an attribute name + value pair into an Attribute.

    The name is matched against the multi-language candidates (exact or
    fuzzy); a percentage (value/name marker or non-flat kind) promotes
    flat kinds to their rate variants.
    """
    # Strip the UI activation marker before converting the numeric value.
    # The caller keeps inactive attributes separate from active sub-attributes.
    value = INACTIVE_SUB_ATTR_PATTERN.sub("", value.strip())

    kind = fuzzy_match(name, _ATTR_CANDIDATES)
    if kind is None:
        return None

    is_percent = "%" in value or "%" in name or not kind.is_flat
    numeric_value = _parse_stat_value(value, is_percent)
    if numeric_value is None:
        return None

    if is_percent:
        kind = _FLAT_TO_RATE_KINDS.get(kind, kind)
        return artifact.Attribute(kind, numeric_value / 100.0)
    return artifact.Attribute(kind, int(numeric_value))


def _rec_artifact(img, det) -> artifact.Artifact | None:
    """Recognize a single artifact card: crop regions, OCR, then parse."""
    artifact_det = det["artifact_info"]

    ocr_input = []

    # 0 - 4 sub attr and name
    name_and_subattr = artifact_det["name_and_subattr"]

    artifact_defined_bound = artifact_det["artifact_defined_with_sanctifying_elixir"]
    artifact_defined_color = artifact_det[
        "artifact_defined_with_sanctifying_elixir_color"
    ]

    toffset = 0
    artifact_defined_height = artifact_defined_bound[3] - artifact_defined_bound[1]
    artifact_defined_py = artifact_defined_bound[3] - int(artifact_defined_height / 2)
    artifact_defined_px = artifact_defined_bound[2] - int(artifact_defined_height / 2)
    artifact_defined_pixel = img.getpixel((artifact_defined_px, artifact_defined_py))
    # Log.debug(artifact_defined_pixel)
    if artifact_defined_pixel == hex_to_rgb(artifact_defined_color):
        toffset = artifact_defined_height

    l = name_and_subattr[0]
    t = name_and_subattr[1] + toffset
    r = name_and_subattr[2]
    h = (name_and_subattr[3] - name_and_subattr[1]) / 5

    sub_attr_images = []
    for _ in range(5):
        b = t + h
        tmp_img = img.crop((l, t, r, b))
        sub_attr_images.append(tmp_img)
        ocr_input.append(np.array(tmp_img))
        t = b

    inactive_substat_indexes = _inactive_substat_indexes(sub_attr_images)

    # 5 main attr
    main_attr = artifact_det["main_attr"]
    tmp_img = img.crop(main_attr)
    ocr_input.append(np.array(tmp_img))

    # 6 main attr value
    main_attr_value = artifact_det["main_attr_value"]
    tmp_img = img.crop(main_attr_value)
    ocr_input.append(np.array(tmp_img))

    # 7 pos
    pos = artifact_det["pos"]
    tmp_img = img.crop(pos)
    ocr_input.append(np.array(tmp_img))

    # 8 star
    star = artifact_det["star"]
    tmp_img = img.crop(star)
    ocr_input.append(np.array(tmp_img))

    # 9 level
    level = artifact_det["level"]
    if toffset != 0:
        level = (level[0], level[1] + toffset, level[2], level[3] + toffset)
    tmp_img = img.crop(level)
    ocr_input.append(np.array(tmp_img))

    # 10 item name (set-specific piece name, for set reverse-derivation)
    item_name = artifact_det["item_name"]
    tmp_img = img.crop(item_name)
    ocr_input.append(np.array(tmp_img))

    global OCR
    if OCR is None:
        OCR = TextRecognizer()

    ocr_output = OCR.recognize(ocr_input)
    # Log.debug(ocr_output)

    artifact_set = artifact.ArtifactSet.UNKNOW
    artifact_pos = None
    artifact_star = 0
    artifact_level = -1
    main_attr = None
    sub_attrs = []
    inactive_sub_attrs = []
    set_name_text = None

    i = 0

    while True:
        item = ocr_output[i]

        txt: str = item[0]
        if i <= 4:
            name_and_value = txt.split("+")
            if len(name_and_value) == 2:
                # Inactive (grayed-out) substats are detected by text
                # luminance; the zh marker in the text is kept as a fallback
                is_inactive = (
                    i in inactive_substat_indexes
                    or INACTIVE_SUB_ATTR_PATTERN.search(name_and_value[1])
                    is not None
                )
                sub_attr = _map_attr(*name_and_value)
                if sub_attr is None:
                    Log.warning(f"sub attr not found for {txt}")
                elif is_inactive:
                    inactive_sub_attrs.append(sub_attr)
                else:
                    sub_attrs.append(sub_attr)
            elif (i == 3 or i == 4) and len(name_and_value) == 1:
                set_name_text = name_and_value[0]
                artifact_set = _map_artifact_set(set_name_text)
                if artifact_set != artifact.ArtifactSet.UNKNOW:
                    i = 5
                    continue
        elif i <= 5:
            name = txt.strip()
            value = ocr_output[i + 1][0].strip()
            main_attr = _map_attr(name, value)
            if main_attr is None:
                Log.warning(f"main attr not found for {name} {value}")
                break
            i = 7
            continue
        elif i <= 7:
            name = txt.strip()
            artifact_pos = _map_artifact_pos(name)
            if artifact_pos is None:
                Log.warning(f"artifact pos not found for {name}")
        elif i <= 8:
            name = txt.strip()
            artifact_star = _map_artifact_star(name)
            if artifact_star < 5:
                break
        elif i <= 9:
            name = txt.strip()
            level_value = _parse_stat_value(name, False)
            artifact_level = int(level_value) if level_value is not None else -1
            if artifact_level < 0 or artifact_level > 20:
                Log.warning(f"artifact level not found for {name}")
                artifact_level = -1
            break

        i += 1

    if artifact_set == artifact.ArtifactSet.UNKNOW:
        # The set name may be obscured (e.g. "(unactivated)"); derive the
        # set from the item name via aliases, like compose
        item_name_text = ocr_output[10][0].strip()
        set_from_item = fuzzy_match(item_name_text, _SET_CANDIDATES)
        if set_from_item is not None:
            artifact_set = set_from_item

    # Only log when the set could not be resolved at all
    if artifact_set == artifact.ArtifactSet.UNKNOW and (
        set_name_text or item_name_text
    ):
        Log.warning(
            f"artifact set not found for set name {set_name_text!r} "
            f"item name {item_name_text!r}"
        )

    if (
        artifact_pos is None
        or main_attr is None
        or artifact_level < 0
        or artifact_level > 20
        or artifact_star < 4
    ):
        Log.error(f"illegal rec artifact {ocr_output}")
        return None

    art = artifact.Artifact(
        set=artifact_set,
        piece=artifact_pos,
        rarity=artifact_star,
        level=artifact_level,
        main_attr=main_attr,  # type: ignore
        sub_attrs=sub_attrs,
        inactive_sub_attrs=inactive_sub_attrs,
    )

    return art


def _is_existing_artifact(
    art: artifact.Artifact,
    existing_hashes: set[str],
) -> bool:
    """Round the artifact attrs and check its hash against existing ones."""
    if not existing_hashes:
        return False

    artifact.round_attrs(art)
    return artifact.hash_artifact(art) in existing_hashes


def _scan_page(det: dict, existing_hashes: set[str]):
    """Scan one page: click each card, OCR it, stop on a known artifact.

    :return: (artifacts, existing_found), or None when aborted by mouse
    """
    row = det["panel"]["row"]
    col = det["panel"]["col"]

    panel_left, panel_top, panel_right, panel_bottom = det["panel"]["bound"]
    card_width = (panel_right - panel_left) / col
    card_height = (panel_bottom - panel_top) / row

    artifact_info_rect = det["artifact_info"]["content"]
    artifact_info_rect = (
        artifact_info_rect[0],
        artifact_info_rect[1],
        artifact_info_rect[2] - artifact_info_rect[0],
        artifact_info_rect[3] - artifact_info_rect[1],
    )

    artifacts: list[artifact.Artifact] = []
    positions = [
        (
            panel_left + j * card_width + card_width * 0.5,
            panel_top + i * card_height + card_height * 0.5,
        )
        for i in range(row)
        for j in range(col)
    ]

    pyautogui.click(x=positions[0][0], y=positions[0][1], _pause=False)
    time.sleep(0.05)

    for index, position in enumerate(positions):
        img = pyautogui.screenshot(region=artifact_info_rect)

        next_index = index + 1
        if next_index < len(positions):
            expected_position = positions[next_index]
            pyautogui.click(
                x=expected_position[0],
                y=expected_position[1],
                _pause=False,
            )
        else:
            expected_position = position

        art = _rec_artifact(img, det)
        if art is not None:
            if _is_existing_artifact(art, existing_hashes):
                Log.info("existing artifact found, stop scanning")
                return artifacts, True
            artifacts.append(art)

        current_position = pyautogui.position()
        if (
            abs(current_position.x - expected_position[0]) > 10
            or abs(current_position.y - expected_position[1]) > 10
        ):
            Log.info("mouse position is moved, stop scanning page")
            return None

    return artifacts, False


_GAP_IMG = None


def _turning_page(det: dict, scroll_clicks: int):
    """Scroll to the next page; returns the scroll clicks used, 0 when done."""
    row = det["panel"]["row"]
    gap_row = det["panel"]["gap_row"]
    bound = det["panel"]["bound"]

    clickx = bound[0] + (bound[2] - bound[0]) / 2
    clicky = bound[1] + (bound[3] - bound[1]) / 2

    global _GAP_IMG
    gap_rec = (
        bound[0],
        bound[1],
        int(bound[2] - bound[0]),
        gap_row,
    )

    if scroll_clicks != 0:
        panel_rec = (
            bound[0] + 2 * gap_row,
            bound[1],
            bound[2] - bound[0],
            bound[3] - bound[1],
        )

        pyautogui.moveTo(x=clickx, y=clicky)
        gap_img = pyautogui.screenshot(region=panel_rec)
        for _ in range(0, scroll_clicks + 5, -1):
            pyautogui.scroll(clicks=scroll_clicks, _pause=False)
            current_position = pyautogui.position()
            if (
                abs(current_position.x - clickx) > 10
                or abs(current_position.y - clicky) > 10
            ):
                Log.info("mouse position is moved, stop turning page")
                return 0

        for _ in range(0, 5):
            pyautogui.scroll(clicks=scroll_clicks, _pause=False)
            time.sleep(0.05)
            new_gap_img = pyautogui.screenshot(region=gap_rec)
            new_similar_ratio_value = similar_score_by_hist(_GAP_IMG, new_gap_img)
            if new_similar_ratio_value > 0.9:
                break

        time.sleep(0.6)
        new_gap_img = pyautogui.screenshot(region=panel_rec)

        similar_score_value = similar_score_by_pixels(gap_img, new_gap_img)
        if similar_score_value > 0.9:
            Log.info("scolled to end")
            return 0
        else:
            return scroll_clicks

    clicks = 0
    row_count = 0
    similar_ratio_value = 0
    if _GAP_IMG is None:
        _GAP_IMG = pyautogui.screenshot(region=gap_rec)

    while True:
        pyautogui.moveTo(x=clickx, y=clicky)
        pyautogui.scroll(clicks=-1)
        time.sleep(0.05)
        clicks = clicks - 1

        new_gap_img = pyautogui.screenshot(region=gap_rec)
        new_similar_ratio_value = similar_score_by_hist(_GAP_IMG, new_gap_img)
        delta = new_similar_ratio_value - similar_ratio_value
        Log.debug(f"row delta:{delta} similar_ratio_value: {new_similar_ratio_value}")
        if delta > 0.3 and new_similar_ratio_value > 0.75:
            row_count += 1
            Log.info(f"scolled row {row_count}")
            if row_count >= row:
                break
        elif abs(delta) < 0.0001:
            Log.info("scolled to end")
            return 0

        similar_ratio_value = new_similar_ratio_value

        current_position = pyautogui.position()
        if (
            abs(current_position.x - clickx) > 10
            or abs(current_position.y - clicky) > 10
        ):
            Log.info("mouse position is moved, stop turning page")
            return 0

    return clicks


def _scan_panel(det: dict, existing_hashes: set[str]):
    """Scan the whole panel, turning pages until done or a known artifact."""
    scroll_clicks = 0
    artifacts = []

    while True:
        page_result = _scan_page(det, existing_hashes)
        if page_result is None:
            break

        page_artifacts, existing_found = page_result
        artifacts.extend(page_artifacts)
        if existing_found or not page_artifacts:
            break

        Log.debug(f"scroll_clicks: {scroll_clicks}")
        scroll_clicks = _turning_page(det, scroll_clicks)
        if scroll_clicks == 0:
            break

    return artifacts


def _preresolve_config(det_config: dict, window_rect: tuple[int, int, int, int]):
    """Shift layout coordinates from window-relative to screen coordinates."""
    det_panel = det_config["panel"]["bound"]

    det_config["panel"]["bound"] = (
        det_panel[0] + window_rect[0],
        det_panel[1] + window_rect[1],
        det_panel[2] + window_rect[0],
        det_panel[3] + window_rect[1],
    )

    det_artifact_info = det_config["artifact_info"]
    l, t, r, b = det_artifact_info["content"]
    det_artifact_info["content"] = (
        l + window_rect[0],
        t + window_rect[1],
        r + window_rect[0],
        b + window_rect[1],
    )

    for k, v in det_artifact_info.items():
        if k == "content" or k == "artifact_defined_with_sanctifying_elixir_color":
            continue
        det_artifact_info[k] = (
            v[0] - l,
            v[1] - t,
            v[2] - l,
            v[3] - t,
        )


def start(existing_hashes: set[str] | None = None):
    """Scan the artifact inventory from the game window.

    :param existing_hashes: hashes to dedupe against; scanning stops at the
        first already-known artifact
    :return: the scanned artifacts, or None on failure
    """
    window_rect = _get_content_rect()
    if window_rect is None:
        Log.error("No genshin window found")
        return

    det_config = _load_rec_config(window_rect[2], window_rect[3])
    if det_config is None:
        Log.error("No resolution config found")
        return

    time.sleep(1)
    _preresolve_config(det_config, window_rect)
    artifacts = _scan_panel(det_config, existing_hashes or set())
    return artifacts


if __name__ == "__main__":
    start()
