import time

from utils.helpers import cooldown_remaining, is_admin


def test_cooldown_active_right_after_fight():
    remaining = cooldown_remaining(int(time.time()), 300)
    assert remaining > 290


def test_cooldown_expired_after_enough_time():
    remaining = cooldown_remaining(int(time.time()) - 400, 300)
    assert remaining == 0


def test_admin_permission_checks_env_configured_ids():
    assert is_admin(7224258053) is True
    assert is_admin(999999999) is False


async def test_battle_recorded_and_stats_updated(test_db):
    await test_db.ensure_user(2001, "a")
    await test_db.ensure_user(2002, "b")
    await test_db.create_character(2001, "الف", "مرد", "پارس", "پارسه")
    await test_db.create_character(2002, "ب", "زن", "ماد", "همدان")

    battle_id = await test_db.record_battle(
        attacker_id=2001, defender_id=2002, winner_id=2001,
        coins_reward=50, xp_reward=40, chat_id=None,
    )
    assert battle_id is not None

    await test_db.update_character(2001, wins=1)
    await test_db.update_character(2002, losses=1)

    winner = await test_db.get_character(2001)
    loser = await test_db.get_character(2002)
    assert winner["wins"] == 1
    assert loser["losses"] == 1


async def test_group_fight_recorded_with_chat_id(test_db):
    await test_db.ensure_user(2003, "c")
    await test_db.ensure_user(2004, "d")
    await test_db.create_character(2003, "سام", "مرد", "پارت", "نسا")
    await test_db.create_character(2004, "دارا", "مرد", "سغد", "سمرقند")

    chat_id = -100123456789
    await test_db.ensure_group(chat_id, "Test Group")
    await test_db.record_battle(
        attacker_id=2003, defender_id=2004, winner_id=2003,
        coins_reward=50, xp_reward=40, chat_id=chat_id,
    )

    leaderboard = await test_db.group_leaderboard(chat_id)
    names = [row["name"] for row in leaderboard]
    assert "سام" in names

    stats = await test_db.group_stats(chat_id, 2003)
    assert stats["wins"] == 1
