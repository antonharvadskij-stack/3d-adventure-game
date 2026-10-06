"""Deterministic AION physics QA.
Checks physical contact/penetration rather than assuming a specific body-center height.
"""
import os, sys, json, math
sys.path.insert(0, os.path.dirname(__file__))
from simulation import PhysicsWorld

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

    result={"ok":all(checks.values()),"checks":checks,
            "positions":{"ground":pos,"wall":pos2,"dynamicA":x1,"dynamicB":x2}}
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result["ok"] else 1

if __name__=="__main__":
    raise SystemExit(run())
