"""
Hero event logic: what spawns, and how the winning Hero Card is minted.
"""
import random

HERO_NAMES = ["سهراب", "رستم‌زاد", "آرمین", "کیانوش", "بهرام", "شیدا", "آرش‌وند"]

RARITY_WEIGHTS = {
    "Common": 45,
    "Rare": 30,
    "Epic": 15,
    "Legendary": 8,
    "Mythic": 2,
}

RARITY_HP = {
    "Common": 8000,
    "Rare": 18000,
    "Epic": 35000,
    "Legendary": 50000,
    "Mythic": 80000,
}

RARITY_POWER = {
    "Common": 600,
    "Rare": 1200,
    "Epic": 1800,
    "Legendary": 2400,
    "Mythic": 3200,
}

RARITY_BONUS = {
    "Common": 10,
    "Rare": 25,
    "Epic": 45,
    "Legendary": 70,
    "Mythic": 110,
}

RARITY_EMOJI = {
    "Common": "⚪",
    "Rare": "🔵",
    "Epic": "🟣",
    "Legendary": "⭐",
    "Mythic": "🌟",
}


def roll_rarity() -> str:
    names = list(RARITY_WEIGHTS.keys())
    weights = list(RARITY_WEIGHTS.values())
    return random.choices(names, weights=weights, k=1)[0]


def spawn_hero() -> dict:
    rarity = roll_rarity()
    name = random.choice(HERO_NAMES)
    return {
        "name": name,
        "rarity": rarity,
        "hp": RARITY_HP[rarity],
        "power": RARITY_POWER[rarity],
        "bonus": RARITY_BONUS[rarity],
    }


CONSOLATION_COINS = 50
CONSOLATION_XP = 15
WINNER_COINS = 500
WINNER_XP = 200
