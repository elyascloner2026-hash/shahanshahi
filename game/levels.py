"""
Level & XP formulas for Shahanshahi.

Kept isolated so balance changes never require touching handler logic.
"""

BASE_XP = 100
GROWTH = 1.15


def xp_required_for_level(level: int) -> int:
    """XP needed to go from `level` to `level + 1`."""
    return int(BASE_XP * (GROWTH ** (level - 1)))


def level_from_xp(total_xp: int) -> tuple[int, int, int]:
    """
    Given cumulative XP, return (level, xp_into_current_level, xp_required_for_next).
    """
    level = 1
    remaining = total_xp
    while True:
        needed = xp_required_for_level(level)
        if remaining < needed:
            return level, remaining, needed
        remaining -= needed
        level += 1


XP_REWARDS = {
    "fight_win": 40,
    "fight_loss": 10,
    "quest_daily": 30,
    "quest_story": 60,
    "event_hero": 50,
    "daily_bonus": 15,
}
