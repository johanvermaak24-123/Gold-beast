export function normalizeBackend(value){
 const text=String(value||'').trim();
 let url;
 try{url=new URL(text);}catch{throw new Error('Enter an http:// or https:// server address.');}
 if(!['http:','https:'].includes(url.protocol)||!url.hostname||url.username||url.password||url.search||url.hash||/\s/.test(text))throw new Error('Use a server address without credentials, a query or a fragment.');
 return url.toString().replace(/\/+$/,'');
}
