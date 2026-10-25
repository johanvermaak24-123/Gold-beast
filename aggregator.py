"""Fixed-weight regime state, agreement confidence, and explicit divergences."""
from core import iso
WEIGHTS={'real_yield':.35,'positioning':.25,'flows':.20,'dollar':.10,'narrative':.10}

def aggregate(factors):
    by={f['name']:f for f in factors}
    usable=[f for f in factors if f['status']=='ok' and f['signal'] is not None]
    coverage=sum(WEIGHTS[f['name']] for f in usable)
    score=sum(WEIGHTS[f['name']]*f['signal'] for f in usable)
    active=[f for f in usable if abs(f['signal'])>.05]
    signed=sum(1 if f['signal']>0 else -1 for f in active)
    # Equal-factor directional agreement: 3 vs 2 = 20%, all 5 = 100%.
    agreement=abs(signed)/len(active) if active else 0
    confidence=round(min(85,100*agreement*coverage),1)
    ry=by['real_yield']['signal'];narr=by['narrative']['signal']
    alerts=[]
    def alert(kind,message,names):
        alerts.append({'type':kind,'message':message,'factors':names,
                       'lineage':{k:by[k]['lineage'] for k in names},'detected_at':iso()})
    conflict=ry is not None and narr is not None and abs(ry)>.7 and abs(narr)>.5 and ry*narr<0
    if conflict:
        alert('REGIME_DIVERGENCE',f'Real-yield macro is {"bullish" if ry>0 else "bearish"}; narrative is {"bullish" if narr>0 else "bearish"}. Research posture: fade the narrative, respect macro. This is a hypothesis, not an order.', ['real_yield','narrative'])
    flow=by['flows']['details']
    if ry is not None and ry<-.2 and flow.get('central_bank_buying'):
        alert('STRUCTURAL_DIVERGENCE','Real yields rising while reported central banks buy: candidate structural support, not proof of a floor.',['real_yield','flows'])
    if flow.get('structural_divergence'):
        alert('FLOW_DIVERGENCE','Two-quarter central-bank buying coexists with ETF holdings outflows.',['flows'])
    percentile=by['positioning']['details'].get('percentile')
    if narr is not None and narr<-.5 and percentile is not None and percentile<15 and by['positioning']['status']=='ok':
        alert('CONTRARIAN_RISK','Bearish narrative cluster with washed-out managed money. No narrative historical percentile is claimed.',['positioning','narrative'])
    ready=by['real_yield']['status']=='ok' and by['positioning']['status']=='ok' and coverage>=.6
    bias='Bullish' if score>.15 else 'Bearish' if score<-.15 else 'Neutral'
    label='Divergent / Stand Aside' if conflict else ('Real Yield Dominant / '+('Bullish' if ry>0 else 'Bearish')) if ry is not None and abs(ry)>.7 else 'Mixed / '+bias
    # If the weighted result conflicts with a strong real-yield signal, surface it.
    if ry is not None and abs(ry)>.7 and score*ry<0:
        label='Divergent / Stand Aside'
        alert('AGGREGATE_CONFLICT','Weighted total conflicts with a strong real-yield factor; no directional desk bias issued.',['real_yield'])
        bias='Divergent'
    if not ready:label='Incomplete / Insufficient data';bias='Unavailable';confidence=0
    dominant=max(usable,key=lambda f:abs(WEIGHTS[f['name']]*f['signal']))['name'] if usable else None
    return {'regime_label':label,'bias':bias,'final_score':round(score,4),'confidence':confidence,
            'confidence_label':'Legacy agreement × available weight, capped at 85%; not a probability of profit',
            'coverage_percent':round(coverage*100),'dominant_driver':dominant,'factors':factors,
            'divergences':alerts,'generated_at':iso(),'model_version':'regime-terminal-1.0',
            'disclaimer':'Decision support only. These relationships and thresholds need out-of-sample validation; no price prediction or trade execution.'}
