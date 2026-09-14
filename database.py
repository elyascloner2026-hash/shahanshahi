"""
Database layer for Shahanshahi.

Uses aiosqlite for async access. All queries use parameter binding
(never string-formatted SQL) to prevent SQL injection. Schema is kept
close to plain SQL so migrating to PostgreSQL later only requires
swapping the driver and a few type tweaks (INTEGER PK -> SERIAL, etc).
"""
import time
import aiosqlite
from contextlib import asynccontextmanager

from config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    joined_at INTEGER NOT NULL,
    is_banned INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS characters (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id),
    name TEXT NOT NULL,
    gender TEXT NOT NULL,
    territory TEXT NOT NULL,
    city TEXT NOT NULL,
    rank TEXT NOT NULL DEFAULT 'دهقان',
    level INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    coins INTEGER NOT NULL DEFAULT 500,
    gems INTEGER NOT NULL DEFAULT 0,
    power INTEGER NOT NULL DEFAULT 100,
    defense INTEGER NOT NULL DEFAULT 100,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    last_fight_at INTEGER NOT NULL DEFAULT 0,
    heal_1_used_at INTEGER NOT NULL DEFAULT 0,
    heal_2_used_at INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS territories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    emoji TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    territory_name TEXT NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    emoji TEXT NOT NULL,
    price INTEGER NOT NULL,
    power_bonus INTEGER NOT NULL DEFAULT 0,
    defense_bonus INTEGER NOT NULL DEFAULT 0,
    item_type TEXT NOT NULL DEFAULT 'equipment'
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    item_id INTEGER NOT NULL REFERENCES items(id),
    quantity INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS army_units (
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    unit_code TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    max_quantity INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, unit_code)
);

CREATE TABLE IF NOT EXISTS gem_economy_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS premium_unlocks (
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    code TEXT NOT NULL,
    unlocked_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, code)
);

CREATE TABLE IF NOT EXISTS heroes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    name TEXT NOT NULL,
    rarity TEXT NOT NULL,
    power INTEGER NOT NULL,
    defense INTEGER NOT NULL,
    bonus INTEGER NOT NULL,
    obtained_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS hero_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    hp_max INTEGER NOT NULL,
    hp_current INTEGER NOT NULL,
    power INTEGER NOT NULL,
    rarity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at INTEGER NOT NULL,
    finished_at INTEGER
);

CREATE TABLE IF NOT EXISTS hero_damage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES hero_events(id),
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    damage INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attacker_id INTEGER NOT NULL REFERENCES users(user_id),
    defender_id INTEGER NOT NULL REFERENCES users(user_id),
    winner_id INTEGER NOT NULL REFERENCES users(user_id),
    coins_reward INTEGER NOT NULL,
    xp_reward INTEGER NOT NULL,
    chat_id INTEGER,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS group_settings (
    chat_id INTEGER PRIMARY KEY,
    title TEXT,
    fight_enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS group_battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    battle_id INTEGER NOT NULL REFERENCES battles(id),
    chat_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    quest_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    choices_json TEXT NOT NULL,
    reward_coins INTEGER NOT NULL,
    reward_xp INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS quest_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    quest_id INTEGER NOT NULL REFERENCES quests(id),
    status TEXT NOT NULL DEFAULT 'completed',
    choice TEXT,
    completed_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    admin_id INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    target_user_id INTEGER,
    details TEXT,
    created_at INTEGER NOT NULL
);
"""

TERRITORIES = [
    ("پارس", "🏛"),
    ("ماد", "🛡"),
    ("پارت", "🐎"),
    ("ایلام", "🌾"),
    ("باختر", "⚔️"),
    ("سغد", "🏔"),
    ("خوارزم", "🌊"),
    ("ارمنستان", "🏰"),
]

DEFAULT_ITEMS = [
    ("شمشیر", "⚔️", 300, 25, 0, "equipment"),
    ("سپر", "🛡", 300, 0, 25, "equipment"),
    ("کمان", "🏹", 450, 35, 0, "equipment"),
]


class Database:
    """Thin async wrapper around a single shared SQLite connection."""

    def __init__(self, path: str = DATABASE_PATH):
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self):
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON;")
        await self._conn.executescript(SCHEMA)
        # Safe migrations for existing SQLite databases.
        for stmt in (
            "ALTER TABLE characters ADD COLUMN heal_1_used_at INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE characters ADD COLUMN heal_2_used_at INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE characters ADD COLUMN gems INTEGER NOT NULL DEFAULT 0",
        ):
            try:
                await self._conn.execute(stmt)
            except aiosqlite.OperationalError:
                pass
        # One-time Gem economy migration: old builds may have granted starter Gems.
        # Wipe player Gems once, then seed the admin treasury only.
        from config import ADMIN_IDS
        cur = await self._conn.execute("SELECT value FROM gem_economy_meta WHERE key = 'initialized'")
        marker = await cur.fetchone()
        if not marker:
            if ADMIN_IDS:
                placeholders = ",".join("?" for _ in ADMIN_IDS)
                await self._conn.execute(
                    f"UPDATE characters SET gems = 0 WHERE user_id NOT IN ({placeholders})",
                    tuple(ADMIN_IDS),
                )
                await self._conn.execute(
                    f"UPDATE characters SET gems = 1000000000 WHERE user_id IN ({placeholders})",
                    tuple(ADMIN_IDS),
                )
            else:
                await self._conn.execute("UPDATE characters SET gems = 0")
            await self._conn.execute(
                "INSERT INTO gem_economy_meta(key, value) VALUES('initialized', '1')"
            )
        await self._conn.commit()
        await self._seed_defaults()

    async def close(self):
        if self._conn:
            await self._conn.close()

    async def _seed_defaults(self):
        cur = await self._conn.execute("SELECT COUNT(*) as c FROM territories")
        row = await cur.fetchone()
        if row["c"] == 0:
            await self._conn.executemany(
                "INSERT INTO territories (name, emoji) VALUES (?, ?)", TERRITORIES
            )
        cur = await self._conn.execute("SELECT COUNT(*) as c FROM items")
        row = await cur.fetchone()
        if row["c"] == 0:
            await self._conn.executemany(
                "INSERT INTO items (name, emoji, price, power_bonus, defense_bonus, item_type) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                DEFAULT_ITEMS,
            )
        await self._conn.commit()

    @asynccontextmanager
    async def tx(self):
        """Context manager that commits on success, rolls back on error."""
        try:
            yield self._conn
            await self._conn.commit()
        except Exception:
            await self._conn.rollback()
            raise

    # ---------- users / characters ----------

    async def ensure_user(self, user_id: int, username: str | None):
        await self._conn.execute(
            "INSERT INTO users (user_id, username, joined_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username",
            (user_id, username, int(time.time())),
        )
        await self._conn.commit()

    async def is_banned(self, user_id: int) -> bool:
        cur = await self._conn.execute(
            "SELECT is_banned FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
        return bool(row["is_banned"]) if row else False

    async def set_banned(self, user_id: int, banned: bool):
        await self._conn.execute(
            "UPDATE users SET is_banned = ? WHERE user_id = ?", (int(banned), user_id)
        )
        await self._conn.commit()

    async def get_character(self, user_id: int):
        cur = await self._conn.execute(
            "SELECT * FROM characters WHERE user_id = ?", (user_id,)
        )
        return await cur.fetchone()

    async def create_character(self, user_id, name, gender, territory, city):
        await self._conn.execute(
            "INSERT INTO characters (user_id, name, gender, territory, city, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, gender, territory, city, int(time.time())),
        )
        await self._conn.commit()
        # Admin is the only account that receives the initial Gem treasury.
        from config import ADMIN_IDS
        if user_id in ADMIN_IDS:
            await self._conn.execute(
                "UPDATE characters SET gems = 1000000000 WHERE user_id = ?", (user_id,)
            )
            await self._conn.commit()
        # A new player starts with a small basic army.
        await self._conn.executemany(
            "INSERT OR IGNORE INTO army_units (user_id, unit_code, quantity, max_quantity) VALUES (?, ?, ?, ?)",
            [(user_id, "archer_1", 10, 10), (user_id, "swordsman_1", 10, 10)],
        )
        await self._conn.commit()

    async def update_character(self, user_id: int, **fields):
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [user_id]
        await self._conn.execute(
            f"UPDATE characters SET {cols} WHERE user_id = ?", values
        )
        await self._conn.commit()

    async def list_territories(self):
        cur = await self._conn.execute("SELECT * FROM territories ORDER BY id")
        return await cur.fetchall()

    async def list_cities(self, territory_name: str):
        cur = await self._conn.execute(
            "SELECT * FROM cities WHERE territory_name = ? ORDER BY id",
            (territory_name,),
        )
        return await cur.fetchall()

    # ---------- economy ----------

    async def add_coins(self, user_id: int, amount: int, reason: str):
        await self._conn.execute(
            "UPDATE characters SET coins = MAX(0, coins + ?) WHERE user_id = ?",
            (amount, user_id),
        )
        await self._conn.execute(
            "INSERT INTO transactions (user_id, amount, reason, created_at) VALUES (?, ?, ?, ?)",
            (user_id, amount, reason, int(time.time())),
        )
        await self._conn.commit()

    async def add_xp(self, user_id: int, amount: int):
        await self._conn.execute(
            "UPDATE characters SET xp = xp + ? WHERE user_id = ?", (amount, user_id)
        )
        await self._conn.commit()

    async def add_gems(self, user_id: int, amount: int, reason: str = "unknown"):
        await self._conn.execute(
            "UPDATE characters SET gems = MAX(0, gems + ?) WHERE user_id = ?", (amount, user_id)
        )
        await self._conn.commit()

    async def spend_gems(self, user_id: int, amount: int) -> bool:
        cur = await self._conn.execute(
            "UPDATE characters SET gems = gems - ? WHERE user_id = ? AND gems >= ?",
            (amount, user_id, amount),
        )
        await self._conn.commit()
        return cur.rowcount == 1

    async def buy_gems_from_admin(self, buyer_id: int, admin_id: int, gems: int, coin_price: int) -> bool:
        """Atomically move Coins from buyer to admin and Gems from admin to buyer."""
        if buyer_id == admin_id or gems <= 0 or coin_price <= 0:
            return False
        cur = await self._conn.execute(
            "UPDATE characters SET coins = coins - ? WHERE user_id = ? AND coins >= ?",
            (coin_price, buyer_id, coin_price),
        )
        if cur.rowcount != 1:
            await self._conn.rollback()
            return False
        cur = await self._conn.execute(
            "UPDATE characters SET gems = gems - ? WHERE user_id = ? AND gems >= ?",
            (gems, admin_id, gems),
        )
        if cur.rowcount != 1:
            await self._conn.rollback()
            return False
        await self._conn.execute(
            "UPDATE characters SET gems = gems + ? WHERE user_id = ?", (gems, buyer_id)
        )
        await self._conn.execute(
            "UPDATE characters SET coins = coins + ? WHERE user_id = ?", (coin_price, admin_id)
        )
        await self._conn.execute(
            "INSERT INTO transactions (user_id, amount, reason, created_at) VALUES (?, ?, ?, ?)",
            (buyer_id, -coin_price, "gem_purchase", int(time.time())),
        )
        await self._conn.execute(
            "INSERT INTO transactions (user_id, amount, reason, created_at) VALUES (?, ?, ?, ?)",
            (admin_id, coin_price, "gem_sale", int(time.time())),
        )
        await self._conn.commit()
        return True

    async def transfer_gems(self, sender_id: int, receiver_id: int, amount: int) -> bool:
        """Atomically transfer Gems between two existing characters."""
        if sender_id == receiver_id or amount <= 0:
            return False
        cur = await self._conn.execute(
            "UPDATE characters SET gems = gems - ? WHERE user_id = ? AND gems >= ?",
            (amount, sender_id, amount),
        )
        if cur.rowcount != 1:
            await self._conn.rollback()
            return False
        cur = await self._conn.execute(
            "UPDATE characters SET gems = gems + ? WHERE user_id = ?",
            (amount, receiver_id),
        )
        if cur.rowcount != 1:
            await self._conn.rollback()
            return False
        now = int(time.time())
        await self._conn.execute(
            "INSERT INTO transactions (user_id, amount, reason, created_at) VALUES (?, ?, ?, ?)",
            (sender_id, -amount, "gem_transfer_out", now),
        )
        await self._conn.execute(
            "INSERT INTO transactions (user_id, amount, reason, created_at) VALUES (?, ?, ?, ?)",
            (receiver_id, amount, "gem_transfer_in", now),
        )
        await self._conn.commit()
        return True

    async def has_premium(self, user_id: int, code: str) -> bool:
        cur = await self._conn.execute(
            "SELECT 1 FROM premium_unlocks WHERE user_id = ? AND code = ?", (user_id, code)
        )
        return await cur.fetchone() is not None

    async def unlock_premium(self, user_id: int, code: str, price: int) -> bool:
        cur = await self._conn.execute(
            "SELECT 1 FROM premium_unlocks WHERE user_id = ? AND code = ?", (user_id, code)
        )
        if await cur.fetchone():
            return False
        cur = await self._conn.execute(
            "UPDATE characters SET gems = gems - ? WHERE user_id = ? AND gems >= ?",
            (price, user_id, price),
        )
        if cur.rowcount != 1:
            await self._conn.rollback()
            return False
        await self._conn.execute(
            "INSERT INTO premium_unlocks (user_id, code, unlocked_at) VALUES (?, ?, ?)",
            (user_id, code, int(time.time())),
        )
        await self._conn.commit()
        return True

    async def get_premium(self, user_id: int):
        cur = await self._conn.execute(
            "SELECT code FROM premium_unlocks WHERE user_id = ? ORDER BY code", (user_id,)
        )
        return [r["code"] for r in await cur.fetchall()]

    # ---------- items / inventory ----------

    async def list_items(self):
        cur = await self._conn.execute("SELECT * FROM items ORDER BY id")
        return await cur.fetchall()

    async def get_item(self, item_id: int):
        cur = await self._conn.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        return await cur.fetchone()

    async def add_inventory_item(self, user_id: int, item_id: int):
        cur = await self._conn.execute(
            "SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?",
            (user_id, item_id),
        )
        row = await cur.fetchone()
        if row:
            await self._conn.execute(
                "UPDATE inventory SET quantity = quantity + 1 WHERE id = ?", (row["id"],)
            )
        else:
            await self._conn.execute(
                "INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, 1)",
                (user_id, item_id),
            )
        await self._conn.commit()

    async def get_inventory(self, user_id: int):
        cur = await self._conn.execute(
            "SELECT inventory.quantity, items.* FROM inventory "
            "JOIN items ON items.id = inventory.item_id WHERE inventory.user_id = ?",
            (user_id,),
        )
        return await cur.fetchall()

    # ---------- army ----------
    async def get_army(self, user_id: int):
        cur = await self._conn.execute(
            "SELECT * FROM army_units WHERE user_id = ? AND quantity > 0 ORDER BY unit_code", (user_id,)
        )
        return await cur.fetchall()

    async def get_all_army(self, user_id: int):
        cur = await self._conn.execute(
            "SELECT * FROM army_units WHERE user_id = ? ORDER BY unit_code", (user_id,)
        )
        return await cur.fetchall()

    async def add_units(self, user_id: int, unit_code: str, amount: int):
        await self._conn.execute(
            "INSERT INTO army_units (user_id, unit_code, quantity, max_quantity) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, unit_code) DO UPDATE SET quantity = quantity + excluded.quantity, max_quantity = MAX(max_quantity, quantity + excluded.quantity)",
            (user_id, unit_code, amount, amount),
        )
        await self._conn.commit()

    async def set_units(self, user_id: int, unit_code: str, amount: int):
        await self._conn.execute(
            "INSERT INTO army_units (user_id, unit_code, quantity, max_quantity) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, unit_code) DO UPDATE SET quantity = MAX(0, excluded.quantity), max_quantity = MAX(max_quantity, excluded.quantity)",
            (user_id, unit_code, max(0, amount), max(0, amount)),
        )
        await self._conn.commit()

    async def lose_army(self, user_id: int, ratio: float):
        rows = await self.get_all_army(user_id)
        for row in rows:
            qty = row["quantity"]
            if qty <= 0:
                continue
            lost = max(1, int(round(qty * ratio)))
            await self._conn.execute(
                "UPDATE army_units SET quantity = MAX(0, quantity - ?) WHERE user_id = ? AND unit_code = ?",
                (lost, user_id, row["unit_code"]),
            )
        await self._conn.commit()
        return await self.get_all_army(user_id)

    async def heal_army(self, user_id: int):
        await self._conn.execute(
            "UPDATE army_units SET quantity = max_quantity WHERE user_id = ?", (user_id,)
        )
        await self._conn.commit()
        return await self.get_all_army(user_id)

    async def get_heal_slots(self, user_id: int):
        cur = await self._conn.execute(
            "SELECT heal_1_used_at, heal_2_used_at FROM characters WHERE user_id = ?", (user_id,)
        )
        return await cur.fetchone()

    async def use_heal_slot(self, user_id: int, slot: int, now: int):
        col = "heal_1_used_at" if slot == 1 else "heal_2_used_at"
        await self._conn.execute(f"UPDATE characters SET {col} = ? WHERE user_id = ?", (now, user_id))
        await self._conn.commit()

    async def get_heroes(self, user_id: int):
        cur = await self._conn.execute(
            "SELECT * FROM heroes WHERE user_id = ? ORDER BY id DESC", (user_id,)
        )
        return await cur.fetchall()

    async def count_heroes(self, user_id: int) -> int:
        cur = await self._conn.execute(
            "SELECT COUNT(*) as c FROM heroes WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
        return row["c"]

    async def add_hero(self, user_id, name, rarity, power, defense, bonus):
        await self._conn.execute(
            "INSERT INTO heroes (user_id, name, rarity, power, defense, bonus, obtained_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, rarity, power, defense, bonus, int(time.time())),
        )
        await self._conn.commit()

    # ---------- battles ----------

    async def record_battle(self, attacker_id, defender_id, winner_id, coins_reward, xp_reward, chat_id=None):
        cur = await self._conn.execute(
            "INSERT INTO battles (attacker_id, defender_id, winner_id, coins_reward, xp_reward, chat_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (attacker_id, defender_id, winner_id, coins_reward, xp_reward, chat_id, int(time.time())),
        )
        battle_id = cur.lastrowid
        if chat_id is not None:
            await self._conn.execute(
                "INSERT INTO group_battles (battle_id, chat_id) VALUES (?, ?)",
                (battle_id, chat_id),
            )
        await self._conn.commit()
        return battle_id

    async def set_last_fight(self, user_id: int, ts: int):
        await self._conn.execute(
            "UPDATE characters SET last_fight_at = ? WHERE user_id = ?", (ts, user_id)
        )
        await self._conn.commit()

    async def group_leaderboard(self, chat_id: int, limit: int = 10):
        cur = await self._conn.execute(
            """
            SELECT c.name, c.user_id,
                SUM(CASE WHEN b.winner_id = c.user_id THEN 1 ELSE 0 END) as wins,
                COUNT(*) as total
            FROM group_battles gb
            JOIN battles b ON b.id = gb.battle_id
            JOIN characters c ON c.user_id IN (b.attacker_id, b.defender_id)
            WHERE gb.chat_id = ?
            GROUP BY c.user_id
            ORDER BY wins DESC
            LIMIT ?
            """,
            (chat_id, limit),
        )
        return await cur.fetchall()

    async def group_stats(self, chat_id: int, user_id: int):
        cur = await self._conn.execute(
            """
            SELECT
                SUM(CASE WHEN b.winner_id = ? THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN b.winner_id != ? THEN 1 ELSE 0 END) as losses,
                COUNT(*) as total
            FROM group_battles gb
            JOIN battles b ON b.id = gb.battle_id
            WHERE gb.chat_id = ? AND (b.attacker_id = ? OR b.defender_id = ?)
            """,
            (user_id, user_id, chat_id, user_id, user_id),
        )
        return await cur.fetchone()

    # ---------- leaderboards (global) ----------

    async def leaderboard(self, order_by: str, limit: int = 10):
        allowed = {
            "level": "level DESC, xp DESC",
            "power": "power DESC",
            "coins": "coins DESC",
            "wins": "wins DESC",
        }
        order = allowed.get(order_by, "level DESC")
        cur = await self._conn.execute(
            f"SELECT name, territory, level, power, coins, wins FROM characters "
            f"ORDER BY {order} LIMIT ?",
            (limit,),
        )
        return await cur.fetchall()

    # ---------- group settings ----------

    async def list_groups(self):
        cur = await self._conn.execute("SELECT chat_id, title FROM group_settings ORDER BY chat_id")
        return await cur.fetchall()

    async def ensure_group(self, chat_id: int, title: str | None):
        await self._conn.execute(
            "INSERT INTO group_settings (chat_id, title) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title",
            (chat_id, title),
        )
        await self._conn.commit()

    # ---------- hero events ----------

    async def get_active_hero_event(self):
        cur = await self._conn.execute(
            "SELECT * FROM hero_events WHERE status = 'active' ORDER BY id DESC LIMIT 1"
        )
        return await cur.fetchone()

    async def create_hero_event(self, name, hp_max, power, rarity):
        cur = await self._conn.execute(
            "INSERT INTO hero_events (name, hp_max, hp_current, power, rarity, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, hp_max, hp_max, power, rarity, int(time.time())),
        )
        await self._conn.commit()
        return cur.lastrowid

    async def apply_hero_damage(self, event_id: int, user_id: int, damage: int):
        await self._conn.execute(
            "INSERT INTO hero_damage (event_id, user_id, damage, created_at) VALUES (?, ?, ?, ?)",
            (event_id, user_id, damage, int(time.time())),
        )
        await self._conn.execute(
            "UPDATE hero_events SET hp_current = MAX(0, hp_current - ?) WHERE id = ?",
            (damage, event_id),
        )
        await self._conn.commit()

    async def finish_hero_event(self, event_id: int):
        await self._conn.execute(
            "UPDATE hero_events SET status = 'finished', finished_at = ? WHERE id = ?",
            (int(time.time()), event_id),
        )
        await self._conn.commit()

    async def hero_event_damage_ranking(self, event_id: int):
        cur = await self._conn.execute(
            "SELECT user_id, SUM(damage) as total FROM hero_damage WHERE event_id = ? "
            "GROUP BY user_id ORDER BY total DESC",
            (event_id,),
        )
        return await cur.fetchall()

    # ---------- quests ----------

    async def get_quest(self, code: str):
        cur = await self._conn.execute("SELECT * FROM quests WHERE code = ?", (code,))
        return await cur.fetchone()

    async def upsert_quest(self, code, quest_type, title, description, choices_json, reward_coins, reward_xp):
        await self._conn.execute(
            "INSERT INTO quests (code, quest_type, title, description, choices_json, reward_coins, reward_xp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(code) DO NOTHING",
            (code, quest_type, title, description, choices_json, reward_coins, reward_xp),
        )
        await self._conn.commit()

    async def has_completed_quest_today(self, user_id: int, quest_id: int) -> bool:
        day_start = int(time.time()) - 86400
        cur = await self._conn.execute(
            "SELECT COUNT(*) as c FROM quest_progress WHERE user_id = ? AND quest_id = ? AND completed_at > ?",
            (user_id, quest_id, day_start),
        )
        row = await cur.fetchone()
        return row["c"] > 0

    async def has_completed_quest_ever(self, user_id: int, quest_id: int) -> bool:
        cur = await self._conn.execute(
            "SELECT COUNT(*) as c FROM quest_progress WHERE user_id = ? AND quest_id = ?",
            (user_id, quest_id),
        )
        row = await cur.fetchone()
        return row["c"] > 0

    async def complete_quest(self, user_id: int, quest_id: int, choice: str):
        await self._conn.execute(
            "INSERT INTO quest_progress (user_id, quest_id, status, choice, completed_at) "
            "VALUES (?, ?, 'completed', ?, ?)",
            (user_id, quest_id, choice, int(time.time())),
        )
        await self._conn.commit()

    # ---------- news ----------

    async def add_news(self, title: str, content: str, admin_id: int):
        await self._conn.execute(
            "INSERT INTO news (title, content, admin_id, created_at) VALUES (?, ?, ?, ?)",
            (title, content, admin_id, int(time.time())),
        )
        await self._conn.commit()

    async def latest_news(self, limit: int = 5):
        cur = await self._conn.execute(
            "SELECT * FROM news ORDER BY id DESC LIMIT ?", (limit,)
        )
        return await cur.fetchall()

    # ---------- admin ----------

    async def log_admin_action(self, admin_id: int, action: str, target_user_id=None, details=None):
        await self._conn.execute(
            "INSERT INTO admin_logs (admin_id, action, target_user_id, details, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (admin_id, action, target_user_id, details, int(time.time())),
        )
        await self._conn.commit()

    async def all_user_ids(self):
        cur = await self._conn.execute("SELECT user_id FROM users WHERE is_banned = 0")
        rows = await cur.fetchall()
        return [r["user_id"] for r in rows]

    async def stats_summary(self):
        cur = await self._conn.execute("SELECT COUNT(*) as c FROM users")
        users_count = (await cur.fetchone())["c"]
        cur = await self._conn.execute("SELECT COUNT(*) as c FROM characters")
        chars_count = (await cur.fetchone())["c"]
        cur = await self._conn.execute("SELECT COUNT(*) as c FROM battles")
        battles_count = (await cur.fetchone())["c"]
        cur = await self._conn.execute("SELECT COUNT(*) as c FROM heroes")
        heroes_count = (await cur.fetchone())["c"]
        return {
            "users": users_count,
            "characters": chars_count,
            "battles": battles_count,
            "heroes": heroes_count,
        }


db = Database()
