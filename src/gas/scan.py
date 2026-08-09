import os
import re
import time
import tomllib

import pyautogui
import pygetwindow as gw
import win32gui

import cv2
import numpy as np

from . import artifact
from . import config as app_config
from .log import Log
from .rec import TextRecognizer

ARTIFACT_SET_ZH_TO_EN = {}
with app_config.ASSETS.joinpath("artifacts.toml").open("rb") as file:
    artifact_set_en_to_zh = tomllib.load(file)
for k, v in artifact_set_en_to_zh.items():
    ARTIFACT_SET_ZH_TO_EN[v] = k

OCR: TextRecognizer | None = None

INACTIVE_SUB_ATTR_PATTERN = re.compile(
    r"(?:[（(](?:待|未)(?:激(?:活)?)?[）)]?|(?:待|未)激(?:活)?[）)]?)$"
)


def _get_content_rect():
    target_windows = gw.getWindowsWithTitle("原神")
    if not target_windows:
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
    with app_config.ASSETS.joinpath("scan.toml").open("rb") as file:
        scan_config = tomllib.load(file)

    for config in scan_config["resolution"]:
        if config["width"] == w and config["height"] == h:
            break
    else:
        return None

    return config


def _map_artifact_set(name: str):
    if name in ARTIFACT_SET_ZH_TO_EN:
        return artifact.ArtifactSet[ARTIFACT_SET_ZH_TO_EN[name].upper()]
    elif name.find("海染") >= 0:
        return artifact.ArtifactSet.OCEAN_HUED_CLAM

    return artifact.ArtifactSet.UNKNOW


def _map_artifact_pos(name: str):
    match name:
        case "生之花":
            return artifact.ArtifactPiece.FLOWER
        case "死之羽":
            return artifact.ArtifactPiece.PLUME
        case "时之沙":
            return artifact.ArtifactPiece.SANDS
        case "空之杯":
            return artifact.ArtifactPiece.GOBLET
        case "理之冠":
            return artifact.ArtifactPiece.CIRCLET
        case _:
            return None


def _map_artifact_star(name: str):
    star = len(name)
    if star < 4 or star > 5:
        return 0
    return star


_ATTR_KIND_KEYWORDS: list[tuple[str, artifact.AttrKind]] = [
    ("暴击率", artifact.AttrKind.CR),
    ("暴击伤害", artifact.AttrKind.CD),
    ("元素精通", artifact.AttrKind.EM),
    ("元素充能", artifact.AttrKind.ER),
    ("物理", artifact.AttrKind.PHYICAL_DMG),
    ("火元素", artifact.AttrKind.PYRO_DMG),
    ("冰元素", artifact.AttrKind.CRYO_DMG),
    ("雷元素", artifact.AttrKind.ELECTRO_DMG),
    ("水元素", artifact.AttrKind.HYDRO_DMG),
    ("风元素", artifact.AttrKind.ANEMO_DMG),
    ("岩元素", artifact.AttrKind.GEO_DMG),
    ("草元素", artifact.AttrKind.DENDRO_DMG),
    ("治疗", artifact.AttrKind.HEALING),
    ("攻击", artifact.AttrKind.ATK),
    ("生命", artifact.AttrKind.HP),
    ("防御", artifact.AttrKind.DEF),
]

_FLAT_TO_RATE_KINDS = {
    artifact.AttrKind.ATK: artifact.AttrKind.ATK_RATE,
    artifact.AttrKind.HP: artifact.AttrKind.HP_RATE,
    artifact.AttrKind.DEF: artifact.AttrKind.DEF_RATE,
}


def _map_attr(name: str, value: str) -> artifact.Attribute | None:
    # Strip the UI activation marker before converting the numeric value.
    # The caller keeps inactive attributes separate from active sub-attributes.
    value = INACTIVE_SUB_ATTR_PATTERN.sub("", value.strip())

    for keyword, kind in _ATTR_KIND_KEYWORDS:
        if keyword not in name:
            continue
        if value.endswith("%"):
            kind = _FLAT_TO_RATE_KINDS.get(kind, kind)
            return artifact.Attribute(kind, float(value.strip("%")) / 100.0)
        if kind.is_flat:
            cleaned = value.replace(" ", "").replace(",", "").replace(".", "")
            return artifact.Attribute(kind, int(cleaned))
        return artifact.Attribute(kind, float(value.strip("%")) / 100.0)

    return None


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """将十六进制颜色字符串转换为RGB元组 (0-255)"""
    hex_color = hex_color.lstrip("#")  # 去除开头的#
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _rec_artifact(img, det) -> artifact.Artifact | None:
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
    if artifact_defined_pixel == _hex_to_rgb(artifact_defined_color):
        toffset = artifact_defined_height

    l = name_and_subattr[0]
    t = name_and_subattr[1] + toffset
    r = name_and_subattr[2]
    h = (name_and_subattr[3] - name_and_subattr[1]) / 5

    for _ in range(5):
        b = t + h
        tmp_img = img.crop((l, t, r, b))
        ocr_input.append(np.array(tmp_img))
        t = b

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

    i = 0

    while True:
        item = ocr_output[i]

        txt: str = item[0]
        if i <= 4:
            txt = re.sub(
                r"""
                [·,:：;；]  # 删除特定符号
                | \s+       # 删除所有空白字符
                | (?<=\d),(?=\d)  # 删除数字中间的逗号（如 4,780）
                """,
                "",
                txt,
                flags=re.X,
            )
            name_and_value = txt.split("+")
            if len(name_and_value) == 2:
                is_inactive = (
                    INACTIVE_SUB_ATTR_PATTERN.search(name_and_value[1]) is not None
                )
                sub_attr = _map_attr(*name_and_value)
                if sub_attr is None:
                    Log.warning(f"sub attr not found for {txt}")
                elif is_inactive:
                    inactive_sub_attrs.append(sub_attr)
                else:
                    sub_attrs.append(sub_attr)
            elif (i == 3 or i == 4) and len(name_and_value) == 1:
                artifact_set = _map_artifact_set(name_and_value[0])
                if artifact_set == artifact.ArtifactSet.UNKNOW:
                    Log.warning(f"artifact set not found for {name_and_value[0]}")
                else:
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
            if artifact_star == 0:
                Log.warning(f"artifact star not found for {name}")
        elif i <= 9:
            name = txt.strip().replace("+", "")
            artifact_level = int(name)
            if artifact_level < 0 or artifact_level > 20:
                Log.warning(f"artifact level not found for {name}")
                artifact_level = -1
            break

        i += 1

    if (
        artifact_pos is None
        or main_attr is None
        or artifact_level < 0
        or artifact_level > 20
        or artifact_star < 4
    ):
        Log.error(f"illeagal rec artifact {ocr_output}")
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
    if not existing_hashes:
        return False

    artifact.round_attrs(art)
    return artifact.hash_artifact(art) in existing_hashes


def _scan_page(det: dict, existing_hashes: set[str]):
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


def _similar_score_by_hist(img1, img2):
    # 转换为HSV色彩空间
    img1_hsv = cv2.cvtColor(np.array(img1), cv2.COLOR_BGR2HSV)
    img2_hsv = cv2.cvtColor(np.array(img2), cv2.COLOR_BGR2HSV)

    # 计算直方图
    hist1 = cv2.calcHist([img1_hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    hist2 = cv2.calcHist([img2_hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])

    # 归一化并比对
    cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

    return similarity


def _similar_score_by_pixels(img1, img2):
    img1 = np.array(img1)
    img2 = np.array(img2)

    diff = img1 - img2
    score = np.mean(abs(diff) < 0.25)
    return score


_GAP_IMG = None


def _turning_page(det: dict, scroll_clicks: int):
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
            new_similar_ratio_value = _similar_score_by_hist(_GAP_IMG, new_gap_img)
            if new_similar_ratio_value > 0.9:
                break

        time.sleep(0.6)
        new_gap_img = pyautogui.screenshot(region=panel_rec)

        similar_score_value = _similar_score_by_pixels(gap_img, new_gap_img)
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
        new_similar_ratio_value = _similar_score_by_hist(_GAP_IMG, new_gap_img)
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
