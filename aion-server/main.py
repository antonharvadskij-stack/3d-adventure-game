from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import time, threading, os
from database import init, load, save, atomic_update
from simulation import seed, tick
WORLD_LOCK=threading.Lock()

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
            now=time.time()
            if w is None:
                return seed()
            elapsed=max(0, now-w.get("lastTick", now))
            if elapsed >= 0.25:
                w=tick(w, elapsed)
            return w
        return atomic_update(update)

@app.get("/")
def root():
    return FileResponse("/app/index.html", media_type="text/html")

@app.get("/health")
def health():
    w=load()
    return {"ok":True,"service":"AION","worldCycle":w.get("cycle",0),"epoch":w.get("epoch"),"worldVersion":w.get("worldVersion",0),"updatedAt":w.get("updatedAt",0)}

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
        except Exception: pass
        time.sleep(10)

threading.Thread(target=loop,daemon=True).start()
