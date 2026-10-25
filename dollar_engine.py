"""DXY breakout only when five-session USD and real-yield directions diverge."""
import asyncio
from real_yield_engine import prices
from core import factor


def evaluate(dxy,cnh,real):
    if not dxy['data'] or real['status']!='ok':
        return factor('dollar',.10,None,'DXY or real-yield comparison unavailable.',[dxy,cnh])
    rows=dxy['data']['rows']; values=[r['value'] for r in rows]
    high=max(values[-21:-1]); low=min(values[-21:-1]); latest=values[-1]
    roc=(latest/values[-6]-1)*100
    dy=real['details']['five_session_change_bp']
    divergent=roc*dy<0 and abs(roc)>.1 and abs(dy)>1
    breakout=latest>high; breakdown=latest<low
    signal=(-1 if breakout else 1 if breakdown else 0) if divergent else 0
    # CNH is context. Its availability does not gate DXY scoring.
    result=factor('dollar',.10,signal,
        'DXY uses previous 20 daily closes (excluding latest); factor fires only when five-session dollar and real yields move in opposite directions.',
        [dxy],dxy=latest,roc_5d_percent=roc,prior_20d_high=high,prior_20d_low=low,
        breakout=breakout,breakdown=breakdown,yield_divergence=divergent,
        usd_cnh=cnh['data']['rows'][-1]['value'] if cnh['data'] else None,
        cnh_lineage=cnh,observed_at=rows[-1]['date'])
    return result

async def run(real):
    dxy,cnh=await asyncio.gather(prices('DX-Y.NYB','3mo'),prices('CNH=X','3mo'))
    return evaluate(dxy,cnh,real)
