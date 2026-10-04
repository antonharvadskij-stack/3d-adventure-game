from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time, threading, os
from database import init, load, save
from simulation import seed, tick

app=FastAPI(title="AION Persistent Universe", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
init()
if load() is None:
    save(seed(), time.time())

def advance():
    w=load()
    now=time.time()
    elapsed=max(0, now-w.get("lastTick", now))
    w=tick(w, elapsed)
    save(w, now)
    return w

@app.get("/")
def root():
    return {"service":"AION","status":"online","endpoints":["/health","/world","/world/tick"]}

@app.get("/health")
def health():
    w=load()
    return {"ok":True,"service":"AION","worldCycle":w.get("cycle",0),"epoch":w.get("epoch")}

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
        "database": "postgresql" if os.getenv("DATABASE_URL") else "sqlite"
    }

@app.get("/world")
def world():
    return advance()

@app.post("/world/tick")
def manual_tick(seconds:int=60):
    w=load()
    w=tick(w, max(1,min(seconds,2592000)))
    save(w,time.time())
    return w

def loop():
    while True:
        try: advance()
        except Exception: pass
        time.sleep(30)

threading.Thread(target=loop,daemon=True).start()
