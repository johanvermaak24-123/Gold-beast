import React,{useState} from 'react';
import {SafeAreaView,View,Text,Pressable,TextInput,ActivityIndicator,StatusBar,StyleSheet,ScrollView} from 'react-native';
import RegimeDashboard from './screens/RegimeDashboard';
import PositioningFlows from './screens/PositioningFlows';
import NarrativeClusters from './screens/NarrativeClusters';
import DivergenceAlerts from './screens/DivergenceAlerts';
import useTerminal from './hooks/useTerminal';
import {colors,s} from './theme';
export default function App(){
 const terminal=useTerminal();
 const [tab,setTab]=useState(0),[settings,setSettings]=useState(false),[url,setUrl]=useState(''),[setupError,setSetupError]=useState('');
 const names=['Regime','Positioning','Narratives','Divergences'];
 const Screen=[RegimeDashboard,PositioningFlows,NarrativeClusters,DivergenceAlerts][tab];
 const showSetup=terminal.backend===''||settings;
 async function connect(){setSetupError('');try{await terminal.connect(url||terminal.backend);setSettings(false);}catch(e){setSetupError(e.message);}}
 return <SafeAreaView style={a.app}><StatusBar barStyle="light-content"/>
  <View style={a.header}><View><Text style={a.brand}>AU / INTELLIGENCE</Text><Text style={s.muted}>MACRO · POSITIONING · FLOWS</Text></View><Pressable accessibilityRole="button" onPress={()=>{setUrl(terminal.backend||'');setSettings(!settings);}}><Text style={s.warning}>Server</Text></Pressable></View>
  {terminal.backend===null?<ActivityIndicator color={colors.gold}/>:showSetup?<ScrollView contentContainerStyle={s.wrap} keyboardShouldPersistTaps="handled">
   <Text style={s.title}>Connect your terminal</Text><Text style={s.muted}>Enter the FastAPI server address. Your phone remembers it after you close the app.</Text>
   <TextInput accessibilityLabel="Backend URL" style={s.input} value={url} onChangeText={setUrl} autoCapitalize="none" autoCorrect={false} keyboardType="url" placeholder="https://your-server.example" placeholderTextColor={colors.muted}/>
   {!!setupError&&<Text accessibilityRole="alert" style={{color:colors.down}}>{setupError}</Text>}
   <Pressable disabled={terminal.saving} onPress={connect} style={s.button}>{terminal.saving?<ActivityIndicator color={colors.gold}/>:<Text style={s.text}>Test connection & save</Text>}</Pressable>
   <View style={s.card}><Text style={s.text}>First connection</Text><Text style={s.muted}>Run the backend using START_HERE.md. On the same Wi-Fi use your computer’s LAN IP with :8000. For use anywhere, enter your deployed HTTPS address.</Text></View>
   <Text style={s.warning}>No server is hosted automatically. Missing feeds or untrained models remain visible and cannot produce an executable trade.</Text>
   {!!terminal.backend&&<Pressable onPress={()=>setSettings(false)}><Text style={s.text}>Back to terminal</Text></Pressable>}
  </ScrollView>:<>
   <View style={a.status}><Text style={s.muted}>{terminal.loading?'Updating sources…':terminal.connected?'Connected · updates every 5 min':'Disconnected'}</Text><Pressable accessibilityRole="button" disabled={terminal.loading} onPress={terminal.reconnect}><Text style={s.warning}>Reconnect</Text></Pressable></View>
   {terminal.loading&&<ActivityIndicator color={colors.gold}/>}
   {!!terminal.error&&<View style={a.banner}><Text accessibilityRole="alert" style={{color:colors.down}}>{terminal.error}</Text></View>}
   {terminal.staleDisplay&&<Text style={[s.warning,a.banner]}>STALE DISPLAY — previous decision is not current. Reconnecting does not validate an old trade.</Text>}
   <View style={{flex:1}}>{terminal.data?<Screen data={terminal.data}/>:<View style={s.wrap}><Text style={s.title}>Building your first report</Text><Text style={s.muted}>Sources load on the server. The first report can take a minute; a sleeping host may need longer.</Text></View>}</View>
   <View style={a.nav}>{names.map((n,i)=><Pressable key={n} onPress={()=>setTab(i)} accessibilityRole="tab" accessibilityState={{selected:tab===i}} style={a.tab}><Text style={{color:tab===i?colors.gold:colors.muted,fontSize:11,fontWeight:'700'}}>{n}</Text></Pressable>)}</View>
  </>}
 </SafeAreaView>;
}
const a=StyleSheet.create({app:{flex:1,backgroundColor:colors.bg,paddingTop:25},header:{padding:18,flexDirection:'row',justifyContent:'space-between',alignItems:'center'},brand:{color:colors.gold,fontSize:18,fontWeight:'900'},status:{paddingHorizontal:18,paddingBottom:10,flexDirection:'row',justifyContent:'space-between'},banner:{padding:14,backgroundColor:'#291b25',gap:8},nav:{flexDirection:'row',borderTopWidth:1,borderColor:'#28364a',paddingBottom:10},tab:{flex:1,paddingVertical:18,alignItems:'center'}});
