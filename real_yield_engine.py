"""35% real-yield factor. Daily observed state, not an intraday prediction."""
import asyncio
import csv
import io
import os
from datetime import timedelta
import httpx
import numpy as np
from core import now,source,factor,expired

async def fred(series,days=800,min_points=30):
    async def load():
        async with httpx.AsyncClient(timeout=20,follow_redirects=True) as client:
            start=str(now().date()-timedelta(days=days))
            if os.getenv('FRED_API_KEY'):
                r=await client.get('https://api.stlouisfed.org/fred/series/observations',params={
                    'series_id':series,'api_key':os.environ['FRED_API_KEY'],'file_type':'json',
                    'observation_start':start})
                r.raise_for_status()
                values=[{'date':x['date'],'value':x['value']} for x in r.json()['observations']]
                mode='FRED API latest vintage'
            else:
                r=await client.get('https://fred.stlouisfed.org/graph/fredgraph.csv',params={'id':series,'cosd':start})
                r.raise_for_status()
                values=[{'date':x.get('observation_date') or x.get('DATE'),'value':x[series]}
                        for x in csv.DictReader(io.StringIO(r.text))]
                mode='FRED public CSV latest vintage'
        rows=[]
        for x in values:
            try:
                value=float(x['value'])
                if np.isfinite(value) and x['date']<=str(now().date()):rows.append({'date':x['date'],'value':value})
            except (TypeError,ValueError):pass
        rows.sort(key=lambda x:x['date'])
        if len(rows)<min_points: raise ValueError('Insufficient yield history')
        return {'rows':rows,'mode':mode,'observed_at':rows[-1]['date'],'units':'percent yield',
                'published_at':None,'publication_note':'Observation date is not a release timestamp.'}
    result=await source('fred:'+series,'https://fred.stlouisfed.org/series/'+series,load,3600)
    if result['data'] and expired(result['data']['observed_at'],5): result['status']='stale'
    return result

async def prices(symbol,period='2y'):
    async def load():
        def sync():
            import yfinance as yf
            frame=yf.Ticker(symbol).history(period=period,auto_adjust=False,timeout=12)
            rows=[{'date':str(i.date()),'value':float(v)} for i,v in frame['Close'].dropna().items() if np.isfinite(v) and v>0]
            if len(rows)<25:raise ValueError('Insufficient prices')
            return {'rows':rows,'symbol':symbol,'observed_at':rows[-1]['date'],
                    'quote_type':'daily close; latest candle may be incomplete','published_at':None}
        return await asyncio.to_thread(sync)
    result=await source('prices:'+symbol+':'+period,'https://finance.yahoo.com/quote/'+symbol,load,900)
    if result['data'] and expired(result['data']['observed_at'],5):result['status']='stale'
    return result

def evaluate(nominal,real,gold):
    lineage=[real]
    if not real['data']:
        return factor('real_yield',.35,None,'10Y TIPS unavailable.',lineage,valuation=None)
    rows=real['data']['rows']
    values=[r['value'] for r in rows]
    change=values[-1]-values[-6]
    momentum=values[-1]-values[-2]
    acceleration=momentum-(values[-2]-values[-3])
    # 15bp over five observed sessions saturates the heuristic factor.
    signal=float(np.clip(-change/.15,-1,1))
    valuation=None
    if gold['data']:
        y={r['date']:r['value'] for r in rows}
        g={r['date']:r['value'] for r in gold['data']['rows']}
        dates=sorted(set(y)&set(g))
        if len(dates)>=253:
            train=dates[-253:-1]; test=dates[-1]
            X=np.column_stack((np.ones(len(train)),[y[d] for d in train]))
            logg=np.log([g[d] for d in train])
            beta=np.linalg.lstsq(X,logg,rcond=None)[0]
            residuals=logg-X@beta
            std=float(np.std(residuals,ddof=2))
            fitted=float(np.exp(beta[0]+beta[1]*y[test]))
            valuation={'label':'Conditional 252-observation regression reference, NOT intrinsic fair value',
                       'instrument':'GC=F gold futures proxy','training_end':train[-1],'test_date':test,
                       'reference_price':fitted,'deviation_percent':(g[test]/fitted-1)*100,
                       'residual_z':float((np.log(g[test])-np.log(fitted))/std) if std>1e-9 else None,
                       'slope':float(beta[1]),'used_for_signal':False,
                       'warning':'Levels regression may be spurious or unstable; roll/structural breaks matter.'}
    return factor('real_yield',.35,signal,
        f'10Y real yield changed {change*100:+.1f} bp over five observations. Rising real yields increase the opportunity cost of gold.',
        lineage,real_yield=values[-1],nominal_yield=nominal['data']['rows'][-1]['value'] if nominal['data'] else None,
        five_session_change_bp=change*100,momentum_bp=momentum*100,acceleration_bp=acceleration*100,
        valuation=valuation,valuation_lineage=gold,nominal_lineage=nominal,observed_at=rows[-1]['date'])

async def run():
    nominal,real,gold=await asyncio.gather(fred('DGS10'),fred('DFII10'),prices('GC=F'))
    # Nominal is explanatory context: an outage must not invalidate available TIPS.
    result=evaluate(nominal,real,gold)
    result['status']='ok' if real['status']=='ok' else real['status']
    if result['status']=='ok' and result['signal'] is None:
        result['signal']=float(np.clip(-result['details']['five_session_change_bp']/15,-1,1))
    if result['status']!='ok':result['signal']=None
    return result
