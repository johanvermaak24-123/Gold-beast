"""Optional observations; never silently substitute partial inputs into factors."""
import asyncio
import re
from flow_engine import etf
from news_sources import fetch_news
from narrative_cluster_engine import densities

PATTERNS = {
 'FED_HAWKISH':r'\bhawkish\b|higher for longer|\brate hikes?\b',
 'FED_DOVISH':r'\bdovish\b|\brate cuts?\b',
 'INFLATION_HOT':r'hot (?:cpi|inflation)|inflation (?:rises|rising|accelerates)',
 'INFLATION_COOLING':r'cooling inflation|inflation (?:falls|eases|slows)',
 'GEOPOLITICAL_RISK':r'\bwar\b|geopolitical tensions|military strike',
 'GEOPOLITICAL_DEESCALATION':r'\bceasefire\b|peace deal|de.escalation',
 'DEBT_DEBASEMENT':r'\bdebasement\b|debt crisis|fiscal crisis',
 'FISCAL_CREDIBILITY':r'deficit reduction|fiscal consolidation',
 'DOLLAR_STRENGTH':r'strong(?:er)? dollar|dollar (?:rises|rallies|surges)',
 'DOLLAR_WEAKNESS':r'weak(?:er)? dollar|dollar (?:falls|slides|slumps)'}

def label(title):
    matches=[k for k,v in PATTERNS.items() if re.search(v,title,re.I)]
    return {'regime':matches[0] if len(matches)==1 else None,
            'confidence':1.0 if len(matches)==1 else 0.0,
            'reason':'Exact phrase rule; not LLM inference or a price-impact probability.'}

async def monitor():
    news=await fetch_news(72)
    articles=[{k:v for k,v in a.items() if k!='summary'} | {'label':label(a['title'])} for a in news['headlines']]
    result=densities(articles)
    # Signals inferred by the shared density function are intentionally excluded.
    return {'status':'ok' if articles else 'unavailable','method':'EXACT_PHRASE_RULES_NOT_LLM',
            **{k:v for k,v in result.items() if k in ('windows','prior_24h','series_72h')},
            'articles':articles,'source_status':news['source_status'],
            'warning':'RSS availability varies; collection is not comprehensive. Phrase labels ignore nuance and do not enter the weighted narrative factor.'}

async def run():
    gld,topics=await asyncio.gather(etf('GLD'),monitor(),return_exceptions=True)
    result={'topics':topics if isinstance(topics,dict) else {'status':'unavailable','reason':type(topics).__name__}}
    if isinstance(gld,dict) and gld.get('data'):
        d=gld['data']
        result['gld']={'status':gld['status'],'source':gld['source'],'fetched_at':gld['fetched_at'],
                       'observed_at':d['observed_at'],'change_20_sessions_tonnes':d['change_20_sessions_tonnes'],
                       'daily_changes':[{'date':r['date'],'change_tonnes':r['change_tonnes']} for r in d['rows']],
                       'warning':'GLD physical holdings change only. IAU and central-bank purchases remain separate missing inputs; no full flow factor is inferred.'}
    else: result['gld']={'status':'unavailable','reason':'GLD issuer history unavailable.'}
    return result
