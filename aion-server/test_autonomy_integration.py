from autonomy import cycle

def test_autonomy_cycle_keeps_world_bounded():
    world={
        "population":[{"name":"A"}],
        "settlements":[{"name":"Home"}],
        "economy":{"food":100,"water":100},
        "society":{"stability":1},
        "evolution":{"birthRate":1,"settlementRate":1,"resourceAbundance":1},
        "aiPolicy":{"focus":"survival"},
    }
    result, meta=cycle(world, {})
    assert len(result["population"]) <= 100000
    assert len(result["settlements"]) <= 1000
    assert meta["accepted"] is True


def test_self_development_creates_and_sandboxes_module():
    from autonomy import self_develop
    world={
        "population":[{"name":"A"}]*4,
        "settlements":[{"name":"Home"}],
        "economy":{"food":100,"water":100,"wood":60,"stone":30,"knowledge":0},
        "society":{"stability":1},
        "evolution":{"birthRate":1,"settlementRate":1,"resourceAbundance":1,"terrainScale":1,"fogDistance":90},
    }
    ok,module=self_develop(world)
    assert ok is True
    sd=world["aiDiagnostics"]["selfDevelopment"]
    assert sd["version"]==1
    assert sd["accepted"]==1
    assert sd["modules"][0]["autonomous"] is True
    assert "sandboxTest" in sd["modules"][0]
    assert world["evolution"]["selfCodeVersion"]==1


def test_self_create_mechanic():
    from autonomy import self_create_mechanic
    world={
        "population":[{"name":"A"}]*4,
        "settlements":[{"name":"Home"}],
        "economy":{"food":100,"water":100,"wood":60,"stone":30,"knowledge":0},
        "society":{"stability":1},
        "evolution":{"resourceAbundance":1,"terrainScale":1,"fogDistance":90},
    }
    ok,mechanic=self_create_mechanic(world)
    assert ok is True
    assert mechanic["autonomous"] is True
    assert mechanic["sandboxTest"]["after"] >= mechanic["sandboxTest"]["before"]
    assert world["aiDiagnostics"]["mechanics"][0]["name"] == "seasonal_adaptation"
