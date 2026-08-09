import json
import math

from .. import artifact

_FORMAT = "GOOD"
_SOURCE = "Genshin ATool"
_VERSION = 3

_SLOT_KEYS = {
    artifact.ArtifactPiece.FLOWER: "flower",
    artifact.ArtifactPiece.PLUME: "plume",
    artifact.ArtifactPiece.SANDS: "sands",
    artifact.ArtifactPiece.GOBLET: "goblet",
    artifact.ArtifactPiece.CIRCLET: "circlet",
}

_STAT_KEYS = {
    artifact.AttrKind.HP: "hp",
    artifact.AttrKind.HP_RATE: "hp_",
    artifact.AttrKind.ATK: "atk",
    artifact.AttrKind.ATK_RATE: "atk_",
    artifact.AttrKind.DEF: "def",
    artifact.AttrKind.DEF_RATE: "def_",
    artifact.AttrKind.CR: "critRate_",
    artifact.AttrKind.CD: "critDMG_",
    artifact.AttrKind.ER: "enerRech_",
    artifact.AttrKind.EM: "eleMas",
    artifact.AttrKind.HEALING: "heal_",
    artifact.AttrKind.PHYICAL_DMG: "physical_dmg_",
    artifact.AttrKind.ANEMO_DMG: "anemo_dmg_",
    artifact.AttrKind.GEO_DMG: "geo_dmg_",
    artifact.AttrKind.ELECTRO_DMG: "electro_dmg_",
    artifact.AttrKind.DENDRO_DMG: "dendro_dmg_",
    artifact.AttrKind.HYDRO_DMG: "hydro_dmg_",
    artifact.AttrKind.PYRO_DMG: "pyro_dmg_",
    artifact.AttrKind.CRYO_DMG: "cryo_dmg_",
}

# Artifact sets not in the current GOOD schema (or unknown) are rejected
# at export time.
_SET_KEYS = {
    artifact.ArtifactSet.SILKEN_MOONS_SERENADE: "SilkenMoonsSerenade",
    artifact.ArtifactSet.NIGHT_OF_THE_SKYS_UNVEILING: "NightOfTheSkysUnveiling",
    artifact.ArtifactSet.A_DAY_CARVED_FROM_RISING_WINDS: "ADayCarvedFromRisingWinds",
    artifact.ArtifactSet.AUBADE_OF_MORNINGSTAR_AND_MOON: "AubadeOfMorningstarAndMoon",
    artifact.ArtifactSet.DISENCHANTMENT_IN_DEEP_SHADOW: "DisenchantmentInDeepShadow",
    artifact.ArtifactSet.CELESTIAL_GIFT: "CelestialGift",
    artifact.ArtifactSet.HEART_OF_THE_FURNACE: None,
    artifact.ArtifactSet.SCARLET_PROOF: None,
    artifact.ArtifactSet.FINALE_OF_THE_DEEP_GALLERIES: "FinaleOfTheDeepGalleries",
    artifact.ArtifactSet.LONG_NIGHTS_OATH: "LongNightsOath",
    artifact.ArtifactSet.OBSIDIAN_CODEX: "ObsidianCodex",
    artifact.ArtifactSet.SCROLL_OF_THE_HERO_OF_CINDER_CITY: "ScrollOfTheHeroOfCinderCity",
    artifact.ArtifactSet.SONG_OF_DAYS_PAST: "SongOfDaysPast",
    artifact.ArtifactSet.UNFINISHED_REVERIE: "UnfinishedReverie",
    artifact.ArtifactSet.FRAGMENT_OF_HARMONIC_WHIMSY: "FragmentOfHarmonicWhimsy",
    artifact.ArtifactSet.NIGHTTIME_WHISPERS_IN_THE_ECHOING_WOODS: "NighttimeWhispersInTheEchoingWoods",
    artifact.ArtifactSet.GOLDEN_TROUPE: "GoldenTroupe",
    artifact.ArtifactSet.MARECHAUSSEE_HUNTER: "MarechausseeHunter",
    artifact.ArtifactSet.VOURUKASHAS_GLOW: "VourukashasGlow",
    artifact.ArtifactSet.NYMPHS_DREAM: "NymphsDream",
    artifact.ArtifactSet.DESERT_PAVILION_CHRONICLE: "DesertPavilionChronicle",
    artifact.ArtifactSet.FLOWER_OF_PARADISE_LOST: "FlowerOfParadiseLost",
    artifact.ArtifactSet.DEEPWOOD_MEMORIES: "DeepwoodMemories",
    artifact.ArtifactSet.GILDED_DREAMS: "GildedDreams",
    artifact.ArtifactSet.VERMILLION_HEREAFTER: "VermillionHereafter",
    artifact.ArtifactSet.ECHOES_OF_AN_OFFERING: "EchoesOfAnOffering",
    artifact.ArtifactSet.HUSK_OF_OPULENT_DREAMS: "HuskOfOpulentDreams",
    artifact.ArtifactSet.OCEAN_HUED_CLAM: "OceanHuedClam",
    artifact.ArtifactSet.EMBLEM_OF_SEVERED_FATE: "EmblemOfSeveredFate",
    artifact.ArtifactSet.SHIMENAWAS_REMINISCENCE: "ShimenawasReminiscence",
    artifact.ArtifactSet.TENACITY_OF_THE_MILLELITH: "TenacityOfTheMillelith",
    artifact.ArtifactSet.ARCHAIC_PETRA: "ArchaicPetra",
    artifact.ArtifactSet.NOBLESSE_OBLIGE: "NoblesseOblige",
    artifact.ArtifactSet.PALE_FLAME: "PaleFlame",
    artifact.ArtifactSet.RETRACING_BOLIDE: "RetracingBolide",
    artifact.ArtifactSet.THUNDERING_FURY: "ThunderingFury",
    artifact.ArtifactSet.THUNDER_SOOTHER: "Thundersoother",
    artifact.ArtifactSet.CRIMSON_WITCH_OF_FLAMES: "CrimsonWitchOfFlames",
    artifact.ArtifactSet.LAVAWALKER: "Lavawalker",
    artifact.ArtifactSet.VIRIDESCENT_VENERER: "ViridescentVenerer",
    artifact.ArtifactSet.MAIDEN_BELOVED: "MaidenBeloved",
    artifact.ArtifactSet.HEART_OF_DEPTH: "HeartOfDepth",
    artifact.ArtifactSet.BLIZZARD_STRAYER: "BlizzardStrayer",
    artifact.ArtifactSet.WANDERERS_TROUPE: "WanderersTroupe",
    artifact.ArtifactSet.GLADIATORS_FINALE: "GladiatorsFinale",
    artifact.ArtifactSet.BLOODSTAINED_CHIVALRY: "BloodstainedChivalry",
    artifact.ArtifactSet.UNKNOW: None,
}


class GoodExporter:
    """GOOD (Genshin Open Object Descriptor) v3.

    Main stat values are not stored in the GOOD format; they are derived
    from rarity and level on load.
    """

    def load(self, path: str) -> list[artifact.Artifact]:
        with open(path, encoding="utf-8") as f:
            root = json.load(f)
        return _from_good_file(root)

    @classmethod
    def detect(cls, content: bytes) -> bool:
        try:
            root = json.loads(content.decode("utf-8"))
        except Exception:
            return False
        return isinstance(root, dict) and root.get("format") == _FORMAT

    def dump(self, path: str, artifacts: list[artifact.Artifact]) -> None:
        # Build and validate the full document before writing, so an
        # unmappable artifact never leaves a partially written file.
        root = _to_good_file(artifacts)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(root, f, ensure_ascii=False, indent=2)


def _to_good_file(artifacts: list[artifact.Artifact]) -> dict:
    return {
        "format": _FORMAT,
        "source": _SOURCE,
        "version": _VERSION,
        "artifacts": [_to_good_artifact(art) for art in artifacts],
    }


def _to_good_artifact(art: artifact.Artifact) -> dict:
    set_key = _SET_KEYS[art.set]
    if set_key is None:
        raise ValueError(
            f"Artifact set {art.set.name} is not supported by the current GOOD schema"
        )

    good = {
        "setKey": set_key,
        "slotKey": _SLOT_KEYS[art.piece],
        "level": art.level,
        "rarity": art.rarity,
        "mainStatKey": _to_good_stat_key(art.main_attr),
        "location": "",
        "lock": False,
        "substats": [_to_good_substat(attr) for attr in art.sub_attrs],
    }
    if art.inactive_sub_attrs:
        good["unactivatedSubstats"] = [
            _to_good_substat(attr) for attr in art.inactive_sub_attrs
        ]
    return good


def _to_good_substat(attr: artifact.Attribute) -> dict:
    return {
        "key": _to_good_stat_key(attr),
        "value": _to_good_value(attr),
    }


def _to_good_stat_key(attr: artifact.Attribute) -> str:
    try:
        return _STAT_KEYS[attr.kind]
    except KeyError:
        raise ValueError(f"{attr.kind.name} is not a valid GOOD stat") from None


def _to_good_value(attr: artifact.Attribute) -> float:
    value = attr.value if attr.kind.is_flat else attr.value * 100.0
    return round(value, 6)


_GOOD_SLOT_KEYS = {key: piece for piece, key in _SLOT_KEYS.items()}
_GOOD_STAT_KINDS = {key: kind for kind, key in _STAT_KEYS.items()}
_GOOD_SET_KEYS = {
    key: artifact_set for artifact_set, key in _SET_KEYS.items() if key is not None
}

_SUB_STAT_KINDS = {
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

_MAIN_ATTR_KINDS = {
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
_MAIN_ATTR_RANGES = {
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


def _from_good_file(root: dict) -> list[artifact.Artifact]:
    if root.get("format") != _FORMAT:
        raise ValueError(f"Unsupported GOOD format: {root.get('format')!r}")

    version = root.get("version")
    if not isinstance(version, int) or not 1 <= version <= _VERSION:
        raise ValueError(f"Unsupported GOOD version: {version!r}")

    return [_from_good_artifact(raw) for raw in root.get("artifacts", [])]


def _from_good_artifact(raw: dict) -> artifact.Artifact:
    set_key = raw.get("setKey")
    artifact_set = _GOOD_SET_KEYS.get(set_key)
    if artifact_set is None:
        raise ValueError(f"Unsupported GOOD setKey: {set_key!r}")

    slot_key = raw.get("slotKey")
    piece = _GOOD_SLOT_KEYS.get(slot_key)
    if piece is None:
        raise ValueError(f"Unsupported GOOD slotKey: {slot_key!r}")

    rarity = raw.get("rarity")
    if rarity not in (4, 5):
        raise ValueError(f"Unsupported GOOD rarity: {rarity!r}")

    level = raw.get("level")
    maximum_level = 16 if rarity == 4 else 20
    if not isinstance(level, int) or not 0 <= level <= maximum_level:
        raise ValueError(f"Unsupported GOOD level: {level!r} for rarity {rarity}")

    main_stat_key = raw.get("mainStatKey")
    main_kind = _GOOD_STAT_KINDS.get(main_stat_key)
    if main_kind is None:
        raise ValueError(f"Unsupported GOOD mainStatKey: {main_stat_key!r}")
    if main_kind not in _MAIN_ATTR_KINDS[piece]:
        raise ValueError(f"{main_stat_key!r} is not a valid main stat for {slot_key!r}")

    return artifact.Artifact(
        set=artifact_set,
        piece=piece,
        rarity=rarity,
        level=level,
        main_attr=artifact.Attribute(
            main_kind, _main_attribute_value(main_kind, rarity, level)
        ),
        sub_attrs=[
            _from_good_substat(raw_substat) for raw_substat in raw.get("substats", [])
        ],
        inactive_sub_attrs=[
            _from_good_substat(raw_substat)
            for raw_substat in raw.get("unactivatedSubstats", [])
        ],
    )


def _from_good_substat(raw: dict) -> artifact.Attribute:
    stat_key = raw.get("key")
    kind = _GOOD_STAT_KINDS.get(stat_key)
    if kind is None:
        raise ValueError(f"Unsupported GOOD substat key: {stat_key!r}")
    if kind not in _SUB_STAT_KINDS:
        raise ValueError(f"{stat_key!r} is not a valid GOOD substat")

    value = raw.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"Invalid GOOD substat value: {value!r}")
    if not math.isfinite(value):
        raise ValueError(f"Invalid GOOD substat value: {value!r}")

    value = value / 100.0 if not kind.is_flat else value
    return artifact.Attribute(kind, value)


def _main_attribute_value(kind: artifact.AttrKind, rarity: int, level: int) -> float:
    start, end = _MAIN_ATTR_RANGES[(rarity, kind)]
    maximum_level = 16 if rarity == 4 else 20
    value = start + (end - start) * level / maximum_level

    if kind in (artifact.AttrKind.HP, artifact.AttrKind.ATK):
        return float(_round_half_away(value))
    if kind is artifact.AttrKind.EM:
        return _round_half_away(value * 10.0) / 10.0
    return _round_half_away(value * 1_000.0) / 1_000.0


def _round_half_away(value: float) -> int:
    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)
