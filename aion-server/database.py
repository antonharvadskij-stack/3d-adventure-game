import os, json, threading, time

LOCK = threading.Lock()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required for persistent AION world")

# Seeded from the highest diagnostics snapshot observed before this checkpoint
# was introduced. Thereafter, the database checkpoint is the durable high-water
# mark, independent of the mutable JSON world snapshot.
INITIAL_SELF_DEVELOPMENT_CHECKPOINT = {"version": 1162, "accepted": 1080, "rejected": 82}


def _pg():
    import psycopg
    return psycopg.connect(DATABASE_URL)


def _read_checkpoint(cur):
    cur.execute("SELECT version, accepted, rejected FROM aion_self_development_checkpoint WHERE id=1")
    row = cur.fetchone()
    if row:
        return {"version": int(row[0] or 0), "accepted": int(row[1] or 0), "rejected": int(row[2] or 0)}
    return dict(INITIAL_SELF_DEVELOPMENT_CHECKPOINT)


def _merge_checkpoint(state, checkpoint):
    if not isinstance(state, dict):
        return state
    diagnostics = state.setdefault("aiDiagnostics", {})
    if not isinstance(diagnostics, dict):
        diagnostics = {}
        state["aiDiagnostics"] = diagnostics
    sd = diagnostics.setdefault("selfDevelopment", {})
    if not isinstance(sd, dict):
        sd = {}
        diagnostics["selfDevelopment"] = sd
    for key in ("version", "accepted", "rejected"):
        try:
            current = int(sd.get(key, 0) or 0)
        except (TypeError, ValueError):
            current = 0
        sd[key] = max(current, int(checkpoint.get(key, 0) or 0))
    return state


def _write_checkpoint(cur, state):
    sd = (state.get("aiDiagnostics") or {}).get("selfDevelopment") or {}
    values = {}
    for key in ("version", "accepted", "rejected"):
        try:
            values[key] = max(0, int(sd.get(key, 0) or 0))
        except (TypeError, ValueError):
            values[key] = 0
    cur.execute(
        """INSERT INTO aion_self_development_checkpoint(id,version,accepted,rejected)
           VALUES(1,%s,%s,%s)
           ON CONFLICT(id) DO UPDATE SET
             version=GREATEST(aion_self_development_checkpoint.version, EXCLUDED.version),
             accepted=GREATEST(aion_self_development_checkpoint.accepted, EXCLUDED.accepted),
             rejected=GREATEST(aion_self_development_checkpoint.rejected, EXCLUDED.rejected)""",
        (values["version"], values["accepted"], values["rejected"]),
    )


def init():
    with LOCK:
        c = _pg()
        try:
            with c.cursor() as cur:
                cur.execute("CREATE TABLE IF NOT EXISTS world (id INTEGER PRIMARY KEY, state JSONB NOT NULL, updated DOUBLE PRECISION NOT NULL)")
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS aion_self_development_checkpoint (
                         id INTEGER PRIMARY KEY CHECK (id=1),
                         version BIGINT NOT NULL DEFAULT 0,
                         accepted BIGINT NOT NULL DEFAULT 0,
                         rejected BIGINT NOT NULL DEFAULT 0
                       )"""
                )
                cur.execute(
                    """INSERT INTO aion_self_development_checkpoint(id,version,accepted,rejected)
                       VALUES(1,%s,%s,%s) ON CONFLICT(id) DO NOTHING""",
                    (INITIAL_SELF_DEVELOPMENT_CHECKPOINT["version"],
                     INITIAL_SELF_DEVELOPMENT_CHECKPOINT["accepted"],
                     INITIAL_SELF_DEVELOPMENT_CHECKPOINT["rejected"]),
                )
            c.commit()
        finally:
            c.close()


def load():
    c = _pg()
    try:
        with c.cursor() as cur:
            cur.execute("SELECT state FROM world WHERE id=1")
            r = cur.fetchone()
            state = r[0] if r else None
            if state is not None:
                checkpoint = _read_checkpoint(cur)
                state = _merge_checkpoint(state, checkpoint)
        return state
    finally:
        c.close()


def atomic_update(updater):
    with LOCK:
        c = _pg()
        try:
            with c.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(918273645)")
                cur.execute("SELECT state FROM world WHERE id=1")
                r = cur.fetchone()
                state = r[0] if r else None
                checkpoint = _read_checkpoint(cur)
                state = _merge_checkpoint(state, checkpoint)
                state = updater(state)
                state = _merge_checkpoint(state, checkpoint)
                _write_checkpoint(cur, state)
                cur.execute(
                    "INSERT INTO world(id,state,updated) VALUES(1,%s,%s) "
                    "ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state,updated=EXCLUDED.updated",
                    (json.dumps(state, ensure_ascii=False), time.time())
                )
            c.commit()
            return state
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()


def save(state, now=None):
    now = now or time.time()
    with LOCK:
        c = _pg()
        try:
            with c.cursor() as cur:
                checkpoint = _read_checkpoint(cur)
                state = _merge_checkpoint(state, checkpoint)
                _write_checkpoint(cur, state)
                cur.execute(
                    "INSERT INTO world(id,state,updated) VALUES(1,%s,%s) "
                    "ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state,updated=EXCLUDED.updated",
                    (json.dumps(state, ensure_ascii=False), now)
                )
            c.commit()
        finally:
            c.close()
