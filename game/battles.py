"""
Battle resolution logic.

Combat score = base stats + level/rank scaling + hero bonus + randomness.
Kept purely functional (no DB access) so it's easy to unit test.
"""
import random

from game.ranks import RANKS

RANK_MULTIPLIER = {name: 1.0 + i * 0.05 for i, (_, name) in enumerate(RANKS)}

BEGINNER_PROTECTION_LEVEL = 5
BEGINNER_PROTECTION_LOSS_REDUCTION = 0.5  # losers under this level lose fewer coins

COIN_REWARD_BASE = 40
COIN_REWARD_PER_LEVEL = 5


def combat_score(power: int, defense: int, level: int, rank: str, hero_bonus: int = 0) -> float:
    base = power * 1.2 + defense * 0.8 + level * 5 + hero_bonus
    multiplier = RANK_MULTIPLIER.get(rank, 1.0)
    return base * multiplier


def resolve_fight(attacker_stats: dict, defender_stats: dict) -> dict:
    """
    Each *_stats dict needs: power, defense, level, rank, hero_bonus.
    Returns a dict describing the outcome.
    """
    a_score = combat_score(**attacker_stats) * random.uniform(0.85, 1.15)
    d_score = combat_score(**defender_stats) * random.uniform(0.85, 1.15)

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
