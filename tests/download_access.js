const html=await Deno.readTextFile('ccs/index.html');
const script=html.split('<script>')[1].split('</script>')[0];
const saved=new Map();
function session(){
  const elements=new Map();
  const document={querySelector(s){if(!elements.has(s))elements.set(s,{value:s==='#cookies'?'firefox':'',dataset:{}});return elements.get(s)}};
  const localStorage={getItem:k=>saved.has(k)?saved.get(k):null,setItem:(k,v)=>saved.set(k,v)};
  const fetch=async()=>({ok:true,json:async()=>[]});
  new Function('document','localStorage','fetch','setInterval',script)(document,localStorage,fetch,()=>{});
  return document.querySelector('#cookies');
}
let field=session();
if(field.value!=='firefox')throw Error('Firefox default missing');
field.value='';field.onchange();
field=session();if(field.value!=='')throw Error('Anonymous choice lost on reload');
field.value='firefox';field.onchange();
if(session().value!=='firefox')throw Error('Browser choice lost on reload');
console.log('Download access defaults to Firefox and preserves browser or anonymous choices across reloads.');
