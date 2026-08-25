import enum
import hashlib
import base64
from dataclasses import dataclass, field

_COLOR_PINK = "\033[95m"
_COLOR_PURPLE = "\033[95m"
_COLOR_CYAN = "\033[96m"
_COLOR_WHITE = "\033[97m"
_COLOR_BLACK = "\033[30m"
_COLOR_GREY = "\033[90m"
_COLOR_DIM_GREY = "\033[2;37m"
_COLOR_ORANGE = "\033[91m"
_COLOR_YELLOW = "\033[93m"
_COLOR_GREEN = "\033[92m"
_COLOR_RED = "\033[91m"
_COLOR_BLUE = "\033[94m"
_COLOR_RESET = "\033[0m"


class ArtifactSet(enum.StrEnum):
    SILKEN_MOONS_SERENADE = "silken_moons_serenade"
    NIGHT_OF_THE_SKYS_UNVEILING = "night_of_the_skys_unveiling"
    A_DAY_CARVED_FROM_RISING_WINDS = "a_day_carved_from_rising_winds"
    AUBADE_OF_MORNINGSTAR_AND_MOON = "aubade_of_morningstar_and_moon"
    DISENCHANTMENT_IN_DEEP_SHADOW = "disenchantment_in_deep_shadow"
    CELESTIAL_GIFT = "celestial_gift"
    HEART_OF_THE_FURNACE = "heart_of_the_furnace"
    SCARLET_PROOF = "scarlet_proof"
    FINALE_OF_THE_DEEP_GALLERIES = "finale_of_the_deep_galleries"
    LONG_NIGHTS_OATH = "long_nights_oath"
    OBSIDIAN_CODEX = "obsidian_codex"
    SCROLL_OF_THE_HERO_OF_CINDER_CITY = "scroll_of_the_hero_of_cinder_city"
    SONG_OF_DAYS_PAST = "song_of_days_past"
    UNFINISHED_REVERIE = "unfinished_reverie"
    FRAGMENT_OF_HARMONIC_WHIMSY = "fragment_of_harmonic_whimsy"
    NIGHTTIME_WHISPERS_IN_THE_ECHOING_WOODS = "nighttime_whispers_in_the_echoing_woods"
    GOLDEN_TROUPE = "golden_troupe"
    MARECHAUSSEE_HUNTER = "marechaussee_hunter"
    VOURUKASHAS_GLOW = "vourukashas_glow"
    NYMPHS_DREAM = "nymphs_dream"
    DESERT_PAVILION_CHRONICLE = "desert_pavilion_chronicle"
    FLOWER_OF_PARADISE_LOST = "flower_of_paradise_lost"
    DEEPWOOD_MEMORIES = "deepwood_memories"
    GILDED_DREAMS = "gilded_dreams"
    VERMILLION_HEREAFTER = "vermillion_hereafter"
    ECHOES_OF_AN_OFFERING = "echoes_of_an_offering"
    HUSK_OF_OPULENT_DREAMS = "husk_of_opulent_dreams"
    OCEAN_HUED_CLAM = "ocean_hued_clam"
    EMBLEM_OF_SEVERED_FATE = "emblem_of_severed_fate"
    SHIMENAWAS_REMINISCENCE = "shimenawas_reminiscence"
    TENACITY_OF_THE_MILLELITH = "tenacity_of_the_millelith"
    ARCHAIC_PETRA = "archaic_petra"
    NOBLESSE_OBLIGE = "noblesse_oblige"
    PALE_FLAME = "pale_flame"
    RETRACING_BOLIDE = "retracing_bolide"
    THUNDERING_FURY = "thundering_fury"
    THUNDER_SOOTHER = "thunder_soother"
    CRIMSON_WITCH_OF_FLAMES = "crimson_witch_of_flames"
    LAVAWALKER = "lavawalker"
    VIRIDESCENT_VENERER = "viridescent_venerer"
    MAIDEN_BELOVED = "maiden_beloved"
    HEART_OF_DEPTH = "heart_of_depth"
    BLIZZARD_STRAYER = "blizzard_strayer"
    WANDERERS_TROUPE = "wanderers_troupe"
    GLADIATORS_FINALE = "gladiators_finale"
    BLOODSTAINED_CHIVALRY = "bloodstained_chivalry"
    UNKNOW = "unknow"


class ArtifactPiece(enum.StrEnum):
    FLOWER = "flower"
    PLUME = "plume"
    SANDS = "sands"
    GOBLET = "goblet"
    CIRCLET = "circlet"


class StatKind(enum.StrEnum):
    HP = "hp"
    HP_RATE = "hp_rate"
    ATK = "atk"
    ATK_RATE = "atk_rate"
    DEF = "def"
    DEF_RATE = "def_rate"
    CR = "cr"
    CD = "cd"
    ER = "er"
    EM = "em"
    HEALING = "healing"
    PHYSICAL_DMG = "physical_dmg"
    ANEMO_DMG = "anemo_dmg"
    GEO_DMG = "geo_dmg"
    ELECTRO_DMG = "electro_dmg"
    DENDRO_DMG = "dendro_dmg"
    HYDRO_DMG = "hydro_dmg"
    PYRO_DMG = "pyro_dmg"
    CRYO_DMG = "cryo_dmg"

    @property
    def is_flat(self) -> bool:
        """Flat (non-percentage) stat kinds."""
        return self in (StatKind.HP, StatKind.ATK, StatKind.DEF, StatKind.EM)


@dataclass(frozen=True, slots=True)
class Stat:
    kind: StatKind
    value: float

    def rounded(self, digits: int = 3) -> "Stat":
        """Round the value for percentage kinds; flat kinds are kept as-is."""
        if self.kind.is_flat:
            return self
        return Stat(self.kind, round(self.value, digits))

    @property
    def hash_text(self) -> str:
        return f"Stat.{self.kind.name}({self.value!r},)"

    def __str__(self) -> str:
        return f"{self.kind.name}({self.value!r})"


@dataclass
class Artifact:
    set: ArtifactSet
    piece: ArtifactPiece
    rarity: int
    level: int
    main_stat: Stat
    sub_stats: list[Stat]
    inactive_sub_stats: list[Stat] = field(default_factory=list)


def round_stats(artifact: Artifact):
    artifact.main_stat = artifact.main_stat.rounded()
    artifact.sub_stats = [stat.rounded() for stat in artifact.sub_stats]
    artifact.inactive_sub_stats = [
        stat.rounded() for stat in artifact.inactive_sub_stats
    ]


def hash_artifact(artifact: Artifact) -> str:
    hash_value = hashlib.md5()
    hash_value.update(artifact.set.name.encode("utf8"))
    hash_value.update(artifact.piece.name.encode("utf8"))
    hash_value.update(artifact.rarity.to_bytes())
    hash_value.update(artifact.level.to_bytes())

    hash_value.update(artifact.main_stat.hash_text.encode("utf8"))
    for stat in artifact.sub_stats:
        hash_value.update(stat.hash_text.encode("utf8"))
    for stat in artifact.inactive_sub_stats:
        hash_value.update(stat.hash_text.encode("utf8"))

    return base64.encodebytes(hash_value.digest()).decode("utf8").strip()


def hash_artifacts(artifacts: list[Artifact]) -> set[str]:
    """Hashes of the artifacts after rounding, used for dedupe."""
    hashes = set()
    for art in artifacts:
        round_stats(art)
        hashes.add(hash_artifact(art))
    return hashes


def to_dict(artifact: Artifact):
    artifact_dict = {
        "set": artifact.set.value,
        "piece": artifact.piece.value,
        "rarity": artifact.rarity,
        "level": artifact.level,
        "main_stat": _stat_to_dict(artifact.main_stat),
        "sub_stats": [_stat_to_dict(stat) for stat in artifact.sub_stats],
    }
    if artifact.inactive_sub_stats:
        artifact_dict["inactive_sub_stats"] = [
            _stat_to_dict(stat) for stat in artifact.inactive_sub_stats
        ]
    return artifact_dict


def from_dict_list(artifact_dict_list: list):
    return [_from_dict(artifact_dict) for artifact_dict in artifact_dict_list]


def _stat_to_dict(stat: Stat):
    return {"name": stat.kind.value, "value": stat.value}


def _create_stat(name: str, stat_value: float) -> Stat:
    kind = StatKind(name)
    value = int(stat_value) if kind.is_flat else stat_value
    return Stat(kind, value)


def _stat_from_dict(stat_dict: dict):
    stat_type = stat_dict["name"]
    stat_value = stat_dict["value"]
    return _create_stat(stat_type, stat_value)


def _from_dict(artifact_dict: dict):
    artifact = Artifact(
        set=ArtifactSet(artifact_dict["set"]),
        piece=ArtifactPiece(artifact_dict["piece"]),
        rarity=artifact_dict["rarity"],
        level=artifact_dict["level"],
        main_stat=_stat_from_dict(artifact_dict["main_stat"]),
        sub_stats=[
            _stat_from_dict(stat) for stat in artifact_dict.get("sub_stats", [])
        ],
        inactive_sub_stats=[
            _stat_from_dict(stat)
            for stat in artifact_dict.get("inactive_sub_stats", [])
        ],
    )
    return artifact


def _to_dict_list(artifacts: list):
    artifact_dict_list = [to_dict(artifact) for artifact in artifacts]
    return artifact_dict_list


def _is_eq(src: Artifact, dst: Artifact):
    if src.set != dst.set:
        return False

    if src.piece != dst.piece:
        return False

    if src.rarity != dst.rarity:
        return False

    if src.level != dst.level:
        return False

    if src.main_stat != dst.main_stat:
        return False

    for src_sub_stat, dst_sub_stat in zip(src.sub_stats, dst.sub_stats):
        if src_sub_stat != dst_sub_stat:
            return False

    if src.inactive_sub_stats != dst.inactive_sub_stats:
        return False

    return True


def _print_artifact_pretty(
    artifact: Artifact,
):
    print(
        "%02d" % artifact.level,
        end=" ",
    )

    print(
        _COLOR_CYAN,
        artifact.set.name,
        _COLOR_RESET,
        _COLOR_GREEN,
        artifact.piece.name,
        _COLOR_RESET,
        "main:",
        artifact.main_stat,
        artifact.rarity,
        end="\n",
    )

    for i, sub_stat in enumerate(artifact.sub_stats):
        print(f"    sub{i + 1}:", sub_stat, end="\n")

    for i, sub_stat in enumerate(artifact.inactive_sub_stats):
        index = len(artifact.sub_stats) + i + 1
        print(f"{_COLOR_DIM_GREY}    sub{index}: {sub_stat}{_COLOR_RESET}")
