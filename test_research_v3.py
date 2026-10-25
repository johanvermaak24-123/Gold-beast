import unittest
import numpy as np
from datetime import date,timedelta
from research_engine import dataset,evaluate
from supplemental import label

class ResearchTests(unittest.TestCase):
    def setUp(self):
        n=950;rng=np.random.default_rng(42)
        self.rows=[]
        for values in [2+np.cumsum(rng.normal(0,.02,n)),100*np.exp(np.cumsum(rng.normal(0,.003,n))),4+np.cumsum(rng.normal(0,.01,n)),1800*np.exp(np.cumsum(rng.normal(0,.01,n)))]:
            self.rows.append([{'date':str(date(2018,1,1)+timedelta(days=i)),'value':float(v)} for i,v in enumerate(values)])
    def test_lagged_macro_inputs(self):
        _,_,x,_=dataset(*self.rows)
        self.rows[0][-1]['value']+=100
        self.rows[0][-2]['value']+=100
        _,_,changed,_=dataset(*self.rows)
        np.testing.assert_equal(x[-1],changed[-1])
    def test_purged_nonoverlapping_results_and_distribution(self):
        d,v,x,i=dataset(*self.rows);r=evaluate(d,v,x,i,'5d')
        self.assertAlmostEqual(sum(r['probabilities'].values()),1)
        self.assertEqual(r['decision'],'NO TRADE')
        self.assertTrue(r['validation']['training_target_purge'])
        for a,b in zip(r['recent_tests'],r['recent_tests'][1:]):
            self.assertLessEqual(a['outcome_date'],b['date'])
    def test_future_change_cannot_change_earlier_test(self):
        d,v,x,i=dataset(*self.rows);before=evaluate(d,v,x,i,'24h')
        self.rows[3][-1]['value']*=2
        d,v,x,i=dataset(*self.rows);after=evaluate(d,v,x,i,'24h')
        self.assertEqual(before['recent_tests'][0],after['recent_tests'][0])
    def test_ambiguous_topic_is_unclassified(self):
        self.assertIsNone(label('Hawkish Fed faces war and ceasefire')['regime'])
        self.assertEqual(label('Fed remains hawkish')['regime'],'FED_HAWKISH')
        self.assertIsNone(label('Gold is pretty')['regime'])
