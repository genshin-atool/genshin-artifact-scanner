"""String matching utilities for OCR text.

Mirrors the compose project's TextUtil: normalization plus bounded
Levenshtein edit distance with early pruning.
"""

from typing import Mapping, TypeVar

T = TypeVar("T")


def normalize(value: str) -> str:
    """Lowercase and keep only letters and digits (removes punctuation/spaces)."""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def edit_distance(first: str, second: str, max_distance: int | None = None) -> int:
    """Bounded Levenshtein edit distance.

    Uses a rolling array (O(N) space) and aborts a row as soon as its
    minimum value exceeds max_distance; returns max_distance + 1 in that case.
    """
    if max_distance is None:
        max_distance = max(len(first), len(second))

    previous = list(range(len(second) + 1))
    current = [0] * (len(second) + 1)

    for i, first_char in enumerate(first):
        current[0] = i + 1
        row_minimum = current[0]

        for j, second_char in enumerate(second):
            substitution_cost = 0 if first_char == second_char else 1
            current[j + 1] = min(
                current[j] + 1,
                previous[j + 1] + 1,
                previous[j] + substitution_cost,
            )
            row_minimum = min(row_minimum, current[j + 1])

        if row_minimum > max_distance:
            return max_distance + 1

        previous, current = current, previous

    return previous[len(second)]


def maximum_edit_distance(length: int) -> int:
    """Allowed edit distance by query length (short text, few typos)."""
    if length < 8:
        return 1
    if length < 24:
        return 2
    return 3


# Prefix allowance applies only to longer queries; short names (e.g. the
# generic piece label "Goblet") would otherwise false-match long aliases
# that merely start with the same text
_PREFIX_MIN_LENGTH = 8


def fuzzy_match(text: str, candidates: Mapping[str, T]) -> T | None:
    """Match text against normalized candidates.

    Exact matches win; otherwise candidates within the allowed edit
    distance are ranked, and a tie between the top two is rejected to
    avoid false positives. Truncated OCR text (a prefix of the candidate,
    or vice versa) is allowed to differ by the full length difference.
    """
    normalized = normalize(text)
    if not normalized:
        return None

    exact = candidates.get(normalized)
    if exact is not None:
        return exact

    max_distance = maximum_edit_distance(len(normalized))
    ranked: list[tuple[int, T]] = []
    for candidate, value in candidates.items():
        if len(normalized) >= _PREFIX_MIN_LENGTH and (
            normalized.startswith(candidate) or candidate.startswith(normalized)
        ):
            allowed = abs(len(candidate) - len(normalized))
        else:
            allowed = max_distance
            if abs(len(candidate) - len(normalized)) > allowed:
                continue
        distance = edit_distance(normalized, candidate, allowed)
        if distance <= allowed:
            ranked.append((distance, value))

    if not ranked:
        return None

    ranked.sort(key=lambda item: item[0])
    # Ambiguity check on values: ties are rejected only when the tied
    # candidates point to different values (mirrors compose)
    best_distance = ranked[0][0]
    tied_values = {value for distance, value in ranked if distance == best_distance}
    if len(tied_values) > 1:
        return None

    return ranked[0][1]
