"""Ten measured driver states. Forecasts are produced separately by fitted models."""
import asyncio
import json
import math
import os
from pathlib import Path
from datetime import datetime
import numpy as np
from core import source,now,expired
from real_yield_engine import fred,prices

FEATURES=['real_yield','usd','liquidity','bond','fed','risk','inflation','recession','positioning','technical']

def state(name,signal,reason,lineage,resolution='daily',**metrics):
    valid=signal is not None and math.isfinite(signal) and all(x.get('status')=='ok' for x in lineage)
    return {'engine':name,'gold_support':float(np.clip(signal,-1,1)) if valid else None,
            'status':'ok' if valid else 'unavailable','reason':reason,'lineage':lineage,
            'resolution':resolution,'metrics':metrics}

async def cadence_fred(code,max_days):
    # Different keys prevent a weekly cache being mistaken for a daily source.
    # Existing fred() fetches >=30 points and applies daily freshness; relax only
    # observation-age flags when the retrieval itself succeeded, never a failure.
    item=await fred(code,days=1800 if max_days>14 else 800)
    if item.get('data') and not item.get('error'):
        item['status']='stale' if expired(item['data']['observed_at'],max_days) else 'ok'
    return item

def change(item,n=5,percent=False):
    if item.get('status')!='ok' or not item.get('data'):return None
    r=item['data']['rows']
    if len(r)<=n:return None
    return (r[-1]['value']/r[-1-n]['value']-1)*100 if percent else r[-1]['value']-r[-1-n]['value']

def scaled(value,scale):return None if value is None else float(np.clip(value/scale,-1,1))

async def fed_state():
    path=Path(os.getenv('DATA_DIR','data'))/'fed_path.json'
    async def load():
        d=json.loads(path.read_text())
        published=datetime.fromisoformat(d['published_at'].replace('Z','+00:00'))
        if not published.tzinfo or published>now() or (now()-published).total_seconds()>86400:
            raise ValueError('Stale/future Fed path')
        p=d['probabilities']
        if set(p)!={'hike','hold','cut'} or any(not 0<=float(x)<=1 for x in p.values()) or abs(sum(p.values())-1)>1e-6:
            raise ValueError('Invalid Fed probabilities')
        if not d.get('source_url') or not d.get('meeting_date'):raise ValueError('Missing Fed lineage')
        return d
    item=await source('fed:path','Verified local futures-derived fed_path.json',load,300)
    d=item.get('data') or {}
    if d and (now()-datetime.fromisoformat(d['published_at'].replace('Z','+00:00'))).total_seconds()>86400:item['status']='stale'
    p=d.get('probabilities')
    return state('fed',p['cut']-p['hike'] if p else None,
                 'Market-implied next-meeting distribution imported with source and publication time; not inferred from speeches.',[item],
                 market_probabilities=p,meeting_date=d.get('meeting_date'))

async def run(base):
    # Fetch different reporting cadences independently; never use revised data as
    # historical publication-time evidence without a separate vintage archive.
    codes=[('WALCL',14),('WRESBAL',14),('M2SL',75),('DGS2',5),('DGS10',5),('T10YIE',5),('VIXCLS',5),('BAMLH0A0HYM2',5),('UNRATE',75),('INDPRO',75)]
    values=await asyncio.gather(*(cadence_fred(c,age) for c,age in codes),prices('DX-Y.NYB','3mo'),prices('GC=F','3mo'),fed_state())
    macro=dict(zip([c for c,_ in codes],values[:len(codes)]));usd,gold,fed=values[-3:]
    by={f['name']:f for f in base['factors']}
    real=by['real_yield'];pos=by['positioning']
    engines=[state('real_yield',real['signal'],real['reason'],real['lineage'],**real['details'])]
    dx=change(usd,5,True)
    engines.append(state('usd',scaled(-dx,.5),'USD five-observation direction; capital-flow demand is not directly observed.',[usd],roc_5d_percent=dx))
    liq=change(macro['WALCL'],4,True)
    engines.append(state('liquidity',scaled(liq,2),'US Fed four-week balance-sheet proxy; global liquidity and collateral coverage remain incomplete.',[macro['WALCL']],
                         fed_assets_change_pct=liq,reserves_change_pct=change(macro['WRESBAL'],4,True),m2_change_pct=change(macro['M2SL'],3,True),scope='US proxy, not global aggregate'))
    bond=change(macro['DGS10'])
    engines.append(state('bond',scaled(-bond,.15),'Nominal yield momentum; Treasury fund flows are not inferred from prices.',[macro['DGS10']],
                         yield_change_pp=bond,us2y=macro['DGS2'].get('data'),flows=None))
    engines.append(fed)
    vx,cr=change(macro['VIXCLS']),change(macro['BAMLH0A0HYM2'])
    stress=None if vx is None or cr is None else float(np.clip((vx/4+cr/.15)/2,-1,1))
    engines.append(state('risk',stress,'VIX/credit stress proxy. Gold can be liquidated during funding shocks.',[macro['VIXCLS'],macro['BAMLH0A0HYM2']],vix_change=vx,credit_change_pp=cr))
    infl=change(macro['T10YIE'])
    engines.append(state('inflation',scaled(infl,.15),'Breakeven change is a conditional inflation-expectations proxy; relationship to gold is learned, not treated as a law.',[macro['T10YIE']],breakeven_change_pp=infl))
    un,ip=change(macro['UNRATE'],3),change(macro['INDPRO'],3,True)
    rec=None if un is None or ip is None else float(np.clip(un-ip*.1,-1,1))
    engines.append(state('recession',rec,'Unemployment/production slowdown proxy; not a recession probability.',[macro['UNRATE'],macro['INDPRO']],unemployment_change_pp=un,production_change_pct=ip))
    engines.append(state('positioning',pos['signal'],pos['reason'],pos['lineage'],resolution='weekly',**pos['details']))
    tech=change(gold,5,True)
    engines.append(state('technical',scaled(tech,2),'Five-observation gold momentum confirms state; it cannot bypass macro/model readiness gates.',[gold],roc_5d_percent=tech,atr=None,order_flow=None))
    return engines
