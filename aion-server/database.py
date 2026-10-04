import os, json, sqlite3, threading, time
LOCK=threading.Lock()
DATABASE_URL=os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required for persistent AION world")

def _pg():
    import psycopg
    return psycopg.connect(DATABASE_URL)

def init():
    with LOCK:
        c=_pg()
        with c.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS world (id INTEGER PRIMARY KEY, state JSONB NOT NULL, updated DOUBLE PRECISION NOT NULL)")
        c.commit(); c.close()

def load():
    c=_pg()
    with c.cursor() as cur:
        cur.execute("SELECT state FROM world WHERE id=1")
        r=cur.fetchone()
    c.close()
    return r[0] if r else None

def save(state, now=None):
    now=now or time.time()
    with LOCK:
        c=_pg()
        with c.cursor() as cur:
            cur.execute("INSERT INTO world(id,state,updated) VALUES(1,%s,%s) ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state,updated=EXCLUDED.updated",(json.dumps(state,ensure_ascii=False),now))
        c.commit(); c.close()
