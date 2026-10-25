from datetime import datetime,timedelta,timezone
import os,tempfile,unittest
from unittest.mock import patch
from aggregator import aggregate
from real_yield_engine import evaluate as yields
from positioning_engine import evaluate as positions
from dollar_engine import evaluate as dollar
from narrative_cluster_engine import densities,Label
from flow_engine import parse_holdings
from core import source

def snapshot(rows,status='ok'):
 return {'status':status,'source':'https://example.org/data','fetched_at':'2026-10-25T12:00:00+00:00','data':{'rows':rows,'observed_at':rows[-1]['date']}}
def f(name,weight,signal,status='ok',**details):
 return dict(name=name,weight=weight,signal=signal,status=status,reason='fixture',lineage=[],details=details)
def factors(signals):
 return [f(n,w,v) for (n,w),v in zip([('real_yield',.35),('positioning',.25),('flows',.2),('dollar',.1),('narrative',.1)],signals)]
class Engines(unittest.TestCase):
 def test_yields(self):
  rows=[{'date':f'2026-09-{i+1:02}','value':1+i*.04} for i in range(25)]
  self.assertEqual(yields(snapshot(rows),snapshot(rows),{'data':None})['signal'],-1)
  self.assertEqual(yields({'data':None,'status':'unavailable'},snapshot(rows),{'data':None})['signal'],-1)
 def test_cot_percentiles(self):
  rows=[dict(date=str(i),net=i,long=i+100,short=100,open_interest=1000) for i in range(157)]
  result=positions(snapshot(rows));self.assertEqual(result['details']['percentile'],100);self.assertEqual(result['signal'],-1)
  rows[-1]['net']=-1
  self.assertEqual(positions(snapshot(rows))['signal'],1)
 def test_cot_stale(self):
  rows=[dict(date=str(i),net=i,long=i+100,short=100,open_interest=1000) for i in range(157)]
  self.assertIsNone(positions(snapshot(rows,'stale'))['signal'])
 def test_cot_insufficient(self):
  self.assertIsNone(positions(snapshot([{'date':'2026-10-20','net':1}]))['signal'])
 def test_dollar_divergence(self):
  rows=[{'date':str(i),'value':100} for i in range(25)]+[{'date':'26','value':101}]
  real=f('real_yield',.35,-1,five_session_change_bp=10)
  self.assertEqual(dollar(snapshot(rows),{'data':None},real)['signal'],0)
  real['details']['five_session_change_bp']=-10
  self.assertEqual(dollar(snapshot(rows),{'data':None},real)['signal'],-1)
 def test_agreement(self):
  self.assertEqual(aggregate(factors([1,1,1,1,1]))['confidence'],85)
  self.assertEqual(aggregate(factors([.2,.2,.2,-.2,-.2]))['confidence'],20)
 def test_divergence(self):
  result=aggregate(factors([-.9,1,1,1,1]))
  self.assertEqual(result['regime_label'],'Divergent / Stand Aside');self.assertEqual(result['bias'],'Divergent')
  self.assertTrue(any(a['type']=='REGIME_DIVERGENCE' for a in result['divergences']))
 def test_missing_weights(self):
  fs=factors([1,1,None,None,None])
  for x in fs[2:]:x['status']='unavailable'
  self.assertAlmostEqual(aggregate(fs)['final_score'],.6);self.assertEqual(aggregate(fs)['coverage_percent'],60)
 def test_holdings(self):
  text='date,tonnes\n'+'\n'.join(f'2025-01-{i+1:02},{100+i}' for i in range(30))
  self.assertEqual(parse_holdings(text,'GLD')['change_20_sessions_tonnes'],20)
  with self.assertRaises(ValueError):parse_holdings('date,close\n2025-01-01,100','GLD')
 def test_density(self):
  stamp=datetime.now(timezone.utc);rows=[]
  for hours,regime in [(6,'FED_HAWKISH'),(30,'FED_DOVISH')]:rows += [{'published_at':(stamp-timedelta(hours=hours)).isoformat(),'label':{'regime':regime,'confidence':.9}} for _ in range(20)]
  result=densities(rows,stamp)
  self.assertEqual(result['signal'],-1);self.assertEqual(len(result['series_72h']),24)
  self.assertEqual(result['windows']['24']['density']['FED_HAWKISH'],1)
  self.assertIsNone(densities(rows[:2],stamp)['signal'])
 def test_llm_validation(self):
  with self.assertRaises(ValueError):Label(regime='BUY',confidence=1,reason='bad')
  with self.assertRaises(ValueError):Label(regime='FED_HAWKISH',confidence=2,reason='bad')
class Persistence(unittest.IsolatedAsyncioTestCase):
 async def test_stale_fallback(self):
  with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'DATA_DIR':directory}):
   async def good():return {'value':1}
   async def bad():raise RuntimeError('provider failure')
   a=await source('test','https://example.org',good,0);b=await source('test','https://example.org',bad,0)
   self.assertEqual(a['status'],'ok');self.assertEqual(b['status'],'stale');self.assertEqual(b['data'],{'value':1})

class API(unittest.TestCase):
 def test_four_endpoints(self):
  from fastapi.testclient import TestClient
  import main
  result=aggregate(factors([.8,0,None,0,None]))
  async def fake():return result
  with patch.object(main,'refresh',fake):
   client=TestClient(main.app)
   for endpoint in ('regime','positioning','narratives','divergences'):
    response=client.get('/'+endpoint)
    self.assertEqual(response.status_code,200)
   self.assertIn('positioning',client.get('/positioning').json())
   self.assertEqual(client.get('/narratives').json()['name'],'narrative')
   self.assertIn('alerts',client.get('/divergences').json())

class Valuation(unittest.TestCase):
 def test_regression_excludes_latest_price(self):
  import math
  base=datetime(2025,1,1)
  yr=[{'date':(base+timedelta(days=i)).date().isoformat(),'value':1+i*.002} for i in range(300)]
  gr=[{'date':r['date'],'value':math.exp(8-.2*r['value']+.001*math.sin(i))} for i,r in enumerate(yr)]
  a=yields(snapshot(yr),snapshot(yr),snapshot(gr))['details']['valuation']
  gr[-1]['value']*=1.1
  b=yields(snapshot(yr),snapshot(yr),snapshot(gr))['details']['valuation']
  self.assertEqual(a['reference_price'],b['reference_price'])
  self.assertGreater(b['deviation_percent'],a['deviation_percent'])
