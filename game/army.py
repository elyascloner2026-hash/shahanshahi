"""Army units and combat calculations. 15 upgrade levels per unit."""
from dataclasses import dataclass

@dataclass(frozen=True)
class UnitType:
    code: str
    name: str
    emoji: str
    level: int
    power: int
    defense: int
    price: int

UNIT_FAMILIES = {
    "archer": ("کماندار", "🏹", 35, 8, 250),
    "swordsman": ("شمشیرزن", "⚔️", 28, 28, 250),
    "guard": ("نگهبان", "🛡", 15, 45, 300),
}

# Each family has 15 levels. Higher levels are substantially stronger and cost more.
UNITS = {}
for family, (name, emoji, base_power, base_defense, base_price) in UNIT_FAMILIES.items():
    for level in range(1, 16):
        multiplier = 1.0 + (level - 1) * 0.38
        price_multiplier = 1.0 + (level - 1) * 0.62
        UNITS[f"{family}_{level}"] = UnitType(
            code=f"{family}_{level}",
            name=f"{name} سطح {level}",
            emoji=emoji,
            level=level,
            power=max(1, round(base_power * multiplier)),
            defense=max(1, round(base_defense * multiplier)),
            price=max(1, round(base_price * price_multiplier)),
        )


def army_strength(units) -> dict:
    power = defense = 0
    total = 0
    for row in units:
        u = UNITS.get(row["unit_code"])
        if not u:
            continue
        count = int(row["quantity"])
        total += count
        power += u.power * count
        defense += u.defense * count
    return {"power": power, "defense": defense, "total": total}
