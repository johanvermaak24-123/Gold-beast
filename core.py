"""Shared source lineage and persistent last-good snapshots."""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import sqlite3
from contextlib import contextmanager

UTC=timezone.utc

def now(): return datetime.now(UTC)
def iso(): return now().isoformat()
@contextmanager
def db():
    path=Path(os.getenv('DATA_DIR','data')); path.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path/'terminal.sqlite',timeout=15)
    conn.execute('CREATE TABLE IF NOT EXISTS snapshots (key TEXT PRIMARY KEY, body TEXT, fetched_at TEXT)')
    try:
        with conn:yield conn
    finally:conn.close()

def cached(key):
    with db() as c:
        r=c.execute('SELECT body,fetched_at FROM snapshots WHERE key=?',(key,)).fetchone()
    return (json.loads(r[0]),r[1]) if r else (None,None)

def save(key,data):
    stamp=iso()
    with db() as c:c.execute('INSERT OR REPLACE INTO snapshots VALUES (?,?,?)',(key,json.dumps(data,allow_nan=False),stamp))
    return stamp

async def source(key,url,loader,ttl_seconds=300):
    old,stamp=cached(key)
    if stamp and (now()-datetime.fromisoformat(stamp)).total_seconds()<ttl_seconds:
        return {'status':'ok','data':old,'source':url,'fetched_at':stamp,'cached':True}
    try:
        data=await loader()
        if data is None: raise ValueError('Empty source')
        stamp=save(key,data)
        return {'status':'ok','data':data,'source':url,'fetched_at':stamp,'cached':False}
    except Exception as exc:
        return {'status':'stale' if old is not None else 'unavailable','data':old,
                'source':url,'fetched_at':stamp,'error':type(exc).__name__,
                'warning':'Source failed; last-good data retained but excluded from live scoring.'}

def factor(name,weight,signal,reason,lineage,**details):
    statuses=[v['status'] for v in lineage]
    status='unavailable' if signal is None else 'stale' if any(s!='ok' for s in statuses) else 'ok'
    return dict(name=name,weight=weight,signal=signal if status=='ok' else None,
                status=status,reason=reason,lineage=lineage,details=details)

def expired(date,max_days):
    return not date or (now().date()-datetime.fromisoformat(date[:10]).date()).days>max_days
