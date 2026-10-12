"""Long-run regression for server-authoritative agent physics.

Runs an isolated PyBullet DIRECT world; it never connects to PostgreSQL or a live server.
"""
import json
import math
from simulation import PhysicsWorld


def run():
    world = PhysicsWorld()
    world.add_static("qa:ground", 0, -0.05, 0, 60, 0.1, "box")
    count = 20
    initial = {}
    for i in range(count):
        x = (i % 5) * 2.0 - 4.0
        z = (i // 5) * 2.0 - 3.0
        key = f"qa:agent:{i}"
        world.add_body(key, x, 0.9, z, radius=0.28, mass=1.0, height=1.3)
        vx = 0.65 if i % 2 == 0 else -0.65
        vz = 0.35 if i % 3 == 0 else -0.25
        world.set_velocity(key, vx, vz)
        initial[key] = (x, z)

    # PhysicsWorld.step caps each call at 60 seconds. Chunk calls so the
    # regression really advances 120 simulated seconds (7,200 fixed steps).
    duration = 120.0
    for _ in range(int(duration)):
        world.step(1.0)

    moved = 0
    positions = {}
    issues = []
    for key, (x0, z0) in initial.items():
        pos = world.position(key)
        positions[key] = pos
        if not pos or not all(math.isfinite(v) for v in pos):
            issues.append(f"{key}: missing/non-finite position")
            continue
        x, y, z = pos
        if math.hypot(x - x0, z - z0) > 0.05:
            moved += 1
        if y < 0.20 or y > 2.5:
            issues.append(f"{key}: unexpected vertical position {y:.3f}")
        if abs(x) > 80 or abs(z) > 80:
            issues.append(f"{key}: unbounded horizontal drift")

    result = {
        "ok": not issues and moved >= 18,
        "duration_simulated_seconds": duration,
        "physics_steps": int(duration / world.dt),
        "agents": count,
        "agents_moved": moved,
        "finite_positions": sum(
            1 for pos in positions.values()
            if pos and all(math.isfinite(v) for v in pos)
        ),
        "issues": issues,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
