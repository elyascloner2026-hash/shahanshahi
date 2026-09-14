from game.heroes import spawn_hero, RARITY_WEIGHTS


def test_spawn_hero_has_valid_rarity():
    hero = spawn_hero()
    assert hero["rarity"] in RARITY_WEIGHTS
    assert hero["hp"] > 0
    assert hero["power"] > 0


async def test_hero_event_damage_accumulates(test_db):
    event_id = await test_db.create_hero_event("سهراب", hp_max=1000, power=200, rarity="Rare")
    await test_db.ensure_user(3001, "attacker1")
    await test_db.apply_hero_damage(event_id, 3001, 300)
    await test_db.apply_hero_damage(event_id, 3001, 200)

    event = await test_db.get_active_hero_event()
    assert event["hp_current"] == 500

    ranking = await test_db.hero_event_damage_ranking(event_id)
    assert ranking[0]["user_id"] == 3001
    assert ranking[0]["total"] == 500


async def test_hero_reward_on_defeat(test_db):
    event_id = await test_db.create_hero_event("رستم‌زاد", hp_max=100, power=50, rarity="Common")
    await test_db.ensure_user(3002, "winner")
    await test_db.create_character(3002, "پیروز", "مرد", "پارس", "پارسه")

    await test_db.apply_hero_damage(event_id, 3002, 150)
    event = await test_db.get_active_hero_event()
    assert event["hp_current"] == 0

    await test_db.finish_hero_event(event_id)
    finished_event = await test_db.get_active_hero_event()
    assert finished_event is None  # no longer "active"

    await test_db.add_hero(3002, name="رستم‌زاد", rarity="Common", power=50, defense=0, bonus=10)
    heroes = await test_db.get_heroes(3002)
    assert len(heroes) == 1
    assert heroes[0]["name"] == "رستم‌زاد"

    count = await test_db.count_heroes(3002)
    assert count == 1
