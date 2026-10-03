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
        artifact.StatKind.PHYSICAL_DMG,
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

MAIN_STAT_COEFFICIENTS = {
    (4, artifact.StatKind.HP): 26.8900602,
    (4, artifact.StatKind.ATK): 1.7469879,
    (4, artifact.StatKind.HP_RATE): 0.0052409,
    (4, artifact.StatKind.ATK_RATE): 0.0052409,
    (4, artifact.StatKind.DEF_RATE): 0.0065512,
    (4, artifact.StatKind.EM): 2.0933735,
    (4, artifact.StatKind.ER): 0.0058283,
    (4, artifact.StatKind.CR): 0.0034939,
    (4, artifact.StatKind.CD): 0.0069879,
    (4, artifact.StatKind.HEALING): 0.0040351,
    (4, artifact.StatKind.PHYSICAL_DMG): 0.0065512,
    (4, artifact.StatKind.ANEMO_DMG): 0.0052409,
    (4, artifact.StatKind.GEO_DMG): 0.0052409,
    (4, artifact.StatKind.ELECTRO_DMG): 0.0052409,
    (4, artifact.StatKind.DENDRO_DMG): 0.0052409,
    (4, artifact.StatKind.HYDRO_DMG): 0.0052409,
    (4, artifact.StatKind.PYRO_DMG): 0.0052409,
    (4, artifact.StatKind.CRYO_DMG): 0.0052409,
    (5, artifact.StatKind.HP): 29.8754,
    (5, artifact.StatKind.ATK): 1.9449977,
    (5, artifact.StatKind.HP_RATE): 0.0058282,
    (5, artifact.StatKind.ATK_RATE): 0.0058282,
    (5, artifact.StatKind.DEF_RATE): 0.0072841,
    (5, artifact.StatKind.EM): 2.3332930,
    (5, artifact.StatKind.ER): 0.0064750,
    (5, artifact.StatKind.CR): 0.0038858,
    (5, artifact.StatKind.CD): 0.0077710,
    (5, artifact.StatKind.HEALING): 0.0044835,
    (5, artifact.StatKind.PHYSICAL_DMG): 0.0072841,
    (5, artifact.StatKind.ANEMO_DMG): 0.0058282,
    (5, artifact.StatKind.GEO_DMG): 0.0058282,
    (5, artifact.StatKind.ELECTRO_DMG): 0.0058282,
    (5, artifact.StatKind.DENDRO_DMG): 0.0058282,
    (5, artifact.StatKind.HYDRO_DMG): 0.0058282,
    (5, artifact.StatKind.PYRO_DMG): 0.0058282,
    (5, artifact.StatKind.CRYO_DMG): 0.0058282,
}

_FLAT_KINDS = {artifact.StatKind.HP, artifact.StatKind.ATK}


def main_stat_value(kind: artifact.StatKind, rarity: int, level: int) -> float | int:
    coefficient = MAIN_STAT_COEFFICIENTS[(rarity, kind)]
    factor = 0.4 if kind in _FLAT_KINDS else 0.2
    value = coefficient * factor * (17 * level + 60)

    # HP, ATK and EM are integers in the game display
    if kind in (artifact.StatKind.HP, artifact.StatKind.ATK, artifact.StatKind.EM):
        return _round_half_away(value)
    return _round_half_away(value * 1_000.0) / 1_000.0


def _round_half_away(value: float) -> int:
    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)
