"""Build a minimal public GitHub Pages report. No paid calls, raw issuer datasets,
API keys, private inputs, model artifacts or execution quotes are published.
"""
import sys
import asyncio
import json
import os
from pathlib import Path
ROOT = Path.cwd()
ENGINE = ROOT/'backend' if (ROOT/'backend'/'core.py').exists() else ROOT
sys.path.insert(0,str(ENGINE))
from core import factor,iso
import real_yield_engine as real
import positioning_engine as positioning
import dollar_engine as dollar
from aggregator import aggregate
from driver_engines import run as drivers
from decision_engine import build_report


def public_lineage(item):
    data=item.get('data') or {}
    return {k:v for k,v in {'source':item.get('source'),'status':item.get('status'),
                           'fetched_at':item.get('fetched_at'),'observed_at':data.get('observed_at'),
                           'published_at':data.get('published_at'),'warning':item.get('warning')}.items() if v is not None}


def sanitize(report):
    # Publish small derived states and CFTC public-domain history only. Remove
    # provider history/valuation payloads and local server-private configuration.
    for f in report['factors']:
        f['lineage']=[public_lineage(x) for x in f.get('lineage',[])]
        details=f.get('details',{})
        if f['name']=='positioning':
            allowed={'percentile','net_contracts','long_contracts','short_contracts','observed_at','publication_note','history','weekly_change'}
        elif f['name']=='real_yield':
            allowed={'observed_at','five_session_change_bp','momentum_bp','acceleration_bp'}
        elif f['name']=='dollar':allowed={'observed_at','roc_5d_percent','yield_divergence','breakout','breakdown'}
        else:allowed=set()
        f['details']={k:v for k,v in details.items() if k in allowed}
    for alert in report['divergences']:
        alert['lineage']={k:[public_lineage(x) for x in items] for k,items in alert.get('lineage',{}).items()}
    r=report['intelligence']
    for engine in r['engines']:
        engine['lineage']=[public_lineage(x) for x in engine.get('lineage',[])]
        engine['metrics']={}  # No raw-provider data histories in the static site.
    for case in ('bull_case','bear_case'):
        for evidence in r['review'][case]:evidence['lineage']=[public_lineage(x) for x in evidence.get('lineage',[])]
    r['execution']={'ready':False,'reason':'Scheduled public snapshots are not executable live quotes.'}
    # Preserve decisions and readiness explanations calculated by the
    # engine. Never overwrite them with a hardcoded trading outcome.
    # No model or live quote is supplied by this workflow, so the engine
    # will abstain until its own gates are genuinely satisfied.
    r['research_context']={
        'bias':report['bias'],
        'score':report['final_score'],
        'available_weight_percent':report['coverage_percent'],
        'dominant_driver':report['dominant_driver'],
        'status':'uncalibrated_factor_context_not_entry_signal'
    }
    report['publication']={'mode':'scheduled_snapshot','built_at':iso(),
                           'not_live':True,'raw_provider_payloads_removed':True,
                           'note':'Current data availability depends on public sources. No guarantee of a scheduled run.'}
    return report

async def safe(name,weight,call):
    try:return await call
    except Exception as exc:return factor(name,weight,None,'Source unavailable.',[{'source':name,'status':'unavailable','warning':type(exc).__name__}])

async def main():
    # Do not call restricted issuer archive/LLM imports in this public build.
    ry,po=await asyncio.gather(safe('real_yield',.35,real.run()),safe('positioning',.25,positioning.run()))
    dx=await safe('dollar',.10,dollar.run(ry))
    fl=factor('flows',.20,None,'Verified licensed ETF/WGC inputs require a private backend; no issuer holdings dataset is republished.',[])
    na=factor('narrative',.10,None,'Persistent classified narrative archive is not connected in this public scheduled build.',[])
    report=aggregate([ry,po,fl,dx,na])
    from research_engine import run as research
    from supplemental import run as supplemental
    report['research'],report['supplemental']=await asyncio.gather(research(),supplemental())
    engines=await drivers(report)
    report['intelligence']=build_report(engines,report)
    output=Path(os.environ.get('PAGES_OUTPUT','site'))
    (output/'data').mkdir(parents=True,exist_ok=True)
    (output/'data'/'latest.json').write_text(json.dumps(sanitize(report),allow_nan=False))
    print('Public research snapshot generated; no live trade execution.')

if __name__=='__main__':asyncio.run(main())