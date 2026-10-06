#!/usr/bin/env python3
"""AION smoke-test suite for CI/Render deploy verification."""
import json, os, sys, urllib.request, urllib.error

BASE=os.environ.get("AION_URL","http://localhost:8000").rstrip("/")
results={}
def get(path):
    with urllib.request.urlopen(BASE+path,timeout=20) as r:
        return r.status,json.loads(r.read().decode())

for name,path in [("health","/health"),("world","/debug/world"),("ai","/ai/status")]:
    try:
        status,data=get(path); results[name]={"ok":status==200,"status":status,"data":data}
    except Exception as e:
        results[name]={"ok":False,"error":str(e)}

try:
    status,data=get("/debug/persistence-test?seconds=1")
    results["persistence"]={"ok":status==200 and data.get("ok") is True,"status":status,"data":data}
except Exception as e:
    results["persistence"]={"ok":False,"error":str(e)}

try:
    import subprocess
    proc=subprocess.run([sys.executable,os.path.join(os.path.dirname(__file__),"qa_physics.py")],capture_output=True,text=True,timeout=60)
    results["physics"]={"ok":proc.returncode==0,"output":proc.stdout[-5000:],"error":proc.stderr[-2000:]}
except Exception as e:
    results["physics"]={"ok":False,"error":str(e)}

print(json.dumps({"ok":all(x.get("ok") for x in results.values()),"base":BASE,"results":results},ensure_ascii=False,indent=2))
raise SystemExit(0 if all(x.get("ok") for x in results.values()) else 1)
