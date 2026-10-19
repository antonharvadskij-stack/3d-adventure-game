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

    # Sample every 0.25 simulated seconds (15 fixed steps), not just at
    # the end. This catches sustained interpenetration and speed spikes.
    duration = 120.0
    sample_seconds = 0.25
    samples = int(duration / sample_seconds)
    issues = []
    max_horizontal_speed = 0.0
    max_penetration = 0.0
    overlap_samples = 0
    positions = {}

    for sample in range(samples):
        world.step(sample_seconds)
        current = {}
        for key in initial:
            bid = world.bodies.get(key)
            if bid is None:
                issues.append(f"sample {sample}: missing body {key}")
                continue
            pos = world.position(key)
            current[key] = pos
            if not pos or not all(math.isfinite(v) for v in pos):
                issues.append(f"sample {sample}: {key} has non-finite position")
                continue
            import pybullet as p
            velocity = p.getBaseVelocity(bid, physicsClientId=world.client)[0]
            horizontal_speed = math.hypot(velocity[0], velocity[2])
            max_horizontal_speed = max(max_horizontal_speed, horizontal_speed)
            if horizontal_speed > 2.21:
                issues.append(
                    f"sample {sample}: {key} horizontal speed {horizontal_speed:.3f} exceeds 2.21"
                )
            x, y, z = pos
            if y < 0.20 or y > 2.5:
                issues.append(f"sample {sample}: {key} unexpected vertical position {y:.3f}")
            if abs(x) > 80 or abs(z) > 80:
                issues.append(f"sample {sample}: {key} unbounded horizontal drift")

        keys = list(current)
        for i, key_a in enumerate(keys):
            a = current[key_a]
            if not a or not all(math.isfinite(v) for v in a):
                continue
            for key_b in keys[i + 1:]:
                b = current[key_b]
                if not b or not all(math.isfinite(v) for v in b):
                    continue
                # The convex agent hulls are centered on their base transforms.
                vertical_overlap = a[1] < b[1] + 1.3 and b[1] < a[1] + 1.3
                horizontal_distance = math.hypot(a[0] - b[0], a[2] - b[2])
                penetration = 0.56 - horizontal_distance
                if vertical_overlap and penetration > 0.12:
                    max_penetration = max(max_penetration, penetration)
                    overlap_samples += 1
                    if overlap_samples <= 20:
                        issues.append(
                            f"sample {sample}: body overlap {key_a}/{key_b}, "
                            f"horizontal penetration {penetration:.3f}m"
                        )

    moved = 0
    for key, (x0, z0) in initial.items():
        pos = world.position(key)
        positions[key] = pos
        if pos and math.hypot(pos[0] - x0, pos[2] - z0) > 0.05:
            moved += 1

    result = {
        "ok": not issues and moved >= 18,
        "duration_simulated_seconds": duration,
        "physics_steps": int(duration / world.dt),
        "samples": samples,
        "sample_interval_seconds": sample_seconds,
        "agents": count,
        "agents_moved": moved,
        "finite_positions": sum(
            1 for pos in positions.values()
            if pos and all(math.isfinite(v) for v in pos)
        ),
        "max_horizontal_speed": round(max_horizontal_speed, 4),
        "max_horizontal_penetration": round(max_penetration, 4),
        "overlap_samples": overlap_samples,
        "issues": issues,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
