"""
Rank ladder for Shahanshahi.

Ranks are driven by character level, not raw XP, so they always stay
in lockstep with the level formula in levels.py.
"""

RANKS = [
    (1, "دهقان"),
    (5, "نگهبان"),
    (10, "سرباز"),
    (16, "فرمانده"),
    (23, "سردار"),
    (31, "ساتراپ"),
    (40, "فرمانروا"),
]


def rank_for_level(level: int) -> str:
    current = RANKS[0][1]
    for min_level, name in RANKS:
        if level >= min_level:
            current = name
        else:
            break
    return current


def next_rank_info(level: int) -> tuple[str, int] | None:
    """Returns (next_rank_name, level_required) or None if at max rank."""
    for min_level, name in RANKS:
        if level < min_level:
            return name, min_level
    return None
