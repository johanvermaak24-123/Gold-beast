import React from 'react';
import {ScrollView,View,Text,useWindowDimensions} from 'react-native';
import {LineChart} from 'react-native-chart-kit';
import {colors,s,chart} from '../theme';
export default function PositioningFlows({data}){
 const width=useWindowDimensions().width-68;
 const po=data.factors.find(f=>f.name==='positioning'),fl=data.factors.find(f=>f.name==='flows');
 const p=po.details,flow=fl.details;
 const history=p.history||[];
 function plot(rows,key,suffix=''){
  if(rows.length<2)return <Text style={s.muted}>Not enough observations for chart.</Text>;
  return <LineChart width={width} height={190} withDots={false} chartConfig={chart} yAxisSuffix={suffix} data={{labels:rows.map((r,i)=>i===0||i===rows.length-1?r.date.slice(5):''),datasets:[{data:rows.map(r=>r[key])}]}}/>;
 }
 return <ScrollView contentContainerStyle={s.wrap}>
  <Text style={s.title}>POSITIONING & FLOWS</Text>
  <View style={s.card}><Text style={s.text}>Managed money · COMEX Gold</Text><Text style={s.warning}>{po.status} · Net {p.net_contracts?.toLocaleString()??'unavailable'} contracts</Text><Text style={s.text}>156-week percentile: {p.percentile==null?'—':`${p.percentile.toFixed(1)}%`}</Text>
   <View style={{height:14,backgroundColor:'#253449',position:'relative'}}><View style={{position:'absolute',left:0,width:'15%',height:14,backgroundColor:'#225b49'}}/><View style={{position:'absolute',left:'85%',width:'15%',height:14,backgroundColor:'#723c47'}}/>{p.percentile!=null&&<View style={{position:'absolute',left:`${Math.min(p.percentile,99)}%`,height:18,width:3,backgroundColor:colors.gold}}/>}</View>
   <Text style={s.muted}>Washed out &lt;15% · Crowded long &gt;85%</Text>{plot(history,'net')}
   <Text style={s.muted}>Positions as of {p.observed_at||'—'}. Weekly data is delayed; not live exposure.</Text><Text style={s.muted}>{p.publication_note}</Text>
  </View>
  {(flow.etfs||[]).map(e=><View key={e.fund} style={s.card}><Text style={s.text}>{e.fund} · daily holdings change (tonnes)</Text>{plot(e.rows,'change_tonnes','t')}<Text style={s.muted}>20-observation change: {e.change_20_sessions_tonnes.toFixed(2)} tonnes · {e.observed_at}</Text><Text style={s.muted}>{e.note}</Text></View>)}
  {!(flow.etfs||[]).length&&<Text style={s.warning}>ETF holdings unavailable. Price/volume is not substituted for flows.</Text>}
  <View style={s.card}><Text style={s.text}>Central-bank purchase pace</Text>{flow.central_bank?.rows?.map(q=><Text key={q.period_end} style={s.muted}>{q.period_end}: {q.net_tonnes.toFixed(1)}t · published {q.published_at}</Text>)||<Text style={s.warning}>Import verified WGC quarterly CSV on the backend.</Text>}<Text style={s.muted}>{fl.reason}</Text></View>
 </ScrollView>;
}
