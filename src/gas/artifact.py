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


class ArtifactSet(enum.Enum):
    SILKEN_MOONS_SERENADE = 0
    NIGHT_OF_THE_SKYS_UNVEILING = 1
    A_DAY_CARVED_FROM_RISING_WINDS = 2
    AUBADE_OF_MORNINGSTAR_AND_MOON = 3
    DISENCHANTMENT_IN_DEEP_SHADOW = 4
    CELESTIAL_GIFT = 5
    HEART_OF_THE_FURNACE = 6
    SCARLET_PROOF = 7
    FINALE_OF_THE_DEEP_GALLERIES = 8
    LONG_NIGHTS_OATH = 9
    OBSIDIAN_CODEX = 10
    SCROLL_OF_THE_HERO_OF_CINDER_CITY = 11
    SONG_OF_DAYS_PAST = 12
    UNFINISHED_REVERIE = 13
    FRAGMENT_OF_HARMONIC_WHIMSY = 14
    NIGHTTIME_WHISPERS_IN_THE_ECHOING_WOODS = 15
    GOLDEN_TROUPE = 16
    MARECHAUSSEE_HUNTER = 17
    VOURUKASHAS_GLOW = 18
    NYMPHS_DREAM = 19
    DESERT_PAVILION_CHRONICLE = 20
    FLOWER_OF_PARADISE_LOST = 21
    DEEPWOOD_MEMORIES = 22
    GILDED_DREAMS = 23
    VERMILLION_HEREAFTER = 24
    ECHOES_OF_AN_OFFERING = 25
    HUSK_OF_OPULENT_DREAMS = 26
    OCEAN_HUED_CLAM = 27
    EMBLEM_OF_SEVERED_FATE = 28
    SHIMENAWAS_REMINISCENCE = 29
    TENACITY_OF_THE_MILLELITH = 30
    ARCHAIC_PETRA = 31
    NOBLESSE_OBLIGE = 32
    PALE_FLAME = 33
    RETRACING_BOLIDE = 34
    THUNDERING_FURY = 35
    THUNDER_SOOTHER = 36
    CRIMSON_WITCH_OF_FLAMES = 37
    LAVAWALKER = 38
    VIRIDESCENT_VENERER = 39
    MAIDEN_BELOVED = 40
    HEART_OF_DEPTH = 41
    BLIZZARD_STRAYER = 42
    WANDERERS_TROUPE = 43
    GLADIATORS_FINALE = 44
    BLOODSTAINED_CHIVALRY = 45
    UNKNOW = 46


class ArtifactPiece(enum.Enum):
    FLOWER = 0
    PLUME = 1
    SANDS = 2
    GOBLET = 3
    CIRCLET = 4


class AttrKind(enum.StrEnum):
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
    SHIELD = "shield"
    PHYICAL_DMG = "physical_dmg"
    ANEMO_DMG = "anemo_dmg"
    GEO_DMG = "geo_dmg"
    ELECTRO_DMG = "electro_dmg"
    DENDRO_DMG = "dendro_dmg"
    HYDRO_DMG = "hydro_dmg"
    PYRO_DMG = "pyro_dmg"
    CRYO_DMG = "cryo_dmg"

    @property
    def is_flat(self) -> bool:
        """Flat (non-percentage) attribute kinds."""
        return self in (AttrKind.HP, AttrKind.ATK, AttrKind.DEF, AttrKind.EM)


@dataclass(frozen=True, slots=True)
class Attribute:
    kind: AttrKind
    value: float

    def rounded(self, digits: int = 3) -> "Attribute":
        """Round the value for percentage kinds; flat kinds are kept as-is."""
        if self.kind.is_flat:
            return self
        return Attribute(self.kind, round(self.value, digits))

    @property
    def hash_text(self) -> str:
        return f"Attribute.{self.kind.name}({self.value!r},)"

    def __str__(self) -> str:
        return f"{self.kind.name}({self.value!r})"


@dataclass
class Artifact:
    set: ArtifactSet
    piece: ArtifactPiece
    rarity: int
    level: int
    main_attr: Attribute
    sub_attrs: list[Attribute]
    inactive_sub_attrs: list[Attribute] = field(default_factory=list)


def round_attrs(artifact: Artifact):
    artifact.main_attr = artifact.main_attr.rounded()
    artifact.sub_attrs = [attr.rounded() for attr in artifact.sub_attrs]
    artifact.inactive_sub_attrs = [
        attr.rounded() for attr in artifact.inactive_sub_attrs
    ]


def hash_artifact(artifact: Artifact) -> str:
    hash_value = hashlib.md5()
    hash_value.update(artifact.set.name.encode("utf8"))
    hash_value.update(artifact.piece.name.encode("utf8"))
    hash_value.update(artifact.rarity.to_bytes())
    hash_value.update(artifact.level.to_bytes())

    hash_value.update(artifact.main_attr.hash_text.encode("utf8"))
    for attr in artifact.sub_attrs:
        hash_value.update(attr.hash_text.encode("utf8"))
    for attr in artifact.inactive_sub_attrs:
        hash_value.update(attr.hash_text.encode("utf8"))

    return base64.encodebytes(hash_value.digest()).decode("utf8").strip()


def hash_artifacts(artifacts: list[Artifact]) -> set[str]:
    """Hashes of the artifacts after rounding, used for dedupe."""
    hashes = set()
    for art in artifacts:
        round_attrs(art)
        hashes.add(hash_artifact(art))
    return hashes


def to_dict(artifact: Artifact):
    artifact_dict = {
        "set": artifact.set.name,
        "piece": artifact.piece.name,
        "rarity": artifact.rarity,
        "level": artifact.level,
        "main_attr": _attr_to_dict(artifact.main_attr),
        "sub_attrs": [_attr_to_dict(attr) for attr in artifact.sub_attrs],
    }
    if artifact.inactive_sub_attrs:
        artifact_dict["inactive_sub_attrs"] = [
            _attr_to_dict(attr) for attr in artifact.inactive_sub_attrs
        ]
    return artifact_dict


def from_dict_list(artifact_dict_list: list):
    return [_from_dict(artifact_dict) for artifact_dict in artifact_dict_list]


def _attr_to_dict(attr: Attribute):
    return {"name": attr.kind.value, "value": attr.value}


def _create_attr(name: str, attr_value: float) -> Attribute:
    kind = AttrKind(name)
    value = int(attr_value) if kind.is_flat else attr_value
    return Attribute(kind, value)


def _attr_from_dict(attr_dict: dict):
    attr_type = attr_dict["name"]
    attr_value = attr_dict["value"]
    return _create_attr(attr_type, attr_value)


def _from_dict(artifact_dict: dict):
    artifact = Artifact(
        set=ArtifactSet[artifact_dict["set"]],
        piece=ArtifactPiece[artifact_dict["piece"]],
        rarity=artifact_dict["rarity"],
        level=artifact_dict["level"],
        main_attr=_attr_from_dict(artifact_dict["main_attr"]),  # type: ignore
        sub_attrs=[_attr_from_dict(attr) for attr in artifact_dict["sub_attrs"]],  # type: ignore
        inactive_sub_attrs=[
            _attr_from_dict(attr) for attr in artifact_dict.get("inactive_sub_attrs", [])
        ],  # type: ignore
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

    if src.main_attr != dst.main_attr:
        return False

    for src_sub_attr, dst_sub_attr in zip(src.sub_attrs, dst.sub_attrs):
        if src_sub_attr != dst_sub_attr:
            return False

    if src.inactive_sub_attrs != dst.inactive_sub_attrs:
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
        artifact.main_attr,
        artifact.rarity,
        end="\n",
    )

    for i, sub_attr in enumerate(artifact.sub_attrs):
        print(f"    sub{i + 1}:", sub_attr, end="\n")

    for i, sub_attr in enumerate(artifact.inactive_sub_attrs):
        index = len(artifact.sub_attrs) + i + 1
        print(f"{_COLOR_DIM_GREY}    sub{index}: {sub_attr}{_COLOR_RESET}")
