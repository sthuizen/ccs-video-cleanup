const script=(await Deno.readTextFile('ccs/index.html')).split('<script>')[1].split('</script>')[0];
const elements=new Map();
const document={querySelector(s){if(!elements.has(s))elements.set(s,{value:'',dataset:{},innerHTML:''});return elements.get(s)}};
let clock=1000000;
class TestDate extends Date{static now(){return clock}}
const localStorage={getItem:()=>null,setItem:()=>{}};
const row={id:'test',plan:null,finished:false,processed:false,status:{stage:'Rendering',detail:'Encoding',active:true,percent:50,elapsed_seconds:120,eta_seconds:120,total_elapsed_seconds:300,steps:[{stage:'Downloading',completed:true,elapsed_seconds:180}]}};
const fetch=async()=>({ok:true,json:async()=>[row]});
const api=new Function('document','localStorage','fetch','setInterval','Date',script+'\nreturn {refresh,paintProgress};')(document,localStorage,fetch,()=>{},TestDate);
await api.refresh();
let html=document.querySelector('#progress').innerHTML;
if(!html.includes('50%')||!html.includes('About 2m 0s remaining')||!html.includes('Downloading · 100%'))throw Error('Measured progress, ETA or completed steps missing');
clock+=10000;api.paintProgress();html=document.querySelector('#progress').innerHTML;
if(!html.includes('2m 10s elapsed')||!html.includes('About 1m 50s remaining'))throw Error('Live timers did not advance');
row.status={stage:'Needs information',active:false,elapsed_seconds:0,percent:null,eta_seconds:null,total_elapsed_seconds:300};
await api.refresh();clock+=60000;api.paintProgress();
html=document.querySelector('#progress').innerHTML;
if(!html.includes('Waiting for your details')||!html.includes('0s elapsed'))throw Error('Waiting timer keeps running');
console.log('Progress display shows percentages, ETA, completed steps and live timers; waiting timers stop.');
