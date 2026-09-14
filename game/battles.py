"""Battle resolution using player stats and the army they actually own."""
import random
from game.ranks import RANKS

RANK_MULTIPLIER = {name: 1.0 + i * 0.05 for i, (_, name) in enumerate(RANKS)}
BEGINNER_PROTECTION_LEVEL = 5
BEGINNER_PROTECTION_LOSS_REDUCTION = 0.5
COIN_REWARD_BASE = 40
COIN_REWARD_PER_LEVEL = 5


def combat_score(power: int, defense: int, level: int, rank: str, hero_bonus: int = 0, army_power: int = 0, army_defense: int = 0) -> float:
    base = power * 0.75 + defense * 0.45 + army_power + army_defense * 0.65 + level * 5 + hero_bonus
    return base * RANK_MULTIPLIER.get(rank, 1.0)


def resolve_fight(attacker_stats: dict, defender_stats: dict) -> dict:
    a_score = combat_score(**attacker_stats) * random.uniform(0.90, 1.10)
    d_score = combat_score(**defender_stats) * random.uniform(0.90, 1.10)
    attacker_wins = a_score >= d_score
    winner_level = attacker_stats["level"] if attacker_wins else defender_stats["level"]
    coins_reward = COIN_REWARD_BASE + winner_level * COIN_REWARD_PER_LEVEL
    return {
        "attacker_wins": attacker_wins,
        "attacker_score": round(a_score, 1),
        "defender_score": round(d_score, 1),
        "coins_reward": coins_reward,
    }


def is_protected(level: int) -> bool:
    return level < BEGINNER_PROTECTION_LEVEL
