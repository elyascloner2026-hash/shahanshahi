from game.army import UNITS

def test_each_army_family_has_15_levels():
    for family in ("archer", "swordsman", "guard"):
        levels = [UNITS[f"{family}_{i}"].level for i in range(1, 16)]
        assert levels == list(range(1, 16))

def test_higher_levels_are_stronger():
    for family in ("archer", "swordsman", "guard"):
        assert UNITS[f"{family}_15"].power > UNITS[f"{family}_1"].power
        assert UNITS[f"{family}_15"].defense > UNITS[f"{family}_1"].defense
