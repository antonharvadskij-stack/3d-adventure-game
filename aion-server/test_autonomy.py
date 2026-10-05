from autonomy import cycle, validate

def base():
    return {
        "population":[{"name":"A"}]*4,
        "settlements":[{"name":"Home"}],
        "economy":{"food":100,"water":100},
        "society":{"stability":1},
        "evolution":{"birthRate":1,"settlementRate":1,"resourceAbundance":1},
        "aiPolicy":{"focus":"survival"},
    }

def test_repair_candidate_is_bounded():
    w=base()
    candidate,result=cycle(w,{"resource_pressure":True})
    assert validate(w,candidate)
    assert result["accepted"] is True

def test_bad_population_is_rejected():
    w=base()
    bad=dict(w)
    bad["population"]=[{"name":"x"}]*100001
    assert validate(w,bad) is False
