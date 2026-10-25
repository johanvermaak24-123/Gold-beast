"""Adversarial evidence, six independent horizons and capital-protection gates."""
import json
import os
from pathlib import Path
from datetime import timedelta
from core import now,iso,db
from probability_model import FEATURES,DRIVERS,HORIZONS,predict,stamp,conflict_pattern

IMPORTANCE={'real_yield':.30,'usd':.25,'fed':.15,'bond':.1,'liquidity':.08,
            'risk':.03,'inflation':.03,'recession':.02,'positioning':.03,'technical':.01}

def regime(engines):
    e={x['engine']:x.get('gold_support') for x in engines}
    tags=[]
    def v(k):return e.get(k) or 0
    if e.get('liquidity') is not None:tags.append('Liquidity Expansion' if v('liquidity')>.15 else 'Liquidity Contraction' if v('liquidity')<-.15 else 'Liquidity stable')
    if v('risk')>.85 and v('liquidity')<-.5:label='Panic'
    elif v('risk')>.7:label='Crisis'
    elif v('risk')<-.7 and v('technical')>.7:label='Euphoria'
    elif v('inflation')>.3 and v('recession')>.3:label='Stagflation'
    elif v('recession')>.5:label='Recession'
    elif v('inflation')>.3:label='Reflation'
    elif v('inflation')<-.3:label='Disinflation'
    else:label=tags[0] if tags else 'Insufficient data'
    return {'label':label,'tags':tags,'status':'heuristic candidate, not an established economic diagnosis',
            'probabilities':None,'note':'Preferred gold regimes are estimated from held-out historical samples when available.'}


def evidence(engines,narrative):
    usable=[x for x in engines if x['status']=='ok' and x['gold_support'] is not None]
    ranked=sorted(usable,key=lambda x:abs(x['gold_support'])*IMPORTANCE[x['engine']],reverse=True)
    case=lambda sign:[{'engine':x['engine'],'strength':abs(x['gold_support'])*IMPORTANCE[x['engine']],
                       'argument':x['reason'],'lineage':x['lineage']} for x in ranked if x['gold_support']*sign>.05]
    positive=sum(IMPORTANCE[x['engine']]*max(0,x['gold_support']) for x in usable)
    negative=sum(IMPORTANCE[x['engine']]*max(0,-x['gold_support']) for x in usable)
    mass=positive+negative
    severity=2*min(positive,negative)/mass if mass else 0
    # Search existing verified article archive for contradicting core narratives;
    # geopolitical-only stories do not enter the directional model.
    allowed={'FED_HAWKISH','FED_DOVISH','DOLLAR_STRENGTH','DOLLAR_WEAKNESS','DEBT_DEBASEMENT','FISCAL_CREDIBILITY'}
    articles=[a for a in narrative.get('details',{}).get('articles',[]) if (a.get('label') or {}).get('regime') in allowed]
    return {'bull_case':case(1),'bear_case':case(-1),'conflict_severity':round(severity,4),
            'strongest_bull_argument':case(1)[0]['argument'] if case(1) else 'No verified supporting driver.',
            'strongest_bear_argument':case(-1)[0]['argument'] if case(-1) else 'No verified supporting driver.',
            'counterevidence_articles':articles[:20],
            'contradiction_policy':'Opposing measured drivers lower confidence. A supported out-of-sample conditional distribution may resolve conflicts; reasoning alone cannot raise probability.'}


def execution_state():
    path=Path(os.getenv('DATA_DIR','data'))/'market_quote.json'
    try:
        q=json.loads(path.read_text());t=stamp(q['timestamp']);age=(now()-t).total_seconds()
        if q.get('symbol')!='XAUUSD' or not q.get('source_url'):raise ValueError('Missing quote identity/source')
        bid,ask=float(q['bid']),float(q['ask'])
        if not 0<bid<=ask or not all(__import__('math').isfinite(x) for x in (bid,ask)):raise ValueError('Invalid quote')
        spread=(ask-bid)/((ask+bid)/2)
        ready=0<=age<=60 and q.get('market_open') is True and spread<=.0005
        return {'ready':ready,'quote':q,'age_seconds':age,'spread_fraction':spread,
                'reason':'Fresh open-market quote with spread within threshold.' if ready else 'Closed/stale market or spread exceeds 5bp; no immediate entry.'}
    except Exception:
        return {'ready':False,'quote':None,'reason':'No verified <=60-second open-market XAUUSD quote. No broker connection or execution is implemented.'}


def confidence(probabilities,driver_paths,conflict,coverage):
    directional=max(probabilities['bull'],probabilities['bear'])
    expected={k:v['bull']-v['bear'] for k,v in driver_paths.items()}
    # Gold-supportive alignments: USD down, real yields down, expected Fed rates down.
    core=[-expected[k] for k in ('usd','real_yield','fed')]
    winning=1 if probabilities['bull']>probabilities['bear'] else -1
    aligned=all(x*winning>.1 for x in core)
    cap=95 if aligned else 85
    return round(min(cap,directional*100*(1-conflict)*coverage),1)


def intraday_override(engines):
    path=Path(os.getenv('DATA_DIR','data'))/'intraday_features.json'
    if not path.exists():return engines
    try:
        d=json.loads(path.read_text());items=d['engines'];by={e['engine']:e for e in items}
        if set(by)!=set(FEATURES):raise ValueError('All features required')
        output=[]
        for name in FEATURES:
            x=by[name];t=stamp(x['known_at']);age=(now()-t).total_seconds();signal=float(x['gold_support'])
            if not 0<=age<=900 or not -1<=signal<=1 or not x['source_url']:raise ValueError('Invalid intraday lineage/freshness')
            output.append({'engine':name,'status':'ok','gold_support':signal,'reason':x['reason'],
                           'resolution':'intraday','metrics':{},'lineage':[{'source':x['source_url'],'status':'ok','fetched_at':t.isoformat()}]})
        return output
    except Exception:return engines


def forecast(engines,review,current_regime,execution,horizon):
    missing=[x['engine'] for x in engines if x['status']!='ok' or x['gold_support'] is None]
    path=Path(os.getenv('MODEL_DIR',str(Path(os.getenv('DATA_DIR','data'))/'models')))/(horizon+'.json')
    output={'horizon':horizon,'decision':'NO TRADE','confidence':0,'probabilities':None,'driver_paths':None,
            'forecast_quality':'C','status':'unavailable','reasons':[],'asymmetry':None}
    if missing:output['reasons'].append('Missing drivers: '+', '.join(missing))
    if horizon in {'1h','4h'} and any(e['resolution']!='intraday' for e in engines):
        output['reasons'].append('Intraday feature set not connected; daily/weekly states cannot pass the intraday readiness gate.')
    if not path.exists():output['reasons'].append('No fitted chronological model artifact for '+horizon)
    if output['reasons']:return output
    try:
        artifact=json.loads(path.read_text())
        if artifact['horizon']!=horizon:raise ValueError('Horizon mismatch')
        if not 0<=(now()-stamp(artifact['trained_at'])).total_seconds()<=90*86400:
            raise ValueError('Model older than 90 days or from future')
        features={x['engine']:x['gold_support'] for x in engines}
        result=predict(artifact,features)
        output.update(result)
        output['model_id']=artifact['dataset_sha256'];output['validation']=artifact['validation']
        output['status']='validated_holdout' if artifact['validation']['eligible'] else 'unvalidated'
        output['probability_note']='Model estimates from a single chronological holdout; not guaranteed accuracy or causal capital flows.'
        if not artifact['validation']['eligible']:output['reasons'].append('Gold or driver models failed predeclared held-out Brier/calibration criteria.')
        if result['support_failures']:output['reasons'].append('Current state outside analog support: '+', '.join(result['support_failures']))
        p=result['probabilities'];direction='BUY' if p['bull']>p['bear'] else 'SELL'
        winner=max(p['bull'],p['bear']);edge=winner-max(p['range'],min(p['bull'],p['bear']))
        conf=confidence(p,result['driver_paths'],review['conflict_severity'],1)
        output['confidence']=conf
        if winner<.6 or edge<.15:output['reasons'].append('Directional probability/advantage below .60/.15 thresholds.')
        if review['conflict_severity']>.5:output['reasons'].append('Driver conflict severity exceeds .50.')
        if conf<55:output['reasons'].append('Conflict-adjusted confidence below 55%.')
        a=result['asymmetry'];mean=a['expected_return']*(1 if direction=='BUY' else -1)
        if mean<=.001:output['reasons'].append('Historical analog expected direction return does not exceed a conservative 10bp cost hurdle.')
        core={e['engine']:e['gold_support'] for e in engines}
        if abs(core['real_yield'])>.7 and core['real_yield']*(1 if direction=='BUY' else -1)<0:
            output['reasons'].append('Strong real-yield state opposes directional trade; technical confirmation cannot override it.')
        if not execution['ready']:output['reasons'].append(execution['reason'])
        # No decision without all gates; probabilities can remain visible as research estimates.
        if not output['reasons']:
            output['decision']=direction
            output['forecast_quality']='A+' if conf>85 else 'A' if conf>=75 else 'B'
        stats=artifact.get('regime_history',{}).get(current_regime['label'])
        output['historical_regime_evidence']=stats if stats and stats['n']>=30 else {'status':'Insufficient held-out regime observations'}
        conflict_stats=artifact.get('conflict_history',{}).get(conflict_pattern(features))
        output['historical_conflict_evidence']=conflict_stats if conflict_stats and conflict_stats['n']>=30 else {'status':'Insufficient held-out observations for this USD/real-yield/Fed pattern'}
        output['trade_location']='Unavailable: no verified entry-location model or intraday structure.'
        output['why_winner_wins']='Conditional driver forecasts and held-out gold analogs favor this direction, subject to every gate.' if output['decision']!='NO TRADE' else 'No side survives every validation, conflict, data and execution gate.'
    except Exception as exc:
        output['status']='unavailable';output['reasons'].append('Model rejected: '+type(exc).__name__)
        output['probabilities']=None;output['driver_paths']=None;output['confidence']=0
    return output


def build_report(engines,base):
    engines=intraday_override(engines)
    narrative=next(f for f in base['factors'] if f['name']=='narrative')
    review=evidence(engines,narrative);reg=regime(engines);execution=execution_state()
    horizons={h:forecast(engines,review,reg,execution,h) for h in HORIZONS}
    # Immediate entry uses 1h model; longer views never substitute for unavailable intraday evidence.
    immediate=horizons['1h']
    report={'title':'GOLD INTELLIGENCE REPORT','version':'2.0','generated_at':iso(),
            'current_regime':reg,'engines':engines,'review':review,'horizons':horizons,
            'execution':execution,'final_decision':immediate['decision'],'confidence':immediate['confidence'],
            'confidence_label':'Directional model confidence; not confidence in abstaining.',
            'reason':immediate['reasons'][0] if immediate['reasons'] else immediate['why_winner_wins'],
            'fund_consensus':{'status':'Unavailable: cannot infer decisions of 20 named macro funds without position/decision data.',
                'buy_gold':None,'sell_gold':None,'buy_usd':None,'buy_treasuries':None,'neutral':None},
            'invalidation':['USD/real-yield/Fed path forecasts change direction or become unsupported.',
                'A primary data source becomes stale or revised outside the training distribution.',
                'Funding stress causes gold liquidation despite supportive long-term drivers.',
                'Hold-out calibration degrades in prospective monitoring.',
                'Tradeable quotes, spreads or market status fail the execution gate.'],
            'disclaimer':'No forecast is guaranteed. Missing probabilities are unavailable, not 0%. Confidence is not a win probability. No trade execution.'}
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS reports (generated_at TEXT PRIMARY KEY, body TEXT)')
        c.execute('INSERT OR REPLACE INTO reports VALUES (?,?)',(report['generated_at'],json.dumps(report,allow_nan=False)))
    return report
