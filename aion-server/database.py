import sqlite3, json, threading
from pathlib import Path
DB=Path(__file__).with_name("aion.db")
LOCK=threading.Lock()
def conn():
 c=sqlite3.connect(DB,check_same_thread=False); c.row_factory=sqlite3.Row; return c
def init():
 with LOCK:
  c=conn(); c.executescript("""CREATE TABLE IF NOT EXISTS world(id INTEGER PRIMARY KEY, state TEXT NOT NULL, updated REAL NOT NULL);"""); c.commit(); c.close()
def load():
 c=conn(); r=c.execute("SELECT state FROM world WHERE id=1").fetchone(); c.close(); return json.loads(r["state"]) if r else None
def save(state,now):
 with LOCK:
  c=conn(); c.execute("INSERT INTO world(id,state,updated) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,updated=excluded.updated",(json.dumps(state,ensure_ascii=False),now)); c.commit(); c.close()
