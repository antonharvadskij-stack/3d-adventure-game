from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import time, threading, os, logging
from database import init, load, save, atomic_update
from simulation import seed, tick, diagnose, propose_repair, self_repair, run_experiment
from autonomy import autonomous_cycle
WORLD_LOCK=threading.Lock()

logging.basicConfig(level=logging.INFO)\nlog=logging.getLogger("aion")\n\napp=FastAPI(title="AION Persistent Universe", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
init()
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is required for persistent AION world")
if load() is None:
    save(seed(), time.time())

def advance():
    with WORLD_LOCK:
        return atomic_update(lambda w: autonomous_cycle(w, time.time())[0] if w is not None else seed())

@app.get("/")
def root():
    return FileResponse("/app/index.html", media_type="text/html")

@app.get("/health")
def health():
    w=load()
    return {"ok":True,"service":"AION","worldCycle":w.get("cycle",0),"epoch":w.get("epoch"),"worldVersion":w.get("worldVersion",0),"updatedAt":w.get("updatedAt",0),"universeClock":w.get("universeClock",{})}

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
        return w
    return atomic_update(reset)

@app.get("/world")
def world():
    return advance()

@app.post("/world/tick")
def manual_tick(seconds:int=60):
    def update(w):
        if w is None:
            w=seed()
        return tick(w, max(1,min(seconds,2592000)))
    return atomic_update(update)

def loop():
    while True:
        try: advance()
        except Exception as exc:\n            log.exception("AION autonomous loop failed: %s", exc)
        time.sleep(10)

threading.Thread(target=loop,daemon=True).start()
