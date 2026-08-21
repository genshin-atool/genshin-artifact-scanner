"""Shared game data for deriving main stat values from rarity and level."""

import math

from .. import artifact

SUB_STAT_KINDS = {
    artifact.StatKind.HP,
    artifact.StatKind.HP_RATE,
    artifact.StatKind.ATK,
    artifact.StatKind.ATK_RATE,
    artifact.StatKind.DEF,
    artifact.StatKind.DEF_RATE,
    artifact.StatKind.EM,
    artifact.StatKind.ER,
    artifact.StatKind.CR,
    artifact.StatKind.CD,
}

MAIN_STAT_KINDS = {
    artifact.ArtifactPiece.FLOWER: {artifact.StatKind.HP},
    artifact.ArtifactPiece.PLUME: {artifact.StatKind.ATK},
    artifact.ArtifactPiece.SANDS: {
        artifact.StatKind.HP_RATE,
        artifact.StatKind.ATK_RATE,
        artifact.StatKind.DEF_RATE,
        artifact.StatKind.EM,
        artifact.StatKind.ER,
    },
    artifact.ArtifactPiece.GOBLET: {
        artifact.StatKind.HP_RATE,
        artifact.StatKind.ATK_RATE,
        artifact.StatKind.DEF_RATE,
        artifact.StatKind.EM,
        artifact.StatKind.PHYICAL_DMG,
        artifact.StatKind.ANEMO_DMG,
        artifact.StatKind.GEO_DMG,
        artifact.StatKind.ELECTRO_DMG,
        artifact.StatKind.DENDRO_DMG,
        artifact.StatKind.HYDRO_DMG,
        artifact.StatKind.PYRO_DMG,
        artifact.StatKind.CRYO_DMG,
    },
    artifact.ArtifactPiece.CIRCLET: {
        artifact.StatKind.HP_RATE,
        artifact.StatKind.ATK_RATE,
        artifact.StatKind.DEF_RATE,
        artifact.StatKind.EM,
        artifact.StatKind.CR,
        artifact.StatKind.CD,
        artifact.StatKind.HEALING,
    },
}

# Main stat value at level 0 and at max level (start, end), per rarity.
MAIN_STAT_RANGES = {
    (4, artifact.StatKind.HP): (645.0, 3_571.0),
    (4, artifact.StatKind.ATK): (42.0, 232.0),
    (4, artifact.StatKind.HP_RATE): (0.063, 0.348),
    (4, artifact.StatKind.ATK_RATE): (0.063, 0.348),
    (4, artifact.StatKind.DEF_RATE): (0.079, 0.435),
    (4, artifact.StatKind.EM): (25.2, 139.3),
    (4, artifact.StatKind.ER): (0.070, 0.387),
    (4, artifact.StatKind.CR): (0.042, 0.232),
    (4, artifact.StatKind.CD): (0.084, 0.464),
    (4, artifact.StatKind.HEALING): (0.048, 0.268),
    (4, artifact.StatKind.PHYICAL_DMG): (0.079, 0.435),
    (4, artifact.StatKind.ANEMO_DMG): (0.063, 0.348),
    (4, artifact.StatKind.GEO_DMG): (0.063, 0.348),
    (4, artifact.StatKind.ELECTRO_DMG): (0.063, 0.348),
    (4, artifact.StatKind.DENDRO_DMG): (0.063, 0.348),
    (4, artifact.StatKind.HYDRO_DMG): (0.063, 0.348),
    (4, artifact.StatKind.PYRO_DMG): (0.063, 0.348),
    (4, artifact.StatKind.CRYO_DMG): (0.063, 0.348),
    (5, artifact.StatKind.HP): (717.0, 4_780.0),
    (5, artifact.StatKind.ATK): (47.0, 311.0),
    (5, artifact.StatKind.HP_RATE): (0.070, 0.466),
    (5, artifact.StatKind.ATK_RATE): (0.070, 0.466),
    (5, artifact.StatKind.DEF_RATE): (0.087, 0.583),
    (5, artifact.StatKind.EM): (28.0, 186.5),
    (5, artifact.StatKind.ER): (0.078, 0.518),
    (5, artifact.StatKind.CR): (0.047, 0.311),
    (5, artifact.StatKind.CD): (0.093, 0.622),
    (5, artifact.StatKind.HEALING): (0.054, 0.359),
    (5, artifact.StatKind.PHYICAL_DMG): (0.087, 0.583),
    (5, artifact.StatKind.ANEMO_DMG): (0.070, 0.466),
    (5, artifact.StatKind.GEO_DMG): (0.070, 0.466),
    (5, artifact.StatKind.ELECTRO_DMG): (0.070, 0.466),
    (5, artifact.StatKind.DENDRO_DMG): (0.070, 0.466),
    (5, artifact.StatKind.HYDRO_DMG): (0.070, 0.466),
    (5, artifact.StatKind.PYRO_DMG): (0.070, 0.466),
    (5, artifact.StatKind.CRYO_DMG): (0.070, 0.466),
}


def main_stat_value(kind: artifact.StatKind, rarity: int, level: int) -> float | int:
    start, end = MAIN_STAT_RANGES[(rarity, kind)]
    maximum_level = 16 if rarity == 4 else 20
    value = start + (end - start) * level / maximum_level

    # HP, ATK and EM are integers in the game display
    if kind in (artifact.StatKind.HP, artifact.StatKind.ATK, artifact.StatKind.EM):
        return _round_half_away(value)
    return _round_half_away(value * 1_000.0) / 1_000.0


def _round_half_away(value: float) -> int:
    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)
