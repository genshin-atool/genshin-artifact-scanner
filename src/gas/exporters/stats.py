"""Shared game data for deriving main stat values from rarity and level."""

import math

from .. import artifact

SUB_STAT_KINDS = {
    artifact.AttrKind.HP,
    artifact.AttrKind.HP_RATE,
    artifact.AttrKind.ATK,
    artifact.AttrKind.ATK_RATE,
    artifact.AttrKind.DEF,
    artifact.AttrKind.DEF_RATE,
    artifact.AttrKind.EM,
    artifact.AttrKind.ER,
    artifact.AttrKind.CR,
    artifact.AttrKind.CD,
}

MAIN_ATTR_KINDS = {
    artifact.ArtifactPiece.FLOWER: {artifact.AttrKind.HP},
    artifact.ArtifactPiece.PLUME: {artifact.AttrKind.ATK},
    artifact.ArtifactPiece.SANDS: {
        artifact.AttrKind.HP_RATE,
        artifact.AttrKind.ATK_RATE,
        artifact.AttrKind.DEF_RATE,
        artifact.AttrKind.EM,
        artifact.AttrKind.ER,
    },
    artifact.ArtifactPiece.GOBLET: {
        artifact.AttrKind.HP_RATE,
        artifact.AttrKind.ATK_RATE,
        artifact.AttrKind.DEF_RATE,
        artifact.AttrKind.EM,
        artifact.AttrKind.PHYICAL_DMG,
        artifact.AttrKind.ANEMO_DMG,
        artifact.AttrKind.GEO_DMG,
        artifact.AttrKind.ELECTRO_DMG,
        artifact.AttrKind.DENDRO_DMG,
        artifact.AttrKind.HYDRO_DMG,
        artifact.AttrKind.PYRO_DMG,
        artifact.AttrKind.CRYO_DMG,
    },
    artifact.ArtifactPiece.CIRCLET: {
        artifact.AttrKind.HP_RATE,
        artifact.AttrKind.ATK_RATE,
        artifact.AttrKind.DEF_RATE,
        artifact.AttrKind.EM,
        artifact.AttrKind.CR,
        artifact.AttrKind.CD,
        artifact.AttrKind.HEALING,
    },
}

# Main stat value at level 0 and at max level (start, end), per rarity.
MAIN_ATTR_RANGES = {
    (4, artifact.AttrKind.HP): (645.0, 3_571.0),
    (4, artifact.AttrKind.ATK): (42.0, 232.0),
    (4, artifact.AttrKind.HP_RATE): (0.063, 0.348),
    (4, artifact.AttrKind.ATK_RATE): (0.063, 0.348),
    (4, artifact.AttrKind.DEF_RATE): (0.079, 0.435),
    (4, artifact.AttrKind.EM): (25.2, 139.3),
    (4, artifact.AttrKind.ER): (0.070, 0.387),
    (4, artifact.AttrKind.CR): (0.042, 0.232),
    (4, artifact.AttrKind.CD): (0.084, 0.464),
    (4, artifact.AttrKind.HEALING): (0.048, 0.268),
    (4, artifact.AttrKind.PHYICAL_DMG): (0.079, 0.435),
    (4, artifact.AttrKind.ANEMO_DMG): (0.063, 0.348),
    (4, artifact.AttrKind.GEO_DMG): (0.063, 0.348),
    (4, artifact.AttrKind.ELECTRO_DMG): (0.063, 0.348),
    (4, artifact.AttrKind.DENDRO_DMG): (0.063, 0.348),
    (4, artifact.AttrKind.HYDRO_DMG): (0.063, 0.348),
    (4, artifact.AttrKind.PYRO_DMG): (0.063, 0.348),
    (4, artifact.AttrKind.CRYO_DMG): (0.063, 0.348),
    (5, artifact.AttrKind.HP): (717.0, 4_780.0),
    (5, artifact.AttrKind.ATK): (47.0, 311.0),
    (5, artifact.AttrKind.HP_RATE): (0.070, 0.466),
    (5, artifact.AttrKind.ATK_RATE): (0.070, 0.466),
    (5, artifact.AttrKind.DEF_RATE): (0.087, 0.583),
    (5, artifact.AttrKind.EM): (28.0, 186.5),
    (5, artifact.AttrKind.ER): (0.078, 0.518),
    (5, artifact.AttrKind.CR): (0.047, 0.311),
    (5, artifact.AttrKind.CD): (0.093, 0.622),
    (5, artifact.AttrKind.HEALING): (0.054, 0.359),
    (5, artifact.AttrKind.PHYICAL_DMG): (0.087, 0.583),
    (5, artifact.AttrKind.ANEMO_DMG): (0.070, 0.466),
    (5, artifact.AttrKind.GEO_DMG): (0.070, 0.466),
    (5, artifact.AttrKind.ELECTRO_DMG): (0.070, 0.466),
    (5, artifact.AttrKind.DENDRO_DMG): (0.070, 0.466),
    (5, artifact.AttrKind.HYDRO_DMG): (0.070, 0.466),
    (5, artifact.AttrKind.PYRO_DMG): (0.070, 0.466),
    (5, artifact.AttrKind.CRYO_DMG): (0.070, 0.466),
}


def main_attribute_value(kind: artifact.AttrKind, rarity: int, level: int) -> float | int:
    start, end = MAIN_ATTR_RANGES[(rarity, kind)]
    maximum_level = 16 if rarity == 4 else 20
    value = start + (end - start) * level / maximum_level

    # HP, ATK and EM are integers in the game display
    if kind in (artifact.AttrKind.HP, artifact.AttrKind.ATK, artifact.AttrKind.EM):
        return _round_half_away(value)
    return _round_half_away(value * 1_000.0) / 1_000.0


def _round_half_away(value: float) -> int:
    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)
