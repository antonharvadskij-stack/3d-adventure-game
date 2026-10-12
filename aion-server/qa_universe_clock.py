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
    # Load reconciliation: preserve the highest known legacy age.
    _sync_universe_clock(world)
    expected_age = 109_683_315.14
    assert world["worldAge"] == expected_age
    assert world["universeClock"]["simulatedSeconds"] == expected_age
    assert math.isclose(
        world["universeClock"]["simulatedYears"],
        expected_age / (365.25 * 86400),
        rel_tol=1e-12,
    )

    # A forced advance updates the durable clock before tick runs.
    advance = 5.0
    world["universeClock"]["simulatedSeconds"] += advance
    clock_after_advance = world["universeClock"]["simulatedSeconds"]

    # Legacy tick also increments worldAge, which must NOT be counted twice.
    world["worldAge"] += advance
    _sync_universe_clock(world, prefer_world_age=False)
    assert world["worldAge"] == clock_after_advance
    assert world["universeClock"]["simulatedSeconds"] == clock_after_advance

    # Even if the legacy field drifts forward, the durable clock wins post-tick.
    world["worldAge"] += 10.0
    _sync_universe_clock(world, prefer_world_age=False)
    assert world["worldAge"] == clock_after_advance

    # A subsequent load can still reconcile a higher age from an old snapshot.
    world["worldAge"] += 20.0
    _sync_universe_clock(world, prefer_world_age=True)
    assert world["worldAge"] == clock_after_advance + 20.0
    assert world["universeClock"]["simulatedSeconds"] == world["worldAge"]

    print("AION universe-clock QA: PASS (legacy load reconciliation, single time advance, no duplicate tick increment)")


if __name__ == "__main__":
    run()
