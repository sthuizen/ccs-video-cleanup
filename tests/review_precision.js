// Exercise the actual shipped form handler against a small DOM/network harness.
const html=await Deno.readTextFile('ccs/index.html');
const script=html.split('<script>')[1].split('</script>')[0];
const elements=new Map();
const document={querySelector(selector){if(!elements.has(selector))elements.set(selector,{value:'',dataset:{},innerHTML:'',textContent:''});return elements.get(selector)}};
let submitted;
const fetch=async (url,opts)=>({ok:true,json:async()=>{if(opts){if(url==='/api/audio-tests')submitted=JSON.parse(opts.body);return {id:'fixture'}}return []}});
const show=new Function('document','fetch','setInterval',script+'\nreturn show;')(document,fetch,()=>{});
const plan={start:2300.85,end:4574.12,date:'2026-10-04',passage:'Romans 2:1–16',title:'When will we see justice?',issues:[],confirmed:true,evidence:{},candidates:{}};
show({id:'fixture',plan,status:{stage:'Finished',detail:''},finished:false,processed:false});
for(const [key,value] of Object.entries({start:'00:38:21',end:'01:16:14',date:plan.date,passage:plan.passage,title:plan.title}))document.querySelector('#'+key).value=value;
await document.querySelector('#render').onclick();
if(submitted.start!==2300.85||submitted.end!==4574.12)throw Error('Title-only submission changed the cut points');
document.querySelector('#start').value='00:38:25';
await document.querySelector('#render').onclick();
if(submitted.start!=='00:38:25')throw Error('An explicit cut-point edit was lost');
console.log('Production review handler preserves original cut precision and accepts explicit edits.');
