import React,{useState} from 'react';
import {ScrollView,View,Text,Pressable,Linking,useWindowDimensions} from 'react-native';
import Svg,{Path,Line,Text as SvgText} from 'react-native-svg';
import {colors,s} from '../theme';
const palette=['#ff7e89','#55dbaa','#e49e55','#5ba5eb','#cf77d9','#83c8bb','#e6c476','#aa9cef','#bc6e72','#70a798'];
export default function NarrativeClusters({data}){
 const n=data.factors.find(f=>f.name==='narrative'),d=n.details;
 const series=d.series_72h||[], regimes=Object.keys(d.windows?.['24']?.density||{});
 const [selected,setSelected]=useState(null),width=useWindowDimensions().width-36;
 const W=width-36,H=180,offset=28;
 let base=series.map(()=>0);
 const paths=regimes.map((r,k)=>{
  const top=series.map((p,i)=>base[i]+(p.density[r]||0));
  const x=i=>offset+i*(W-offset)/Math.max(1,series.length);
  const points=top.flatMap((v,i)=>[`${x(i)},${H-v*H}`,`${x(i+1)},${H-v*H}`]).concat(base.flatMap((_,i)=>{const j=base.length-1-i;return [`${x(j+1)},${H-base[j]*H}`,`${x(j)},${H-base[j]*H}`];}));
  base=top;
  return <Path key={r} d={`M${points.join(' L')} Z`} fill={palette[k]} opacity={selected&&selected!==r? .28:.8} onPress={()=>setSelected(r)}/>;
 });
 const articles=(d.articles||[]).filter(a=>a.label?.regime===selected);
 return <ScrollView contentContainerStyle={s.wrap}><Text style={s.title}>NARRATIVE CLUSTERS</Text><Text style={s.warning}>{n.status} · {d.baseline_ready?'Baseline ready':'Accumulating baseline / insufficient coverage'}</Text>
  <Text style={s.muted}>Last 72h · three-hour bins · share of all deduplicated relevant articles. Blank space = unclassified, no coverage or missing topics.</Text>
  {!!series.length&&<Svg width={width} height={H+30}>{paths}<Line x1={offset} y1={H} x2={W} y2={H} stroke="#64758b"/><SvgText x={0} y={12} fill={colors.muted} fontSize={10}>100%</SvgText><SvgText x={offset} y={H+20} fill={colors.muted} fontSize={10}>−72h</SvgText><SvgText x={W-28} y={H+20} fill={colors.muted} fontSize={10}>now</SvgText></Svg>}
  {regimes.map((r,k)=><Pressable key={r} accessibilityRole="button" onPress={()=>setSelected(r)} style={s.card}><Text style={{color:palette[k],fontSize:13}}>{r} · {((d.windows?.['24']?.density[r]||0)*100).toFixed(1)}%</Text></Pressable>)}
  <Text style={s.muted}>{d.warning||n.reason}</Text>{(d.source_status||[]).map((v,i)=><Text key={i} style={s.muted}>{v.source}: {v.status}</Text>)}
  <Text style={s.title}>{selected||'Tap a cluster to inspect sources'}</Text>
  {articles.map((a,i)=><Pressable key={`${a.url}-${i}`} style={s.card} onPress={()=>Linking.openURL(a.url).catch(()=>{})}><Text style={s.text}>{a.title}</Text><Text style={s.muted}>{a.source} · {a.published_at}</Text><Text style={s.muted}>{a.label.reason}</Text><Text style={s.muted}>Model {a.model} · label certainty {(a.label.confidence*100).toFixed(0)}% · first seen {a.first_seen}</Text></Pressable>)}
  {selected&&!articles.length&&<Text style={s.muted}>No classified articles for this cluster.</Text>}
 </ScrollView>;
}
