import os, json, sqlite3, threading, time, logging

log = logging.getLogger("aion.database")
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
    started = time.perf_counter()
    connect_ms = None
    query_ms = None
    c = None
    try:
        connect_started = time.perf_counter()
        c = _pg()
        connect_ms = (time.perf_counter() - connect_started) * 1000
        query_started = time.perf_counter()
        with c.cursor() as cur:
            cur.execute("SELECT state FROM world WHERE id=1")
            r = cur.fetchone()
        query_ms = (time.perf_counter() - query_started) * 1000
        return r[0] if r else None
    except Exception:
        log.exception("postgres_load_failed")
        raise
    finally:
        if c is not None:
            c.close()
        log.info(
            "postgres_load_timing connect_ms=%s query_ms=%s total_ms=%.1f",
            "n/a" if connect_ms is None else f"{connect_ms:.1f}",
            "n/a" if query_ms is None else f"{query_ms:.1f}",
            (time.perf_counter() - started) * 1000,
        )

def atomic_update(updater):
    with LOCK:
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
        c=_pg()
        with c.cursor() as cur:
            cur.execute("INSERT INTO world(id,state,updated) VALUES(1,%s,%s) ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state,updated=EXCLUDED.updated",(json.dumps(state,ensure_ascii=False),now))
        c.commit(); c.close()
