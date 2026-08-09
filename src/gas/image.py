"""Generic image processing helpers."""

import cv2
import numpy as np


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color string to an RGB tuple (0-255)."""
    hex_color = hex_color.lstrip("#")
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def similar_score_by_hist(img1, img2) -> float:
    """HSV histogram similarity (correlation), for detecting layout changes."""
    img1_hsv = cv2.cvtColor(np.array(img1), cv2.COLOR_BGR2HSV)
    img2_hsv = cv2.cvtColor(np.array(img2), cv2.COLOR_BGR2HSV)

    hist1 = cv2.calcHist([img1_hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    hist2 = cv2.calcHist([img2_hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])

    cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)


def similar_score_by_pixels(img1, img2) -> float:
    """Fraction of pixels that are nearly identical."""
    diff = np.array(img1) - np.array(img2)
    return np.mean(abs(diff) < 0.25)


def lower_quartile_luminance(img) -> float:
    """Average BT.709 luminance of the darkest 5% pixels (text strokes)."""
    arr = np.array(img).astype(np.float64)
    luminance = (
        arr[:, :, 0] * 2126 + arr[:, :, 1] * 7152 + arr[:, :, 2] * 722
    ) / 10_000
    flat = luminance.ravel()
    if flat.size == 0:
        return 255.0
    flat.sort()
    sample_count = max(flat.size // 20, 1)
    return float(flat[:sample_count].mean())
