"""Holdings-based ETF changes and publication-aware WGC quarterly CSV imports."""
import asyncio
import csv
import io
import os
from pathlib import Path
import httpx
from core import source,factor,expired,now
GLD_URL='https://api.spdrgoldshares.com/api/v1/historical-archive?exchange=NYSE&lang=en&product=gld'


def parse_holdings(text,fund):
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    rows=[]
    for raw in reader:
        row={k.strip().lower():v for k,v in raw.items() if k}
        if 'date' in row and 'tonnes' in row:
            date,tonnes=row['date'],row['tonnes']
        else:
            # Issuer GLD historical archive uses a descriptive tonnes column.
            date=row.get('date', '')
            key=next((k for k in row if 'tonnes' in k and 'trust' in k),None)
            tonnes=row.get(key,'') if key else ''
        try:
            from dateutil.parser import parse
            day=parse(date).date().isoformat()
            value=float(tonnes.replace(',','').strip())
            if value<0 or day>str(now().date()):continue
            rows.append({'date':day,'tonnes':value})
        except (ValueError,TypeError,AttributeError):continue
    rows=sorted({r['date']:r for r in rows}.values(),key=lambda r:r['date'])
    if len(rows)<22:raise ValueError('Need at least 22 holdings observations')
    changes=[{**r,'change_tonnes':r['tonnes']-p['tonnes']} for p,r in zip(rows,rows[1:])]
    return {'fund':fund,'rows':changes[-31:],'observed_at':rows[-1]['date'],
            'change_20_sessions_tonnes':rows[-1]['tonnes']-rows[-21]['tonnes'],
            'note':'Change in physical holdings proxy, not exact dollar subscriptions; fees can affect holdings.'}

async def etf(fund):
    path=Path(os.getenv('DATA_DIR','data'))/(fund.lower()+'_holdings.csv')
    configured=os.getenv(fund+'_HOLDINGS_URL')
    url=configured or (GLD_URL if fund=='GLD' else 'https://www.ishares.com/us/products/239561/ishares-gold-trust-fund')
    async def load():
        if path.exists():text=path.read_text()
        elif fund=='GLD' or configured:
            async with httpx.AsyncClient(timeout=20,follow_redirects=True) as c:
                r=await c.get(url);r.raise_for_status()
                content=r.content
                if content.startswith(b'\x1f\x8b'):content=__import__('gzip').decompress(content)
                if content.startswith(b'PK'):
                    import openpyxl
                    book=openpyxl.load_workbook(io.BytesIO(content),read_only=True,data_only=True)
                    sheet=book['US GLD Historical Archive']
                    output=io.StringIO();writer=csv.writer(output)
                    found=False
                    for row in sheet.iter_rows(values_only=True):
                        if not found:
                            names=[str(v).strip().lower() if v is not None else '' for v in row]
                            if 'date' not in names or not any('tonnes' in n for n in names):continue
                            date_index=names.index('date');tonnes_index=next(i for i,n in enumerate(names) if 'tonnes' in n)
                            writer.writerow(['date','tonnes']);found=True;continue
                        day=row[date_index]
                        if hasattr(day,'date'):day=day.date().isoformat()
                        writer.writerow([day,row[tonnes_index]])
                    book.close();text=output.getvalue()
                elif content.startswith(b'%PDF'):
                    raise ValueError('Issuer returned PDF, not holdings data')
                else:text=content.decode('utf-8-sig',errors='replace')
        else:raise ValueError('IAU issuer CSV not configured')
        return parse_holdings(text,fund)
    result=await source('holdings:'+fund,str(path) if path.exists() else url,load,3600)
    if result['data'] and expired(result['data']['observed_at'],5):result['status']='stale'
    return result

async def central_bank():
    path=Path(os.getenv('DATA_DIR','data'))/'wgc_quarterly.csv'
    async def load():
        rows=[]
        for row in csv.DictReader(io.StringIO(path.read_text())):
            # Source URL and publication time are mandatory, never synthesized.
            from datetime import datetime
            published=datetime.fromisoformat(row['published_at'].replace('Z','+00:00'))
            if not published.tzinfo:raise ValueError('Publication timestamp must have timezone')
            if published>now() or row['period_end']>str(now().date()):continue
            value=float(row['net_tonnes'])
            if not __import__('math').isfinite(value):raise ValueError('Invalid tonnes')
            rows.append({'period_end':row['period_end'],'net_tonnes':value,
                         'published_at':published.isoformat(),'source_url':row['source_url']})
        rows.sort(key=lambda r:r['period_end'])
        if len(rows)<2:raise ValueError('Need two published quarters')
        return {'rows':rows[-8:],'observed_at':rows[-1]['period_end'],'published_at':rows[-1]['published_at']}
    result=await source('wgc:quarterly','https://www.gold.org/goldhub/data/gold-reserves-by-country',load,3600)
    if result['data'] and expired(result['data']['observed_at'],150):result['status']='stale'
    return result

async def run():
    gld,iau,cb=await asyncio.gather(etf('GLD'),etf('IAU'),central_bank())
    fresh=lambda x:x['status']=='ok' and x['data'] is not None
    etfs=[x['data'] for x in (gld,iau) if fresh(x)]
    # Require both ETFs and quarterly data for the full 20% factor.
    signal=None
    cb_buy=None
    divergence=False
    if fresh(cb):cb_buy=all(r['net_tonnes']>0 for r in cb['data']['rows'][-2:])
    etf_total=sum(x['change_20_sessions_tonnes'] for x in etfs) if len(etfs)==2 else None
    if cb_buy is not None and etf_total is not None:
        cb_signal=1 if cb_buy else -1 if all(r['net_tonnes']<0 for r in cb['data']['rows'][-2:]) else 0
        etf_signal=max(-1,min(1,etf_total/20))
        signal=.5*cb_signal+.5*etf_signal
        divergence=cb_buy and etf_total<0
    result=factor('flows',.20,signal,
        'Two-quarter central-bank direction plus 20-observation GLD/IAU holdings change. Buying against ETF outflows is a candidate structural divergence, not a guaranteed price floor.',
        [gld,iau,cb],etfs=etfs,central_bank=cb['data'],central_bank_buying=cb_buy,
        etf_change_tonnes=etf_total,structural_divergence=divergence)
    return result
