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
