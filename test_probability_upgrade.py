import tempfile
import unittest
import os
from unittest.mock import patch
from datetime import datetime,timedelta,timezone
import numpy as np
from probability_model import FEATURES,TARGETS,CLASSES,fit_analog,raw_predict,tempered,validate_rows,train,predict
from decision_engine import confidence,evidence,forecast,regime,execution_state

class Probability(unittest.TestCase):
 def test_normalized_calibration(self):
  p=tempered([[.1,.2,.7]],2)
  self.assertAlmostEqual(float(p.sum()),1)
  self.assertTrue(np.all(p>0))
 def test_confidence_caps(self):
  p={'bull':.999,'bear':.0005,'range':.0005}
  aligned={k:{'bull':.01,'bear':.98,'range':.01} for k in ('usd','real_yield','fed')}
  self.assertEqual(confidence(p,aligned,0,1),95)
  aligned['usd']={'bull':.98,'bear':.01,'range':.01}
  self.assertEqual(confidence(p,aligned,0,1),85)
  self.assertLessEqual(confidence(p,aligned,.5,1),50)
 def test_missing_probabilities_not_zero(self):
  engines=[dict(engine=k,status='unavailable',gold_support=None,resolution='daily',reason='missing',lineage=[]) for k in FEATURES]
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'MODEL_DIR':d}):
   r=forecast(engines,{'conflict_severity':0},{'label':'Crisis'},{'ready':False},'1h')
  self.assertIsNone(r['probabilities']);self.assertEqual(r['decision'],'NO TRADE')
 def test_conflicts(self):
  make=lambda k,v:dict(engine=k,status='ok',gold_support=v,lineage=[],reason=k)
  a=evidence([make('real_yield',1),make('usd',-1)],{'details':{}})
  self.assertGreater(a['conflict_severity'],.8)
  self.assertTrue(a['bull_case']);self.assertTrue(a['bear_case'])
 def test_missing_quote(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'DATA_DIR':d}):self.assertFalse(execution_state()['ready'])
 def test_reject_lookahead(self):
  t=datetime(2020,1,1,tzinfo=timezone.utc)
  row={'timestamp':t.isoformat(),'features_known_at':(t+timedelta(hours=1)).isoformat(),
       'outcomes_known_at':(t+timedelta(days=1)).isoformat(),'horizon':'24h','source_manifest':'test','regime':'Reflation',
       'gold_return':'.01',**{k:'0' for k in FEATURES},**{k+'_label':'range' for k in TARGETS}}
  with self.assertRaises(ValueError):validate_rows([row],'24h')
 def test_end_to_end_synthetic_not_market_validation(self):
  rng=np.random.default_rng(32);rows=[];base=datetime(2010,1,1,tzinfo=timezone.utc)
  for i in range(1200):
   x=rng.uniform(-1,1,10);t=base+timedelta(days=i*2)
   row={'timestamp':t.isoformat(),'features_known_at':t.isoformat(),'outcomes_known_at':(t+timedelta(days=1)).isoformat(),
        'horizon':'24h','source_manifest':'SYNTHETIC TEST ONLY','regime':'Reflation','gold_return':float(x[0]*.01)}
   row.update(dict(zip(FEATURES,x.tolist())))
   for j,k in enumerate(TARGETS):row[k+'_label']='bull' if x[j%5]>.33 else 'bear' if x[j%5]<-.33 else 'range'
   rows.append(row)
  artifact=train(rows,'24h');result=predict(artifact,{k:0 for k in FEATURES})
  self.assertEqual(len(result['driver_paths']),5)
  self.assertAlmostEqual(sum(result['probabilities'].values()),1)
  self.assertTrue(all(v>0 for v in result['probabilities'].values()))
  self.assertIn('eligible',artifact['validation'])
  self.assertEqual(artifact['validation']['segments'],[360,120,240,240,240])

class ReportIntegration(unittest.TestCase):
 def test_report_abstains_and_api_exposes_it(self):
  from decision_engine import build_report
  from fastapi.testclient import TestClient
  import main
  engines=[dict(engine=k,status='unavailable',gold_support=None,resolution='daily',reason='missing',lineage=[]) for k in FEATURES]
  base={'factors':[{'name':'narrative','details':{}}]}
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'DATA_DIR':d,'MODEL_DIR':d}):
   report=build_report(engines,base)
   self.assertEqual(report['final_decision'],'NO TRADE')
   self.assertEqual(set(report['horizons']),{'1h','4h','24h','5d','20d','60d'})
   self.assertTrue(all(h['probabilities'] is None for h in report['horizons'].values()))
   self.assertIsNone(report['fund_consensus']['buy_gold'])
   async def fake():return {'intelligence':report}
   with patch.object(main,'refresh',fake):
    response=TestClient(main.app).get('/intelligence')
    self.assertEqual(response.status_code,200)
    self.assertEqual(response.json()['final_decision'],'NO TRADE')
 def test_quote_freshness_and_closed_gate(self):
  import json
  from pathlib import Path
  from decision_engine import execution_state
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'DATA_DIR':d}):
   quote={'symbol':'XAUUSD','timestamp':datetime.now(timezone.utc).isoformat(),'source_url':'https://example.org/authorized','bid':4000,'ask':4000.2,'market_open':True}
   path=Path(d)/'market_quote.json';path.write_text(json.dumps(quote))
   self.assertTrue(execution_state()['ready'])
   quote['market_open']=False;path.write_text(json.dumps(quote));self.assertFalse(execution_state()['ready'])
   quote['market_open']=True;quote['timestamp']=(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat();path.write_text(json.dumps(quote))
   self.assertFalse(execution_state()['ready'])

class ReleaseReadiness(unittest.TestCase):
 def test_capabilities_contains_no_execution(self):
  from fastapi.testclient import TestClient
  import main
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'DATA_DIR':d,'MODEL_DIR':d}):
   r=TestClient(main.app).get('/capabilities')
   self.assertEqual(r.status_code,200)
   self.assertFalse(r.json()['trade_execution'])
   self.assertEqual(TestClient(main.app).get('/health').json()['service'],'gold-intelligence')
   self.assertEqual(r.json()['version'],'2.1.0')
   self.assertEqual(len(r.json()['models_present']),6)
