import os, json, sqlite3, threading, time
LOCK=threading.Lock()
DATABASE_URL=os.getenv("DATABASE_URL")

def _pg():
    import psycopg2
    return psycopg2.connect(DATABASE_URL)

def init():
    if DATABASE_URL:
        with LOCK:
            c=_pg()
            with c.cursor() as cur:
                cur.execute("CREATE TABLE IF NOT EXISTS world (id INTEGER PRIMARY KEY, state JSONB NOT NULL, updated DOUBLE PRECISION NOT NULL)")
            c.commit(); c.close()
    else:
        c=sqlite3.connect("aion.db"); c.execute("CREATE TABLE IF NOT EXISTS world(id INTEGER PRIMARY KEY,state TEXT NOT NULL,updated REAL NOT NULL)"); c.commit(); c.close()

def load():
    if DATABASE_URL:
        c=_pg()
        with c.cursor() as cur:
            cur.execute("SELECT state FROM world WHERE id=1")
            r=cur.fetchone()
        c.close()
        return r[0] if r else None
    c=sqlite3.connect("aion.db"); r=c.execute("SELECT state FROM world WHERE id=1").fetchone(); c.close()
    return json.loads(r[0]) if r else None

def save(state, now=None):
    now=now or time.time()
    if DATABASE_URL:
        with LOCK:
            c=_pg()
            with c.cursor() as cur:
                cur.execute("INSERT INTO world(id,state,updated) VALUES(1,%s,%s) ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state,updated=EXCLUDED.updated",(json.dumps(state,ensure_ascii=False),now))
            c.commit(); c.close()
    else:
        with LOCK:
            c=sqlite3.connect("aion.db")
            c.execute("INSERT INTO world(id,state,updated) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,updated=excluded.updated",(json.dumps(state,ensure_ascii=False),now))
            c.commit(); c.close()
