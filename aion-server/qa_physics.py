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

    # Verify the same seeded, non-flat terrain used by the browser is a real server-side collider.
    terrain_world=PhysicsWorld()
    terrain_seed=12345
    terrain_world.set_terrain(terrain_seed)
    terrain_world.add_body("qa:terrain-agent",0,5,0,.4,1,1.5)
    terrain_world.step(2.0)
    terrain_pos=terrain_world.position("qa:terrain-agent")
    x=z=0.0
    k=(terrain_seed%100000)/100000.0
    base=math.sin(x*.045)*1.8+math.cos(z*.052)*1.5+math.sin((x+z)*.085)*1.1+math.sin(x*.17-z*.11)*.55
    continent=math.sin(x*.031+z*.018)+math.sin(x*.017-z*.027)*.7+math.cos(x*.013+z*.041)*.6
    land=max(0.0,min(1.0,(continent+.3)/.65))
    detail=math.sin(x*(.021+k*.02)+terrain_seed*.000001)*.22+math.cos(z*(.027+k*.015)-terrain_seed*.0000013)*.18
    terrain_surface=max(-1.15,-1.15+land*(1.15+base*.38+max(0.0,continent)**1.35*.95+detail))-.05
    terrain_contact=bool(terrain_pos and abs(terrain_pos[1]-(terrain_surface+.75))<.18)
    checks["seeded_terrain_collision"]=terrain_contact

    generation_world=PhysicsWorld()
    generation_world.reset_world_generation((1,111))
    generation_world.add_body("agent:old",0,1,0,.4,1,1.5)
    generation_world.add_static("static:old",2,1,0,.5,1.0,"box")
    generation_world.reset_world_generation((2,222))
    checks["new_world_clears_cached_bodies"]=(
        "agent:old" not in generation_world.bodies and
        "static:old" not in generation_world.bodies
    )

    result={"ok":all(checks.values()),"checks":checks,
            "positions":{"ground":pos,"wall":pos2,"dynamicA":x1,"dynamicB":x2,
                         "terrain":terrain_pos,"terrain_surface":terrain_surface}}
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result["ok"] else 1

if __name__=="__main__":
    raise SystemExit(run())
