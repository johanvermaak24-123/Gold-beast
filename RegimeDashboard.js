import React,{useState} from 'react';
import {ScrollView,View,Text,Pressable,Linking} from 'react-native';
import {colors,s} from '../theme';
export default function RegimeDashboard({data}){
 const [expanded,setExpanded]=useState(null);
 const report=data.intelligence;
 const pct=p=>p==null?'Unavailable':`${(p*100).toFixed(1)}%`;
 return <ScrollView contentContainerStyle={s.wrap}>
  {report&&<>
   <Text style={s.title}>GOLD INTELLIGENCE REPORT</Text>
   <View style={s.card}><Text style={s.title}>{report.final_decision} · Directional confidence {report.confidence}%</Text><Text style={s.text}>Regime: {report.current_regime.label}</Text><Text style={s.muted}>{report.current_regime.status}</Text><Text style={s.warning}>{report.reason}</Text></View>
   <Text style={s.title}>Independent horizons</Text>
   {Object.entries(report.horizons).map(([h,v])=><View key={h} style={s.card}>
    <Text style={s.text}>{h.toUpperCase()} · {v.decision} · Quality {v.forecast_quality}</Text>
    <Text style={s.muted}>Bull {pct(v.probabilities?.bull)} / Bear {pct(v.probabilities?.bear)} / Range {pct(v.probabilities?.range)}</Text>
    <Text style={s.warning}>{v.status} · Confidence {v.confidence}%</Text>
    {v.reasons.map((r,i)=><Text key={i} style={s.muted}>• {r}</Text>)}
    {v.driver_paths&&Object.entries(v.driver_paths).map(([k,p])=><Text key={k} style={s.muted}>{k}: up {pct(p.bull)} / flat {pct(p.range)} / down {pct(p.bear)}</Text>)}
    {v.asymmetry&&<Text style={s.muted}>Analog 10th / median / 90th return: {pct(v.asymmetry.q10_return)} / {pct(v.asymmetry.median_return)} / {pct(v.asymmetry.q90_return)} · not targets</Text>}
   </View>)}
   <Text style={s.title}>Destroy the forecast first</Text>
   <View style={s.card}><Text style={{...s.text,color:colors.up}}>Strongest bull case</Text><Text style={s.muted}>{report.review.strongest_bull_argument}</Text><Text style={{...s.text,color:colors.down}}>Strongest bear case</Text><Text style={s.muted}>{report.review.strongest_bear_argument}</Text><Text style={s.warning}>Conflict severity {(report.review.conflict_severity*100).toFixed(0)}%</Text><Text style={s.muted}>Measured driver conflict, not event probability.</Text></View>
   {report.engines.map(e=><View key={e.engine} style={s.card}><Text style={s.text}>{e.engine.replace(/_/g,' ').toUpperCase()} · {e.status}</Text><Text style={s.muted}>{e.reason}</Text><Text style={s.muted}>Gold-support state: {e.gold_support==null?'unavailable':e.gold_support.toFixed(2)} · {e.resolution}</Text></View>)}
   <Text style={s.title}>Counterevidence</Text>
   {report.review.counterevidence_articles.slice(0,8).map((a,i)=><Pressable key={i} style={s.card} onPress={()=>Linking.openURL(a.url).catch(()=>{})}><Text style={s.text}>{a.title}</Text><Text style={s.muted}>{a.source} · {a.published_at} · {a.label.regime}</Text></Pressable>)}
   <Text style={s.title}>What proves this wrong?</Text>
   {report.invalidation.map(v=><Text key={v} style={s.muted}>• {v}</Text>)}
   <Text style={s.muted}>{report.fund_consensus.status}</Text><Text style={s.warning}>{report.disclaimer}</Text>
   <Text style={s.title}>Supporting factor monitor</Text>
  </>}
  <View style={s.card}><Text style={s.title}>{data.regime_label}</Text><Text style={s.text}>BIAS: {data.bias} / Confidence: {data.confidence}%</Text><Text style={s.text}>Dominant driver: {data.dominant_driver?.replace(/_/g,' ')||'Unavailable'}</Text><Text style={s.muted}>{data.confidence_label}</Text><Text style={s.warning}>Coverage {data.coverage_percent}% · score {data.final_score.toFixed(2)}</Text><Text style={s.muted}>{new Date(data.generated_at).toLocaleString()}</Text></View>
  {data.factors.map(f=><Pressable accessibilityRole="button" style={s.card} key={f.name} onPress={()=>setExpanded(expanded===f.name?null:f.name)}>
   <View style={s.row}><Text style={s.text}>{f.name.replace(/_/g,' ').toUpperCase()} · {Math.round(f.weight*100)}%</Text><Text style={s.warning}>{f.signal==null?f.status:f.signal.toFixed(2)}</Text></View>
   <View style={{height:12,backgroundColor:'#273447',borderRadius:3,position:'relative'}}>
    <View style={{position:'absolute',left:'50%',width:1,height:12,backgroundColor:'#789'}}/>
    {f.signal!=null&&<View style={{position:'absolute',left:`${f.signal>=0?50:50+f.signal*50}%`,width:`${Math.abs(f.signal)*50}%`,height:12,backgroundColor:f.signal>=0?colors.up:colors.down}}/>}
   </View><Text style={s.muted}>{f.reason}</Text>
   {expanded===f.name&&f.lineage.map((l,i)=><View key={i}><Text style={s.warning}>{l.status} · fetched {l.fetched_at?new Date(l.fetched_at).toLocaleString():'never'}</Text><Pressable accessibilityRole="link" onPress={()=>{if(/^https?:/.test(l.source))Linking.openURL(l.source).catch(()=>{});}}><Text style={s.muted}>{l.source}</Text></Pressable><Text style={s.muted}>Observed: {l.data?.observed_at||'see underlying articles'} · Published: {l.data?.published_at||'not supplied'}</Text></View>)}
  </Pressable>)}
  <Text style={s.muted}>Tap a factor for source lineage. Missing and stale factors are excluded without redistributing their weights.</Text><Text style={s.warning}>{data.disclaimer}</Text>
 </ScrollView>;
}
