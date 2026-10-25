import {useEffect,useRef,useState,useCallback} from 'react';
import {AppState} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
const KEY='gold-terminal.backend.v1';
import {normalizeBackend} from '../connection.mjs';
export default function useTerminal(){
 const [backend,setBackend]=useState(null),[data,setData]=useState(null),[error,setError]=useState('');
 const [loading,setLoading]=useState(false),[connected,setConnected]=useState(false),[retry,setRetry]=useState(0);
 const [saving,setSaving]=useState(false),[clock,setClock]=useState(Date.now());
 useEffect(()=>{const timer=setInterval(()=>setClock(Date.now()),30000);return ()=>clearInterval(timer);},[]);
 const request=useRef(null);
 useEffect(()=>{let alive=true;
  AsyncStorage.getItem(KEY).then(value=>{if(alive)setBackend(value||process.env.EXPO_PUBLIC_BACKEND_URL||'');})
   .catch(()=>{if(alive){setBackend(process.env.EXPO_PUBLIC_BACKEND_URL||'');setError('Could not load saved server address.');}});
  return ()=>{alive=false;};
 },[]);
 const connect=useCallback(async value=>{
  const url=normalizeBackend(value);setSaving(true);
  try{
   const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),15000);
   try{const r=await fetch(url+'/health',{signal:controller.signal});const health=await r.json();
    if(!r.ok||health.status!=='ok'||health.service!=='gold-intelligence')throw new Error('This address is not a healthy Gold Terminal backend.');
   }finally{clearTimeout(timer);}
   await AsyncStorage.setItem(KEY,url);
   request.current?.abort();setData(null);setError('');setBackend(url);setRetry(n=>n+1);
  }catch(e){throw new Error(e.name==='AbortError'?'Server connection timed out. Wake the host and try again.':e.message);}
  finally{setSaving(false);}
 },[]);
 useEffect(()=>{
  if(!backend)return;
  let alive=true,busy=false;
  async function load(){
   if(busy||(AppState.currentState&&AppState.currentState!=='active'))return;
   busy=true;setLoading(true);
   const controller=new AbortController();request.current=controller;
   const timer=setTimeout(()=>controller.abort(),180000);
   try{
    const r=await fetch(backend+'/regime',{signal:controller.signal});
    if(!r.ok)throw new Error(`Server returned ${r.status}`);
    const result=await r.json();
    if(!Array.isArray(result.factors)||!Array.isArray(result.divergences)||!result.generated_at)throw new Error('Unexpected terminal response. Check server version.');
    if(alive){setData(result);setConnected(true);setError('');}
   }catch(e){if(alive){setConnected(false);setError(e.name==='AbortError'?'Update timed out. The host may be waking up.':'Update failed: '+e.message);}}
   finally{clearTimeout(timer);busy=false;if(alive)setLoading(false);}
  }
  load();const timer=setInterval(load,300000);
  const subscription=AppState.addEventListener('change',status=>{if(status==='active')load();});
  return ()=>{alive=false;clearInterval(timer);subscription.remove();request.current?.abort();};
 },[backend,retry]);
 const staleDisplay=!!data&&(!connected||clock-Date.parse(data.generated_at)>360000);
 return {backend,data,error,loading,connected,saving,connect,staleDisplay,reconnect:()=>setRetry(n=>n+1)};
}
