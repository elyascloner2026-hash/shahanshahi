from game.levels import level_from_xp, xp_required_for_level
from game.ranks import rank_for_level, next_rank_info


def test_level_starts_at_one_with_no_xp():
    level, xp_in_level, xp_needed = level_from_xp(0)
    assert level == 1
    assert xp_in_level == 0
    assert xp_needed == xp_required_for_level(1)


def test_level_up_after_enough_xp():
    needed = xp_required_for_level(1)
    level, xp_in_level, _ = level_from_xp(needed)
    assert level == 2
    assert xp_in_level == 0


def test_level_progresses_with_growth_curve():
    total = sum(xp_required_for_level(i) for i in range(1, 6))
    level, _, _ = level_from_xp(total)
    assert level == 6


def test_rank_for_level_beginner():
    assert rank_for_level(1) == "دهقان"


def test_rank_up_thresholds():
    assert rank_for_level(5) == "نگهبان"
    assert rank_for_level(10) == "سرباز"
    assert rank_for_level(40) == "فرمانروا"


def test_next_rank_info_reports_upcoming_rank():
    name, level_required = next_rank_info(3)
    assert name == "نگهبان"
    assert level_required == 5


def test_next_rank_info_none_at_max_rank():
    assert next_rank_info(50) is None
