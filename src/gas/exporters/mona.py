import json
import math

from .. import artifact
from ..log import Log
from .stats import MAIN_STAT_KINDS, SUB_STAT_KINDS, main_stat_value

_VERSION = "1"

_SLOT_KEYS = {
    artifact.ArtifactPiece.FLOWER: "flower",
    artifact.ArtifactPiece.PLUME: "feather",
    artifact.ArtifactPiece.SANDS: "sand",
    artifact.ArtifactPiece.GOBLET: "cup",
    artifact.ArtifactPiece.CIRCLET: "head",
}

_STAT_KEYS = {
    artifact.StatKind.HP: "lifeStatic",
    artifact.StatKind.HP_RATE: "lifePercentage",
    artifact.StatKind.ATK: "attackStatic",
    artifact.StatKind.ATK_RATE: "attackPercentage",
    artifact.StatKind.DEF: "defendStatic",
    artifact.StatKind.DEF_RATE: "defendPercentage",
    artifact.StatKind.CR: "critical",
    artifact.StatKind.CD: "criticalDamage",
    artifact.StatKind.ER: "recharge",
    artifact.StatKind.EM: "elementalMastery",
    artifact.StatKind.HEALING: "cureEffect",
    artifact.StatKind.PHYSICAL_DMG: "physicalBonus",
    artifact.StatKind.ANEMO_DMG: "windBonus",
    artifact.StatKind.GEO_DMG: "rockBonus",
    artifact.StatKind.ELECTRO_DMG: "thunderBonus",
    artifact.StatKind.DENDRO_DMG: "dendroBonus",
    artifact.StatKind.HYDRO_DMG: "waterBonus",
    artifact.StatKind.PYRO_DMG: "fireBonus",
    artifact.StatKind.CRYO_DMG: "iceBonus",
}

# Artifact sets not in the YAS schema are skipped with a warning at export time
_SET_KEYS = {
    artifact.ArtifactSet.SILKEN_MOONS_SERENADE: "SpinMoonSerenade",
    artifact.ArtifactSet.NIGHT_OF_THE_SKYS_UNVEILING: "RealmMirrorNight",
    artifact.ArtifactSet.A_DAY_CARVED_FROM_RISING_WINDS: "ADayCarvedFromRisingWinds",
    artifact.ArtifactSet.AUBADE_OF_MORNINGSTAR_AND_MOON: "AubadeOfMorningstarAndMoon",
    artifact.ArtifactSet.DISENCHANTMENT_IN_DEEP_SHADOW: "DisenchantmentInDeepShadow",
    artifact.ArtifactSet.CELESTIAL_GIFT: "HeavensGift",
    artifact.ArtifactSet.HEART_OF_THE_FURNACE: "HeartOfTheFurnace",
    artifact.ArtifactSet.SCARLET_PROOF: "ScarletProof",
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
    artifact.ArtifactSet.EMBLEM_OF_SEVERED_FATE: "emblemOfSeveredFate",
    artifact.ArtifactSet.SHIMENAWAS_REMINISCENCE: "shimenawaReminiscence",
    artifact.ArtifactSet.TENACITY_OF_THE_MILLELITH: "tenacityOfTheMillelith",
    artifact.ArtifactSet.ARCHAIC_PETRA: "archaicPetra",
    artifact.ArtifactSet.NOBLESSE_OBLIGE: "noblesseOblige",
    artifact.ArtifactSet.PALE_FLAME: "paleFlame",
    artifact.ArtifactSet.RETRACING_BOLIDE: "retracingBolide",
    artifact.ArtifactSet.THUNDERING_FURY: "thunderingFury",
    artifact.ArtifactSet.THUNDER_SOOTHER: "thunderSmoother",
    artifact.ArtifactSet.CRIMSON_WITCH_OF_FLAMES: "crimsonWitch",
    artifact.ArtifactSet.LAVAWALKER: "lavaWalker",
    artifact.ArtifactSet.VIRIDESCENT_VENERER: "viridescentVenerer",
    artifact.ArtifactSet.MAIDEN_BELOVED: "maidenBeloved",
    artifact.ArtifactSet.HEART_OF_DEPTH: "heartOfDepth",
    artifact.ArtifactSet.BLIZZARD_STRAYER: "blizzardStrayer",
    artifact.ArtifactSet.WANDERERS_TROUPE: "wandererTroupe",
    artifact.ArtifactSet.GLADIATORS_FINALE: "gladiatorFinale",
    artifact.ArtifactSet.BLOODSTAINED_CHIVALRY: "bloodstainedChivalry",
    artifact.ArtifactSet.UNKNOW: None,
}


_MONA_SET_KEYS = {
    key: artifact_set for artifact_set, key in _SET_KEYS.items() if key is not None
}
_MONA_SLOT_KEYS = {key: piece for piece, key in _SLOT_KEYS.items()}
_MONA_STAT_KINDS = {key: kind for kind, key in _STAT_KEYS.items()}


class MonaExporter:
    """Mona format (YAS).

    Main stat values are not stored in the Mona format; they are derived
    from rarity and level on load.
    """

    def load(self, path: str) -> list[artifact.Artifact]:
        with open(path, encoding="utf-8") as f:
            root = json.load(f)
        return _from_mona_file(root)

    @classmethod
    def detect(cls, content: bytes) -> bool:
        try:
            root = json.loads(content.decode("utf-8"))
        except Exception:
            return False
        return (
            isinstance(root, dict)
            and root.get("version") == _VERSION
            and all(key in root for key in ("flower", "feather", "sand", "cup", "head"))
        )

    def dump(self, path: str, artifacts: list[artifact.Artifact]) -> None:
        # Build the full document before writing, so a serialization error
        # never leaves a partially written file.
        root = _to_mona_file(artifacts)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(root, f, ensure_ascii=False, indent=2)


def _to_mona_file(artifacts: list[artifact.Artifact]) -> dict:
    grouped = {key: [] for key in _SLOT_KEYS.values()}
    for art in artifacts:
        mona = _to_mona_artifact(art)
        if mona is not None:
            grouped[_SLOT_KEYS[art.piece]].append(mona)
    return {
        "version": _VERSION,
        "flower": grouped["flower"],
        "feather": grouped["feather"],
        "sand": grouped["sand"],
        "cup": grouped["cup"],
        "head": grouped["head"],
    }


def _to_mona_artifact(art: artifact.Artifact) -> dict | None:
    set_key = _SET_KEYS[art.set]
    if set_key is None:
        Log.warning(
            f"Skipping artifact: set {art.set.name} is not supported by the Mona schema"
        )
        return None

    try:
        return {
            "setName": set_key,
            "position": _SLOT_KEYS[art.piece],
            "mainTag": _to_mona_stat(art.main_stat),
            "normalTags": [_to_mona_stat(stat) for stat in art.sub_stats],
            "omit": False,
            "level": art.level,
            "star": art.rarity,
            "equip": None,
        }
    except ValueError as e:
        Log.warning(f"Skipping artifact: {e}")
        return None


def _to_mona_stat(stat: artifact.Stat) -> dict:
    try:
        name = _STAT_KEYS[stat.kind]
    except KeyError:
        raise ValueError(f"{stat.kind.name} is not a valid Mona stat") from None
    return {"name": name, "value": stat.value}


def _from_mona_file(root: dict) -> list[artifact.Artifact]:
    if root.get("version") != _VERSION:
        raise ValueError(f"Unsupported Mona version: {root.get('version')!r}")

    artifacts = []
    for slot_key in ("flower", "feather", "sand", "cup", "head"):
        for raw in root.get(slot_key, []):
            art = _from_mona_artifact(raw, slot_key)
            if art is not None:
                artifacts.append(art)
    return artifacts


def _from_mona_artifact(
    raw: dict, default_slot_key: str
) -> artifact.Artifact | None:
    try:
        set_key = raw.get("setName")
        artifact_set = _MONA_SET_KEYS.get(set_key)
        if artifact_set is None:
            raise ValueError(f"Unsupported Mona setName: {set_key!r}")

        piece = _MONA_SLOT_KEYS.get(raw.get("position") or default_slot_key)
        if piece is None:
            raise ValueError(f"Unsupported Mona position: {raw.get('position')!r}")

        rarity = raw.get("star")
        if rarity not in (4, 5):
            raise ValueError(f"Unsupported Mona star: {rarity!r}")

        level = raw.get("level")
        maximum_level = 16 if rarity == 4 else 20
        if not isinstance(level, int) or not 0 <= level <= maximum_level:
            raise ValueError(f"Unsupported Mona level: {level!r} for star {rarity}")

        main_tag = raw.get("mainTag") or {}
        main_kind = _MONA_STAT_KINDS.get(main_tag.get("name"))
        if main_kind is None:
            raise ValueError(f"Unsupported Mona mainTag name: {main_tag.get('name')!r}")
        if main_kind not in MAIN_STAT_KINDS[piece]:
            raise ValueError(
                f"{main_tag.get('name')!r} is not a valid main stat for {raw.get('position')!r}"
            )

        return artifact.Artifact(
            set=artifact_set,
            piece=piece,
            rarity=rarity,
            level=level,
            main_stat=artifact.Stat(
                main_kind, main_stat_value(main_kind, rarity, level)
            ),
            sub_stats=[
                _from_mona_substat(tag) for tag in raw.get("normalTags", [])
            ],
        )
    except ValueError as e:
        Log.warning(f"Skipping artifact: {e}")
        return None


def _from_mona_substat(raw: dict) -> artifact.Stat:
    stat_key = raw.get("name")
    kind = _MONA_STAT_KINDS.get(stat_key)
    if kind is None:
        raise ValueError(f"Unsupported Mona stat name: {stat_key!r}")
    if kind not in SUB_STAT_KINDS:
        raise ValueError(f"{stat_key!r} is not a valid Mona substat")

    value = raw.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"Invalid Mona stat value: {value!r}")
    if not math.isfinite(value):
        raise ValueError(f"Invalid Mona stat value: {value!r}")

    # Mona stores ratios for percentage stats; flat values are ints in our model
    value = int(value) if kind.is_flat else value
    return artifact.Stat(kind, value)
