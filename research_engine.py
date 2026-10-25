"""Reproducible daily-close research; never an executable entry model.

Uses latest-vintage FRED history and continuous futures: retrospective proxy
research, NOT a point-in-time reconstruction. No intraday extrapolation.
"""
import asyncio
import hashlib
import json
import numpy as np
from core import iso, now
from real_yield_engine import fred, prices

HORIZONS = {'24h': 1, '5d': 5, '20d': 20, '60d': 60}
FEATURES = ['real_yield_change_5', 'real_yield_change_20', 'usd_return_5',
            'usd_return_20', 'nominal_change_5', 'gold_return_20', 'gold_vol_20']
CLASSES = ['bear', 'range', 'bull']

def dataset(real, usd, nominal, gold):
    tables = [{r['date']: float(r['value']) for r in rows} for rows in (real, usd, nominal, gold)]
    dates = sorted(set.intersection(*(set(t) for t in tables)))
    values = np.array([[t[d] for t in tables] for d in dates])
    if len(dates) < 850: raise ValueError('At least 850 common daily observations required')
    # Lag macro inputs by TWO common observations to reduce same-day publication
    # lookahead. This does not remove latest-vintage revision bias.
    x, indices = [], []
    for i in range(62, len(dates)):
        j = i - 2
        v = values
        returns = np.diff(np.log(v[i-21:i+1, 3]))
        x.append([v[j,0]-v[j-5,0], v[j,0]-v[j-20,0],
                  np.log(v[j,1]/v[j-5,1]), np.log(v[j,1]/v[j-20,1]),
                  v[j,2]-v[j-5,2], np.log(v[i,3]/v[i-20,3]), np.std(returns)])
        indices.append(i)
    return dates, values, np.array(x), np.array(indices)

def analog(train_x, train_y, query):
    scale = np.maximum(train_x.std(axis=0), 1e-7)
    distances = np.sqrt(np.mean(((train_x-query)/scale)**2, axis=1))
    ids = np.argsort(distances)[:min(61, len(distances))]
    # Equal-weight smoothed counts, no in-sample calibration claim.
    counts = np.bincount(train_y[ids], minlength=3) + 1
    return counts / counts.sum(), ids, float(distances[ids].mean())

def evaluate(dates, values, x, indices, horizon):
    h = HORIZONS[horizon]
    observed = indices + h < len(dates)
    train_indices = indices[observed]
    features = x[observed]
    returns = values[train_indices+h,3]/values[train_indices,3]-1
    threshold = .005*np.sqrt(h)
    y = np.where(returns > threshold, 2, np.where(returns < -threshold, 0, 1))
    losses, baselines, correct, records = [], [], [], []
    # Fixed rule, expanding window; purge every training target not known at
    # test decision. Test origins h observations apart avoid overlapping targets.
    start = max(500, len(y)-500)
    for t in range(start, len(y), h):
        eligible = np.flatnonzero(train_indices[:t]+h < train_indices[t])
        if len(eligible) < 400: continue
        p, _, _ = analog(features[eligible], y[eligible], features[t])
        prior = (np.bincount(y[eligible], minlength=3)+1)/(len(eligible)+3)
        target = np.eye(3)[y[t]]
        losses.append(float(np.sum((p-target)**2)))
        baselines.append(float(np.sum((prior-target)**2)))
        correct.append(int(p.argmax()==y[t]))
        records.append({'date': dates[train_indices[t]], 'outcome_date': dates[train_indices[t]+h],
                        'probabilities': dict(zip(CLASSES,p.tolist())), 'actual': CLASSES[y[t]]})
    eligible = np.flatnonzero(train_indices+h < indices[-1])
    p, ids, distance = analog(features[eligible], y[eligible], x[-1])
    comparable = returns[eligible][ids]
    brier = float(np.mean(losses)) if losses else None
    baseline = float(np.mean(baselines)) if baselines else None
    passed = len(losses)>=100 and brier < baseline-.01
    return {'status': 'retrospective_research_only', 'decision': 'NO TRADE',
            'probabilities': dict(zip(CLASSES, p.tolist())),
            'research_bias': CLASSES[int(p.argmax())],
            'observed_at': dates[-1], 'sessions': h, 'range_threshold_return': float(threshold),
            'analog_count': len(ids), 'mean_standardized_distance': distance,
            'return_distribution': dict(zip(['p10','median','p90'],np.quantile(comparable,[.1,.5,.9]).tolist())),
            'validation': {'test_count':len(losses), 'brier':brier, 'baseline_brier':baseline,
                           'beats_baseline_gate':bool(passed), 'accuracy':float(np.mean(correct)) if correct else None,
                           'nonoverlapping_outcomes':True,'training_target_purge':True,
                           'method':'Fixed 61-neighbor expanding-window walk-forward; no tuning on holdout.',
                           'limitations':'Latest-vintage inputs, futures rolls, no transaction costs; no proven live calibration.'},
            'recent_tests': records[-12:]}

def build(real, usd, nominal, gold):
    dates, values, x, indices = dataset(real, usd, nominal, gold)
    return {'status':'ok','version':'daily-research-v3','built_at':iso(), 'observed_at':dates[-1],
            'instrument':'GC=F continuous gold futures proxy, not XAUUSD spot',
            'usd_proxy':'Yahoo DX-Y.NYB dollar index daily-close proxy',
            'features':FEATURES,'observations':len(dates),
            'dataset_sha256':hashlib.sha256(json.dumps([dates,values.tolist()]).encode()).hexdigest(),
            'warning':'Experimental retrospective estimates, not validated live probabilities. Daily closes cannot forecast the next hour. Historical analogs may fail after regime changes.',
            'horizons':{name:evaluate(dates,values,x,indices,name) for name in HORIZONS},
            'market':{'gold_close':float(values[-1,3]),'gold_change_percent':float((values[-1,3]/values[-2,3]-1)*100),
                      'real_yield_percent':float(values[-1,0]),'nominal_yield_percent':float(values[-1,2]),
                      'broad_usd_index':float(values[-1,1])}}

async def run():
    sources = await asyncio.gather(fred('DFII10',6000),prices('DX-Y.NYB','10y'),
                                   fred('DGS10',6000),prices('GC=F','10y'))
    lineage = [{k:v for k,v in s.items() if k!='data'} | {'observed_at':(s.get('data') or {}).get('observed_at')} for s in sources]
    if any(s['status']!='ok' or not s.get('data') for s in sources):
        return {'status':'unavailable','reason':'Daily research requires fresh TIPS, DXY, nominal yield and gold histories.','lineage':lineage}
    try:
        rows = [[r for r in s['data']['rows'] if r['date'] < str(now().date())] for s in sources]
        result = await asyncio.to_thread(build,*rows)
        result['lineage']=lineage
        return result
    except Exception as exc:
        return {'status':'unavailable','reason':str(exc),'lineage':lineage}
