"""Deterministic AION physics QA.
Checks physical contact/penetration rather than assuming a specific body-center height.
"""
import os, sys, json, math
sys.path.insert(0, os.path.dirname(__file__))
from simulation import PhysicsWorld, simulate_physics, physics

def run():
    p=PhysicsWorld()
    p.add_static("qa:ground", 0, -0.05, 0, 50, 0.1, "box")
    p.add_body("qa:agent", 0, 1, 0, .4, 1, 1.5)
    p.set_velocity("qa:agent", 2, 0)
    p.step(2.0)
    pos=p.position("qa:agent")

    # The body's center should remain at least half-height/radius above ground.
    # Current AION bodies use a ~0.4m collision half-height, so allow a small solver epsilon.
    ground_clearance = pos[1] if pos else -math.inf
    checks={
        "ground_contact": bool(pos and ground_clearance >= 0.35),
        "finite_position": bool(pos and all(math.isfinite(v) for v in pos)),
    }

    p.add_static("qa:wall", 2.0, .75, 0, .5, 1.5, "box")
    p.set_position("qa:agent", 0, .9, 0)
    p.set_velocity("qa:agent", 3, 0)
    p.step(1.5)
    pos2=p.position("qa:agent")
    checks["static_collision"]=bool(pos2 and pos2[0] < 2.6)

    p.set_position("qa:agent", 0, .9, 0)
    p.add_body("qa:agent2", .7, .9, 0, .4, 1, 1.5)
    p.set_velocity("qa:agent", 1, 0)
    p.set_velocity("qa:agent2", -1, 0)
    p.step(1.0)
    x1=p.position("qa:agent"); x2=p.position("qa:agent2")
    dist=math.dist(x1,x2) if x1 and x2 else 0
    checks["dynamic_collision"]=dist >= .65

    # Production terrain collider: a body dropped above seeded terrain must land on the surface.
    terrain=PhysicsWorld()
    terrain.set_terrain(12345)
    terrain.add_body("qa:terrain-agent",0,3,0,.4,1,1.5)
    terrain.step(2.0)
    terrain_pos=terrain.position("qa:terrain-agent")
    checks["terrain_collision"]=bool(terrain_pos and math.isfinite(terrain_pos[1]) and 1.65 <= terrain_pos[1] <= 2.2)

    # A new universe must not reuse a previous universe's rigid body for the same agent ID.
    world_a={"worldVersion":1001,"universe":{"worldSeed":12345},"population":[{"id":1,"x":-8,"y":3,"z":0}],"physicsColliders":[]}
    world_b={"worldVersion":1002,"universe":{"worldSeed":54321},"population":[{"id":1,"x":8,"y":3,"z":0}],"physicsColliders":[]}
    simulate_physics(world_a,.1)
    simulate_physics(world_b,.1)
    checks["universe_reset_clears_old_bodies"]=("agent:1001:12345:1" not in physics.bodies and "agent:1002:54321:1" in physics.bodies)

    moving={"worldVersion":1003,"universe":{"worldSeed":33333},"population":[{"id":7,"x":0,"y":3,"z":0}],"physicsColliders":[]}
    motion=[]
    for _ in range(10):
        simulate_physics(moving,.25)
        a=moving["population"][0]
        motion.append((a["x"],a["z"]))
    checks["autonomous_agent_motion"]=math.dist(motion[0],motion[-1])>.25

    result={"ok":all(checks.values()),"checks":checks,
            "positions":{"ground":pos,"wall":pos2,"dynamicA":x1,"dynamicB":x2,"terrain":terrain_pos,
                         "motionStart":motion[0],"motionEnd":motion[-1]}}
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result["ok"] else 1

if __name__=="__main__":
    raise SystemExit(run())
