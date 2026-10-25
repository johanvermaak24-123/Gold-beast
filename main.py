import asyncio
from contextlib import asynccontextmanager
import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core import factor
import real_yield_engine as real
import positioning_engine as positioning
import flow_engine as flows
import dollar_engine as dollar
import narrative_cluster_engine as narrative
from aggregator import aggregate

_snapshot=None
_refreshed=0.0
_lock=asyncio.Lock()

async def safe(name,weight,call):
    try:return await call
    except Exception as exc:
        return factor(name,weight,None,'Module unavailable; inspect server diagnostics.',
                      [{'status':'unavailable','source':name,'error':type(exc).__name__}],error=type(exc).__name__)

async def refresh():
    global _snapshot,_refreshed
    async with _lock:
        if _snapshot and time.monotonic()-_refreshed<300:return _snapshot
        ry,po,fl,na=await asyncio.gather(safe('real_yield',.35,real.run()),
            safe('positioning',.25,positioning.run()),safe('flows',.20,flows.run()),
            safe('narrative',.10,narrative.run()))
        dx=await safe('dollar',.10,dollar.run(ry))
        candidate=aggregate([ry,po,fl,dx,na])
        from driver_engines import run as driver_states
        from decision_engine import build_report
        try:
            engines=await driver_states(candidate)
        except Exception as exc:
            from probability_model import FEATURES
            engines=[{'engine':name,'status':'unavailable','gold_support':None,'reason':'Driver collection failed: '+type(exc).__name__,'resolution':'daily','metrics':{},'lineage':[]} for name in FEATURES]
        candidate['intelligence']=await asyncio.to_thread(build_report,engines,candidate)
        _snapshot=candidate
        _refreshed=time.monotonic()
        return _snapshot

async def poll():
    while True:
        try:await refresh()
        except Exception:pass
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app):
    task=asyncio.create_task(poll())
    yield
    task.cancel()
    try:await task
    except asyncio.CancelledError:pass

app=FastAPI(title='Gold Regime Terminal',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','*').split(','),
                   allow_credentials=False,allow_methods=['GET'],allow_headers=['*'])
@app.get('/health')
def health():return {'status':'ok','service':'gold-intelligence','version':'2.1.0','snapshot_ready':_snapshot is not None}
@app.get('/regime')
async def regime():return await refresh()
@app.get('/positioning')
async def positioning_view():
    data=await refresh()
    return {f['name']:f for f in data['factors'] if f['name'] in {'positioning','flows'}}
@app.get('/narratives')
async def narratives_view():
    data=await refresh()
    return next(f for f in data['factors'] if f['name']=='narrative')
@app.get('/divergences')
async def divergences_view():
    data=await refresh()
    return {'alerts':data['divergences'],'generated_at':data['generated_at'],'coverage_percent':data['coverage_percent']}


@app.get('/intelligence')
async def intelligence_view():
    data=await refresh()
    return data['intelligence']


@app.get('/capabilities')
def capabilities():
    from pathlib import Path
    from probability_model import HORIZONS
    from decision_engine import execution_state
    directory=Path(os.getenv('DATA_DIR','data'))
    model_dir=Path(os.getenv('MODEL_DIR',str(directory/'models')))
    return {'version':'2.1.0','snapshot_ready':_snapshot is not None,
            'models_present':{h:(model_dir/(h+'.json')).is_file() for h in HORIZONS},
            'fed_path_present':(directory/'fed_path.json').is_file(),
            'intraday_features_present':(directory/'intraday_features.json').is_file(),
            'quote_ready':execution_state()['ready'],
            'llm_configured':bool(os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_MODEL')),
            'trade_execution':False,
            'note':'File presence is configuration status, not validation or accuracy.'}
