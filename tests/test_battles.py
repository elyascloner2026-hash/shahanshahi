from game.battles import resolve_fight, is_protected, combat_score


def _stats(power=100, defense=100, level=1, rank="دهقان", hero_bonus=0):
    return {"power": power, "defense": defense, "level": level, "rank": rank, "hero_bonus": hero_bonus}


def test_stronger_attacker_usually_wins_over_many_trials():
    strong = _stats(power=1000, defense=1000, level=20, rank="فرمانده")
    weak = _stats(power=10, defense=10, level=1, rank="دهقان")

    wins = 0
    trials = 200
    for _ in range(trials):
        outcome = resolve_fight(strong, weak)
        if outcome["attacker_wins"]:
            wins += 1
    # randomness exists, but a huge stat gap should win almost always
    assert wins > trials * 0.9


def test_resolve_fight_returns_expected_keys():
    outcome = resolve_fight(_stats(), _stats())
    assert "attacker_wins" in outcome
    assert "coins_reward" in outcome
    assert outcome["coins_reward"] > 0


def test_hero_bonus_increases_combat_score():
    base = combat_score(power=100, defense=100, level=5, rank="دهقان", hero_bonus=0)
    boosted = combat_score(power=100, defense=100, level=5, rank="دهقان", hero_bonus=50)
    assert boosted > base


def test_beginner_protection_flag():
    assert is_protected(1) is True
    assert is_protected(4) is True
    assert is_protected(10) is False
