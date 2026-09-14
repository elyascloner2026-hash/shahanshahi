"""Gem system: the Shahanshah personally owns the Gem supply and transfers Gems to players."""
from config import ADMIN_IDS

# Coins -> Gems packages. Gems are scarce and are supplied by the admin treasury.
GEM_PACKAGES = {
    1: {"gems": 50, "coins": 5000},
    2: {"gems": 120, "coins": 11000},
    3: {"gems": 300, "coins": 25000},
    4: {"gems": 700, "coins": 50000},
}

ADMIN_GEM_STOCK = 1_000_000_000


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
