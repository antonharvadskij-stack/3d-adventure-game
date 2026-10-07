import os, json, sqlite3, threading, time
LOCK=threading.Lock()
DATABASE_URL=os.getenv("DATABASE_URL")
TEST_MODE=os.getenv("AION_TEST_MODE")=="1"
SQLITE_PATH=os.getenv("AION_SQLITE_PATH","/tmp/aion_world.sqlite3")

if not DATABASE_URL and not TEST_MODE:
    raise RuntimeError("DATABASE_URL is required for persistent AION world")

def _pg():
    import psycopg
    return psycopg.connect(DATABASE_URL)

def _sqlite():
    c=sqlite3.connect(SQLITE_PATH, timeout=30)
    c.execute("CREATE TABLE IF NOT EXISTS world (id INTEGER PRIMARY KEY, state TEXT NOT NULL, updated REAL NOT NULL)")
    return c

def init():
    with LOCK:
        if TEST_MODE and not DATABASE_URL:
            c=_sqlite(); c.commit(); c.close(); return
        c=_pg()
        with c.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS world (id INTEGER PRIMARY KEY, state JSONB NOT NULL, updated DOUBLE PRECISION NOT NULL)")
        c.commit(); c.close()

def load():
    if TEST_MODE and not DATABASE_URL:
        c=_sqlite()
        r=c.execute("SELECT state FROM world WHERE id=1").fetchone()
        c.close()
        return json.loads(r[0]) if r else None
    c=_pg()
    with c.cursor() as cur:
        cur.execute("SELECT state FROM world WHERE id=1")
        r=cur.fetchone()
    c.close()
    return r[0] if r else None

def atomic_update(updater):
    with LOCK:
        if TEST_MODE and not DATABASE_URL:
            c=_sqlite()
            r=c.execute("SELECT state FROM world WHERE id=1").fetchone()
            state=json.loads(r[0]) if r else None
            state=updater(state)
            c.execute("INSERT INTO world(id,state,updated) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,updated=excluded.updated",(json.dumps(state,ensure_ascii=False),time.time()))
            c.commit(); c.close()
            return state
        c=_pg()
        try:
            with c.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(918273645)")
                cur.execute("SELECT state FROM world WHERE id=1")
                r=cur.fetchone()
                state=r[0] if r else None
                state=updater(state)
                cur.execute("INSERT INTO world(id,state,updated) VALUES(1,%s,%s) ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state,updated=EXCLUDED.updated",(json.dumps(state,ensure_ascii=False),time.time()))
            c.commit()
            return state
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

def save(state, now=None):
    now=now or time.time()
    with LOCK:
        if TEST_MODE and not DATABASE_URL:
            c=_sqlite()
            c.execute("INSERT INTO world(id,state,updated) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,updated=excluded.updated",(json.dumps(state,ensure_ascii=False),now))
            c.commit(); c.close(); return
        c=_pg()
        with c.cursor() as cur:
            cur.execute("INSERT INTO world(id,state,updated) VALUES(1,%s,%s) ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state,updated=EXCLUDED.updated",(json.dumps(state,ensure_ascii=False),now))
        c.commit(); c.close()
