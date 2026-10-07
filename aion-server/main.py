from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import time, threading, os, logging
from database import init, load, save, atomic_update
from simulation import seed, tick, diagnose, propose_repair, self_repair, run_experiment
from autonomy import autonomous_cycle

WORLD_LOCK=threading.Lock()

logging.basicConfig(level=logging.INFO)
log=logging.getLogger("aion")

app=FastAPI(title="AION Persistent Universe", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
init()
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is required for persistent AION world")
if load() is None:
    save(seed(), time.time())

def advance():
    with WORLD_LOCK:
        def update(w):
            if w is None:
                w=seed()
            return autonomous_cycle(w, time.time())[0]
        return atomic_update(update)

def world_snapshot():
    # Browser reads also recover the persistent clock if the host paused the
    # background worker. Wall-clock elapsed time is converted to simulation
    # time and persisted before returning the snapshot.
    def update(w):
        if w is None:
            w=seed()
        clock=w.setdefault("universeClock", {})
        clock.setdefault("simulatedSeconds", float(w.get("worldAge", 0) or 0))
        clock.setdefault("simulatedYears", float(clock["simulatedSeconds"]) / (365.25 * 86400))
        clock.setdefault("lastRealTimestamp", time.time())
        now=time.time()
        elapsed=max(0.0, now-float(clock.get("lastRealTimestamp", now)))
        if elapsed > 0.25:
            w, _ = autonomous_cycle(w, now)
        clock=w.setdefault("universeClock", clock)
        clock["rate"]="24 real hours = 100 simulated years"
        w["worldAge"]=float(clock.get("simulatedSeconds", 0.0))
        return w
    return atomic_update(update)

@app.get("/persistence-test", response_class=HTMLResponse)
def persistence_test_page():
    path=os.path.join(os.path.dirname(__file__), "persistence_test.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@app.api_route("/", methods=["GET","HEAD"])
def root():
    return FileResponse("/app/index.html", media_type="text/html")

@app.get("/health")
def health():
    w=load()
    return {"ok":True,"service":"AION","worldCycle":w.get("cycle",0),"epoch":w.get("epoch"),"worldVersion":w.get("worldVersion",0),"updatedAt":w.get("updatedAt",0),"universeClock":w.get("universeClock",{})}

@app.post("/debug/persistence-test")
def persistence_test(seconds:int=60):
    """Verify one autonomous advance is persisted and can be reloaded."""
    seconds=max(1,min(seconds,2592000))
    before=load()
    if before is None:
        before=seed()
        save(before)
    before_snapshot={
        "cycle":before.get("cycle",0),
        "worldVersion":before.get("worldVersion",0),
        "worldAge":before.get("worldAge",0),
        "population":len(before.get("population",[])),
        "updatedAt":before.get("updatedAt",0),
    }
    def update(w):
        if w is None:
            w=before
        return autonomous_cycle(w,time.time(),forced_seconds=seconds)[0]
    advanced=atomic_update(update)
    persisted=load()
    after_snapshot={
        "cycle":advanced.get("cycle",0),
        "worldVersion":advanced.get("worldVersion",0),
        "worldAge":advanced.get("worldAge",0),
        "population":len(advanced.get("population",[])),
        "updatedAt":advanced.get("updatedAt",0),
    }
    persisted_snapshot={
        "cycle":persisted.get("cycle",0) if persisted else None,
        "worldVersion":persisted.get("worldVersion",0) if persisted else None,
        "worldAge":persisted.get("worldAge",0) if persisted else None,
        "population":len(persisted.get("population",[])) if persisted else None,
        "updatedAt":persisted.get("updatedAt",0) if persisted else None,
    }
    return {
        "ok":persisted is not None and persisted_snapshot["worldVersion"]==after_snapshot["worldVersion"],
        "simulatedSeconds":seconds,
        "before":before_snapshot,
        "after":after_snapshot,
        "persisted":persisted_snapshot,
    }

@app.get("/debug/world")
def debug_world():
    w=load()
    return {
        "ok": w is not None,
        "worldAge": w.get("worldAge", 0) if w else 0,
        "cycle": w.get("cycle", 0) if w else 0,
        "population": len(w.get("population", [])) if w else 0,
        "epoch": w.get("epoch") if w else None,
        "lastTick": w.get("lastTick") if w else None,
        "database": "postgresql" if os.getenv("DATABASE_URL") else "sqlite", "worldVersion": w.get("worldVersion",0), "updatedAt": w.get("updatedAt",0)
    }

@app.get("/ai/status")
def ai_status():
    w=load() or seed()
    return {"autonomous":True,"scope":"game-world-and-persistent-game-config","generation":w.get("evolution",{}).get("generation",1),"strategy":w.get("evolution",{}).get("strategy"),"goal":w.get("aiDiagnostics",{}).get("goal"),"economy":w.get("economy",{}),"technology":w.get("technology",{}),"society":w.get("society",{}),"policy":w.get("aiPolicy",{}),"population":len(w.get("population",[])),"settlements":len(w.get("settlements",[])),"lastReason":w.get("evolution",{}).get("lastReason"),"diagnostics":w.get("aiDiagnostics",{})}

@app.post("/ai/experiment")
def ai_experiment():
    def update(w):
        if w is None: w=seed()
        self_repair(w)
        return run_experiment(w)
    w=atomic_update(update)
    return {"ok":True,"experiment":w.get("aiDiagnostics",{}).get("lastExperiment"),"evolution":w.get("evolution",{})}

@app.post("/ai/self-repair")
def ai_self_repair():
    def update(w):
        if w is None: w=seed()
        self_repair(w)
        return w
    w=atomic_update(update)
    return {"ok":True,"diagnostics":w.get("aiDiagnostics",{}),"generation":w.get("evolution",{}).get("generation",1)}

@app.api_route("/world/reset", methods=["GET","POST"])
def reset_world(confirm: str = ""):
    if confirm != "BIG_BANG":
        return {"ok":False,"message":"Для перезапуска требуется confirm=BIG_BANG"}
    def reset(_w):
        w=seed()
        w["history"].append("Большой взрыв. Пустота. AION начинает создавать новую Землю с нуля.")
        w["epoch"]="Пустота"
        w["universe"]["resetReason"]="manual_rebirth"
        # A Big Bang is a hard world boundary. Persist the fresh seed immediately;
        # the autonomous loop will advance it after the reset instead of silently
        # applying a day of evolution during the reset request.
        w["universeClock"]={
            "lastRealTimestamp": time.time(),
            "simulatedSeconds": 0.0,
            "simulatedYears": 0.0,
            "rate": "24 real hours = 100 simulated years"
        }
        w["worldVersion"]=int(w.get("worldVersion",0))+1
        w["updatedAt"]=time.time()
        return w
    return atomic_update(reset)

@app.post("/physics/colliders")
def physics_colliders(payload: dict):
    colliders=payload.get("colliders",[]) if isinstance(payload,dict) else []
    clean=[]
    for i,item in enumerate(colliders[:500]):
        try:
            clean.append({"id":str(item.get("id",i)),"x":float(item.get("x",0)),"y":float(item.get("y",0)),"z":float(item.get("z",0)),"radius":max(.05,float(item.get("radius",.5))),"height":max(.05,float(item.get("height",1.0))),"kind":"box"})
        except (TypeError,ValueError):
            continue
    def update(w):
        if w is None: w=seed()
        w["physicsColliders"]=clean
        w.setdefault("physics",{})["staticColliders"]=len(clean)
        return w
    return atomic_update(update)

@app.get("/world")
def world():
    # Read-only snapshot: browser polling must never write to PostgreSQL.
    return world_snapshot()

@app.post("/world/tick")
def manual_tick(seconds:int=60):
    # Manual time advancement uses the same autonomous pipeline as the normal world loop.
    seconds=max(1,min(seconds,2592000))
    def update(w):
        if w is None:
            w=seed()
        now=time.time()
        w["manualTimeAdvanceSeconds"]=seconds
        # Move the persistent universe clock forward by the requested simulated amount.
        clock=w.setdefault("universeClock",{})
        clock["manualAdvanceSeconds"]=clock.get("manualAdvanceSeconds",0)+seconds
        w["lastTick"]=now
        return autonomous_cycle(w, now, forced_seconds=seconds)[0]
    return atomic_update(update)

def loop():
    while True:
        try: advance()
        except Exception as exc:
            log.exception("AION autonomous loop failed: %s", exc)
        time.sleep(20)

threading.Thread(target=loop,daemon=True).start()
