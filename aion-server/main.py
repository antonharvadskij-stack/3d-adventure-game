from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time,threading
from database import init,load,save
from simulation import seed,tick
app=FastAPI(title="AION Persistent Universe")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
init()
if load() is None: save(seed(),time.time())
def advance():
 w=load();now=time.time();return tick(w,now-w.get("lastTick",now))
@app.get("/health")
def health(): return {"ok":True,"service":"AION","time":time.time()}
@app.get("/world")
def world(): 
 w=advance();save(w,time.time());return w
@app.post("/world/tick")
def manual_tick(seconds:int=60):
 w=load();w=tick(w,seconds);save(w,time.time());return w
def loop():
 while True:
  try:
   w=advance();save(w,time.time())
  except Exception: pass
  time.sleep(30)
threading.Thread(target=loop,daemon=True).start()
