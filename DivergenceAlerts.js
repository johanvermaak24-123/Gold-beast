import React from 'react';
import {ScrollView,View,Text} from 'react-native';
import {s} from '../theme';
export default function DivergenceAlerts({data}){
 return <ScrollView contentContainerStyle={s.wrap}><Text style={s.title}>DIVERGENCE ALERTS</Text><Text style={s.muted}>Timestamped research conditions; no execution instructions or proven alpha.</Text>
  {data.divergences.map((a,i)=><View key={i} style={s.card}><Text style={s.warning}>{a.type.replace(/_/g,' ')}</Text><Text style={s.text}>{a.message}</Text><Text style={s.muted}>{a.detected_at}</Text><Text style={s.muted}>Evidence: {a.factors.join(' + ')}</Text>{Object.entries(a.lineage).map(([key,items])=><Text key={key} style={s.muted}>{key}: {items.map(v=>`${v.source} [${v.fetched_at||'unavailable'}]`).join('\n')}</Text>)}</View>)}
  {!data.divergences.length&&<Text style={s.warning}>{data.coverage_percent<100?'No divergence detected among available factors. Missing evidence may hide conflicts.':'No configured divergence condition is active.'}</Text>}
  <Text style={s.muted}>A rising-real-yield / central-bank buying divergence does not establish a price floor. Crowding can persist while price trends continue.</Text>
 </ScrollView>;
}
