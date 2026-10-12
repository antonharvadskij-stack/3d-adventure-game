"""Regression checks for AION's persistent universe clock."""
import math
from autonomy import _sync_universe_clock


def run():
    world = {
        "worldAge": 109_683_315.14,
        "universeClock": {
            "simulatedSeconds": 109_509_851.68,
            "simulatedYears": 0,
            "rate": "legacy",
        },
    }
    _sync_universe_clock(world)
    assert world["worldAge"] == 109_683_315.14
    assert world["universeClock"]["simulatedSeconds"] == world["worldAge"]
    assert math.isclose(
        world["universeClock"]["simulatedYears"],
        world["worldAge"] / (365.25 * 86400),
        rel_tol=1e-12,
    )

    # If an older tick implementation increments worldAge without updating
    # the clock, reconciliation must preserve the higher observed age.
    world["worldAge"] += 5.0
    _sync_universe_clock(world)
    assert world["universeClock"]["simulatedSeconds"] == world["worldAge"]

    # A clock already ahead of worldAge must never be moved backwards.
    world["worldAge"] -= 10.0
    _sync_universe_clock(world)
    assert world["worldAge"] == world["universeClock"]["simulatedSeconds"]
    assert world["worldAge"] >= 109_683_320.14

    print("AION universe-clock QA: PASS (monotonic high-water mark, years conversion, legacy drift reconciliation)")


if __name__ == "__main__":
    run()
