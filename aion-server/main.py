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
    # Fast read-only snapshot. The autonomous loop is the single writer that
    # advances simulation time, so browser polling never competes for the
    # PostgreSQL advisory lock and can never stall behind a simulation tick.
    w=load()
    if w is None:
        w=seed()
        save(w, time.time())
    return w

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
    # Render health checks must be independent of PostgreSQL latency.
    # Database-backed diagnostics belong to /debug/world.
    return {"ok":True,"service":"AION","persistentStorage":"postgresql"}

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
    # Physics state is process-global; serialize this diagnostic with the
    # autonomous writer so PyBullet cannot be accessed concurrently.
    with WORLD_LOCK:
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

@app.get("/ai/self-development")
def ai_self_development():
    w=load() or seed()
    sd=w.get("aiDiagnostics",{}).get("selfDevelopment",{})
    return {
        "ok":True,
        "version":sd.get("version",0),
        "accepted":sd.get("accepted",0),
        "rejected":sd.get("rejected",0),
        "latest":sd.get("modules",[])[-1] if sd.get("modules") else None,
        "lastTest":sd.get("lastTest"),
        "lastDecision":sd.get("lastDecision"),
        "autonomy":"observe -> invent -> sandbox -> validate -> adopt/rollback"
    }

@app.get("/ai/diagnostics")
def ai_diagnostics():
    """Read-only, machine-readable diagnostics for remote health checks."""
    checks = []
    try:
        w = load()
        db_ok = isinstance(w, dict)
        checks.append({"name": "database_read", "ok": db_ok})
        if not db_ok:
            return {
                "ok": False,
                "service": "AION",
                "checks": checks,
                "error": "World state is missing or database read failed",
                "autonomy": "observe -> invent -> sandbox -> validate -> adopt/rollback",
            }

        sd = (w.get("aiDiagnostics") or {}).get("selfDevelopment") or {}
        try:
            version = int(sd.get("version", 0) or 0)
            accepted = int(sd.get("accepted", 0) or 0)
            rejected = int(sd.get("rejected", 0) or 0)
            counters_ok = min(version, accepted, rejected) >= 0 and version >= accepted + rejected
        except (TypeError, ValueError):
            version, accepted, rejected = 0, 0, 0
            counters_ok = False
        checks.append({"name": "self_development_counters", "ok": counters_ok})

        population = w.get("population", [])
        population_ok = isinstance(population, list)
        checks.append({"name": "population_shape", "ok": population_ok})

        latest = sd.get("modules", [])[-1] if isinstance(sd.get("modules"), list) and sd.get("modules") else None
        last_test = sd.get("lastTest")
        test_ok = isinstance(last_test, dict) and last_test.get("validated") is True
        checks.append({"name": "last_sandbox_validation", "ok": test_ok})

        database = "postgresql" if os.getenv("DATABASE_URL") else "sqlite"
        checks.append({"name": "postgresql_configured", "ok": database == "postgresql"})

        return {
            "ok": all(item["ok"] for item in checks),
            "service": "AION",
            "database": database,
            "world": {
                "worldVersion": w.get("worldVersion", 0),
                "worldAge": w.get("worldAge", 0),
                "cycle": w.get("cycle", 0),
                "population": len(population) if population_ok else None,
                "epoch": w.get("epoch"),
                "updatedAt": w.get("updatedAt", 0),
            },
            "selfDevelopment": {
                "version": version,
                "accepted": accepted,
                "rejected": rejected,
                "latest": latest,
                "lastTest": last_test,
                "lastDecision": sd.get("lastDecision"),
            },
            "checks": checks,
            "autonomy": "observe -> invent -> sandbox -> validate -> adopt/rollback",
        }
    except Exception:
        log.exception("AION read-only diagnostics failed")
        return {
            "ok": False,
            "service": "AION",
            "checks": checks + [{"name": "diagnostics_exception", "ok": False}],
            "error": "Diagnostics could not complete; inspect Render application logs",
        }


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
    def reset(previous):
        previous_version=int((previous or {}).get("worldVersion",0) or 0)
        w=seed()
        w["history"].append("Большой взрыв. Пустота. AION начинает создавать новую Землю с нуля.")
        w["epoch"]="Пустота"
        w["universe"]["resetReason"]="manual_rebirth"
        # A Big Bang creates a new persistent world generation. Keep the
        # generation counter from the previous world so the client can prove
        # that a new universe replaced the old one.
        w["universeClock"]={
            "lastRealTimestamp": time.time(),
            "simulatedSeconds": 0.0,
            "simulatedYears": 0.0,
            "rate": "24 real hours = 100 simulated years"
        }
        now=time.time()
        w["worldVersion"]=previous_version+1
        w["updatedAt"]=now
        w.setdefault("universeClock",{})["lastRealTimestamp"]=now
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
        time.sleep(1)

def start_autonomous_loop():
    try:
        advance()
    except Exception as exc:
        log.exception("AION initial autonomous advance failed: %s", exc)
    threading.Thread(target=loop,daemon=True).start()

start_autonomous_loop()
