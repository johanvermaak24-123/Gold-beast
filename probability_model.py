"""Transparent analog distributions with chronological calibration and test gates.

No pretrained market model or numeric trading probabilities are bundled.
"""
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np

FEATURES=['real_yield','usd','liquidity','bond','fed','risk','inflation','recession','positioning','technical']
DRIVERS=['usd','real_yield','treasury','fed','liquidity']
TARGETS=DRIVERS+['gold']
HORIZONS=['1h','4h','24h','5d','20d','60d']
CLASSES=['bear','range','bull']
VERSION='driver-analog-v2'

def conflict_pattern(features):
    return '|'.join(k+(':+ ' if float(features[k])>.1 else ':- ' if float(features[k])<-.1 else ':0 ').strip() for k in ('usd','real_yield','fed'))

def stamp(value):
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if not t.tzinfo:raise ValueError('All timestamps require timezone')
    return t

def tempered(p,t):
    z=np.log(np.maximum(np.asarray(p),1e-9))/t
    z-=z.max(axis=-1,keepdims=True)
    q=np.exp(z);return q/q.sum(axis=-1,keepdims=True)

def brier(p,y):return float(np.mean(np.sum((p-np.eye(3)[y])**2,axis=1)))
def calibration_error(p,y):
    # Top-label expected calibration error, fixed ten bins.
    certainty=p.max(axis=1);correct=(p.argmax(axis=1)==y).astype(float)
    total=0
    for lo in np.arange(0,1,.1):
        mask=(certainty>=lo)&(certainty<lo+.1 if lo<.9 else certainty<=1)
        if mask.any():total+=mask.mean()*abs(correct[mask].mean()-certainty[mask].mean())
    return float(total)

def raw_predict(model,x,temperature=True):
    x=np.asarray(x,float)
    if x.ndim==1:x=x[None,:]
    z=(x-np.asarray(model['mean']))/np.asarray(model['scale'])
    train=np.asarray(model['x']);ys=np.asarray(model['y']);out=[];nearest=[]
    for row in z:
        distance=np.sqrt(np.mean((train-row)**2,axis=1));k=min(model['k'],len(train))
        ids=np.argsort(distance)[:k]
        weights=1/np.maximum(distance[ids],.05)
        count=np.array([weights[ys[ids]==i].sum() for i in range(3)])+1
        out.append(count/count.sum());nearest.append(float(distance.min()))
    p=np.asarray(out)
    return (tempered(p,model['temperature']) if temperature else p),np.asarray(nearest)

def fit_analog(x,y,calx,caly):
    x=np.asarray(x,float);y=np.asarray(y,int)
    mean=x.mean(axis=0);scale=np.maximum(x.std(axis=0),.05)
    z=(x-mean)/scale
    model={'mean':mean.tolist(),'scale':scale.tolist(),'x':z.tolist(),'y':y.tolist(),'k':31,'temperature':1.0}
    p,_=raw_predict(model,calx,False)
    # Calibration segment only; no temperature selection on final test data.
    model['temperature']=float(min([.7,1,1.5,2,3],key=lambda t:brier(tempered(p,t),caly)))
    prior=(np.bincount(y,minlength=3)+1)/(len(y)+3)
    model['prior']=prior.tolist()
    model['support_radius']=2.0  # Predeclared standardised RMS distance gate.
    return model

def metrics(model,x,y):
    p,_=raw_predict(model,x);base=np.tile(model['prior'],(len(y),1))
    return {'n_test':len(y),'brier':brier(p,y),'baseline_brier':brier(base,y),'ece':calibration_error(p,y),
            'class_counts':np.bincount(y,minlength=3).tolist(),
            'accepted':bool(len(y)>=100 and min(np.bincount(y,minlength=3))>=20 and
                            brier(p,y)<brier(base,y)-.01 and calibration_error(p,y)<=.10)}

def gold_features(driver_models,x):
    # All driver probabilities come from models trained earlier than the gold
    # training segment. No in-sample fitted driver outcomes enter gold features.
    expectations=[]
    for name in DRIVERS:
        p,_=raw_predict(driver_models[name],x);expectations.append(p[:,2]-p[:,0])
    return np.column_stack(expectations+[x[:,i] for i in (5,6,7,8,9)])

def validate_rows(rows,horizon):
    if horizon not in HORIZONS:raise ValueError('Unsupported horizon')
    timestamps=[]
    for row in rows:
        t=stamp(row['timestamp']);known=stamp(row['features_known_at']);outcome=stamp(row['outcomes_known_at'])
        if known>t or outcome<=t or outcome>datetime.now(timezone.utc):raise ValueError('Point-in-time violation')
        if row['horizon']!=horizon:raise ValueError('Mixed horizons')
        if not row['source_manifest'] or not row['regime']:raise ValueError('Source manifest and historical regime required')
        for key in FEATURES:
            if not np.isfinite(float(row[key])) or not -1<=float(row[key])<=1:raise ValueError('Invalid feature')
        for target in TARGETS:
            if row[target+'_label'] not in CLASSES:raise ValueError('Unknown target class')
        if not np.isfinite(float(row['gold_return'])):raise ValueError('Invalid return')
        timestamps.append(t)
    if any(b<=a for a,b in zip(timestamps,timestamps[1:])):raise ValueError('Rows must have unique, strictly increasing decision timestamps')


def train(rows,horizon):
    validate_rows(rows,horizon)
    if len(rows)<1200:raise ValueError('At least 1200 point-in-time rows required per horizon')
    n=len(rows);cuts=[int(n*f) for f in (.3,.4,.6,.8)]
    boundaries=[0]+cuts+[n]
    segments=[]
    for j,(a,b) in enumerate(zip(boundaries,boundaries[1:])):
        cutoff=stamp(rows[b]['timestamp']) if b<n else datetime.now(timezone.utc)
        segment=[r for r in rows[a:b] if stamp(r['outcomes_known_at'])<cutoff]
        if len(segment)<60:raise ValueError('Insufficient purged segment')
        segments.append(segment)
    drtrain,drcal,gtrain,gcal,test=segments
    matrix=lambda rs:np.array([[float(r[k]) for k in FEATURES] for r in rs])
    labels=lambda rs,t:np.array([CLASSES.index(r[t+'_label']) for r in rs])
    dx,dc,gx,gc,tx=map(matrix,segments)
    driver_models={}
    driver_tests={}
    for target in DRIVERS:
        model=fit_analog(dx,labels(drtrain,target),dc,labels(drcal,target))
        driver_models[target]=model
        driver_tests[target]=metrics(model,tx,labels(test,target))
    goldx=gold_features(driver_models,gx);goldcal=gold_features(driver_models,gc);goldtest=gold_features(driver_models,tx)
    gold=fit_analog(goldx,labels(gtrain,'gold'),goldcal,labels(gcal,'gold'))
    result=metrics(gold,goldtest,labels(test,'gold'))
    gold['returns']=[float(r['gold_return']) for r in gtrain]
    regime_history={}
    for name in sorted(set(r['regime'] for r in test)):
        subset=[r for r in test if r['regime']==name]
        regime_history[name]={'n':len(subset),'gold_mean_return':float(np.mean([float(r['gold_return']) for r in subset])),
                              'observed_class_frequencies':dict(zip(CLASSES,(np.bincount(labels(subset,'gold'),minlength=3)/len(subset)).tolist()))}
    conflict_history={}
    for pattern in sorted(set(conflict_pattern(r) for r in test)):
        subset=[r for r in test if conflict_pattern(r)==pattern]
        conflict_history[pattern]={'n':len(subset),'gold_mean_return':float(np.mean([float(r['gold_return']) for r in subset])),
            'class_frequencies':dict(zip(CLASSES,(np.bincount(labels(subset,'gold'),minlength=3)/len(subset)).tolist()))}
    return {'version':VERSION,'horizon':horizon,'trained_at':datetime.now(timezone.utc).isoformat(),
            'latest_outcome_at':max(stamp(r['outcomes_known_at']) for r in rows).isoformat(),
            'dataset_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),
            'features':FEATURES,'classes':CLASSES,'driver_models':driver_models,'gold_model':gold,
            'validation':{'gold':result,'drivers':driver_tests,'segments':[len(s) for s in segments],
                          'eligible':bool(result['accepted'] and all(v['accepted'] for v in driver_tests.values())),
                          'warning':'Single chronological holdout; eligibility is not proof of profitability or causal flow prediction.'},
            'regime_history':regime_history,'conflict_history':conflict_history}


def predict(artifact,features):
    if artifact.get('version')!=VERSION or artifact.get('features')!=FEATURES:raise ValueError('Model schema mismatch')
    x=np.array([[features[k] for k in FEATURES]],float)
    if not np.isfinite(x).all():raise ValueError('Missing/nonfinite features')
    drivers={};unsupported=[]
    for name,model in artifact['driver_models'].items():
        p,d=raw_predict(model,x);drivers[name]=dict(zip(CLASSES,p[0].tolist()))
        if d[0]>model['support_radius']:unsupported.append(name)
    gx=gold_features(artifact['driver_models'],x)
    p,d=raw_predict(artifact['gold_model'],gx)
    model=artifact['gold_model'];z=(gx[0]-model['mean'])/model['scale']
    distance=np.sqrt(np.mean((np.asarray(model['x'])-z)**2,axis=1));ids=np.argsort(distance)[:model['k']]
    returns=np.asarray(model['returns'])[ids]
    q=np.quantile(returns,[.1,.5,.9]);up=max(0,float(q[2]));down=max(0,-float(q[0]))
    if d[0]>model['support_radius']:unsupported.append('gold')
    return {'probabilities':dict(zip(CLASSES,p[0].tolist())),'driver_paths':drivers,
            'support_failures':unsupported,'analog_count':len(ids),
            'asymmetry':{'q10_return':float(q[0]),'median_return':float(q[1]),'q90_return':float(q[2]),
                         'upside':up,'downside':down,'upside_downside_ratio':up/down if down>0 else None,
                         'expected_return':float(returns.mean()),
                         'label':'Unweighted historical analog distribution, not a stop/target or guaranteed reward:risk'}}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('csv');parser.add_argument('--horizon',required=True,choices=HORIZONS);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    with open(args.csv) as stream:rows=list(csv.DictReader(stream))
    artifact=train(rows,args.horizon);Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(artifact,allow_nan=False))
    print(json.dumps(artifact['validation'],indent=2))
