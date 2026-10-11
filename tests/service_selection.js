// Existing jobs must not silently select a sermon on launch or during polling.
const html=await Deno.readTextFile('ccs/index.html');
const script=html.split('<script>')[1].split('</script>')[0];
const elements=new Map();
const document={querySelector(s){if(!elements.has(s))elements.set(s,{value:'',dataset:{},innerHTML:'',querySelector(){return null}});return elements.get(s)}};
const job={id:'previous',plan:{date:'2026-10-04',title:'Previous sermon'},status:{stage:'Finished',active:false},finished:true};
let jobs=[job],shown=[],resets=0,selections=[];
const api=new Function('document','localStorage','fetch','setInterval','workflowReset','shown',script+`;show=r=>shown.push(r.id);return {refresh,select:id=>{selected=id;lastKey=''},get:()=>selected};`)(document,{getItem:()=>null},async(path,opts)=>{if(path==='/api/selection'){selections.push(JSON.parse(opts.body).id);return {ok:true,json:async()=>({})}}return {ok:true,json:async()=>jobs}},()=>{},()=>resets++,shown);
await api.refresh();
if(api.get()!==null||shown.length||document.querySelector('#history').value!=='')throw Error('Launch selected a previous sermon');
if(!document.querySelector('#history').innerHTML.includes('value=""'))throw Error('Missing empty selection option');
api.select(job.id);await api.refresh();
if(api.get()!==job.id||shown[0]!==job.id)throw Error('Explicit selection failed');
await api.refresh();if(api.get()!==job.id)throw Error('Polling lost explicit selection');
document.querySelector('#history').value='';document.querySelector('#history').onchange();await api.refresh();
if(api.get()!==null||document.querySelector('#jobs').innerHTML!==''||!resets)throw Error('Clearing selection left prior job displayed');
api.select(job.id);jobs=[];await api.refresh();
if(api.get()!==null)throw Error('Missing job left a stale selection');
console.log('Launch, polling, explicit selection, clearing selection and missing jobs passed.');

if(!selections.includes(null)||!selections.includes(job.id)||selections.at(-1)!==null)throw Error('Tray selection does not follow browser selection');
