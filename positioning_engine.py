"""25% CFTC disaggregated futures-only managed-money COMEX gold crowding."""
import httpx
from core import source,factor,expired,now

URL='https://publicreporting.cftc.gov/resource/72hh-3qpy.json'
CONTRACT='088691'

def evaluate(snapshot):
    if not snapshot['data']:
        return factor('positioning',.25,None,'CFTC data unavailable.',[snapshot])
    rows=snapshot['data']['rows']
    # 156 prior observations, excluding the current report: no self-ranking.
    history=rows[-157:-1]; latest=rows[-1]
    if len(history)<156:
        return factor('positioning',.25,None,'Need 156 prior weekly observations plus latest report.',[snapshot],history=rows)
    current=latest['net']
    p=100*(sum(r['net']<current for r in history)+.5*sum(r['net']==current for r in history))/156
    signal=-(p-85)/15 if p>85 else (15-p)/15 if p<15 else 0
    # Crowding is reversal vulnerability, not proof that the trend is ending.
    return factor('positioning',.25,signal,
        f'Managed money net {current:,} contracts; percentile {p:.1f} against 156 prior reports. Extremes indicate contrarian vulnerability, not reversal timing.',
        [snapshot],percentile=p,net_contracts=current,long_contracts=latest['long'],short_contracts=latest['short'],
        observed_at=latest['date'],published_at=None,
        publication_note='COT normally reports Tuesday positions on Friday; actual delayed/holiday releases must be recorded for backtests.',
        history=rows[-157:],weekly_change=current-rows[-2]['net'],
        percentile_low=15,percentile_high=85,net_open_interest_ratio=latest['net']/latest['open_interest'] if latest['open_interest'] else None)

async def run():
    async def load():
        async with httpx.AsyncClient(timeout=25) as c:
            r=await c.get(URL,params={
                '$where':f"cftc_contract_market_code='{CONTRACT}' AND report_date_as_yyyy_mm_dd <= '{now().date()}T23:59:59'",
                '$select':'report_date_as_yyyy_mm_dd,m_money_positions_long_all,m_money_positions_short_all,open_interest_all',
                '$order':'report_date_as_yyyy_mm_dd DESC','$limit':180})
            r.raise_for_status(); raw=r.json()
        rows=[]
        for x in raw:
            long,short=int(x['m_money_positions_long_all']),int(x['m_money_positions_short_all'])
            if min(long,short)<0:raise ValueError('Negative gross positions')
            rows.append({'date':x['report_date_as_yyyy_mm_dd'][:10],'long':long,'short':short,
                         'net':long-short,'open_interest':int(x['open_interest_all'])})
        rows=sorted({r['date']:r for r in rows}.values(),key=lambda x:x['date'])
        if len(rows)<157:raise ValueError('CFTC history too short')
        if any(not 5<=(__import__('datetime').date.fromisoformat(b['date'])-__import__('datetime').date.fromisoformat(a['date'])).days<=9 for a,b in zip(rows[-157:],rows[-156:])):
            raise ValueError('Missing or irregular weekly history')
        return {'rows':rows,'observed_at':rows[-1]['date'],'contract':CONTRACT,'report':'Disaggregated Futures Only'}
    snapshot=await source('cot:gold:'+CONTRACT,URL,load,21600)
    if snapshot['data'] and expired(snapshot['data']['observed_at'],10):snapshot['status']='stale'
    return evaluate(snapshot)
