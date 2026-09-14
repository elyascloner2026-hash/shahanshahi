import pytest


async def test_user_creation(test_db):
    await test_db.ensure_user(1001, "sohrab")
    assert await test_db.is_banned(1001) is False


async def test_character_creation(test_db):
    await test_db.ensure_user(1002, "arash")
    await test_db.create_character(1002, "آرش", "مرد", "پارس", "پارسه")
    char = await test_db.get_character(1002)
    assert char is not None
    assert char["name"] == "آرش"
    assert char["territory"] == "پارس"
    assert char["coins"] == 500  # starting coins


async def test_coins_never_go_negative(test_db):
    await test_db.ensure_user(1003, "u")
    await test_db.create_character(1003, "کاوه", "مرد", "پارس", "پارسه")
    await test_db.add_coins(1003, -999999, "test_drain")
    char = await test_db.get_character(1003)
    assert char["coins"] == 0


async def test_xp_accumulates(test_db):
    await test_db.ensure_user(1004, "u")
    await test_db.create_character(1004, "بهرام", "مرد", "ماد", "همدان")
    await test_db.add_xp(1004, 50)
    await test_db.add_xp(1004, 25)
    char = await test_db.get_character(1004)
    assert char["xp"] == 75


async def test_ban_unban(test_db):
    await test_db.ensure_user(1005, "u")
    await test_db.set_banned(1005, True)
    assert await test_db.is_banned(1005) is True
    await test_db.set_banned(1005, False)
    assert await test_db.is_banned(1005) is False
