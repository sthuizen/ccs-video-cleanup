const script=(await Deno.readTextFile('ccs/index.html')).split('<script>')[1].split('</script>')[0];
const elements=new Map();
const document={querySelector(s){if(!elements.has(s))elements.set(s,{value:'',checked:s==='#export-youtube',dataset:{},innerHTML:'',querySelector(){return null}});return elements.get(s)}};
const api=new Function('document','localStorage','fetch','setInterval',script+';return {outputChoices,outputCreateLabel,outputChoiceChanged,show};')(document,{getItem:()=>null},async()=>({ok:true,json:async()=>[]}),()=>{});
if(api.outputChoices().join()!=='youtube')throw Error('Default video missing');
document.querySelector('#export-spotify').checked=true;api.outputChoiceChanged();
if(api.outputChoices().length!==2||!api.outputCreateLabel().includes('video and podcast'))throw Error('Both choices missing');
document.querySelector('#export-youtube').checked=false;
if(!api.outputCreateLabel().includes('podcast audio'))throw Error('Podcast label misleading');
document.querySelector('#export-spotify').checked=false;api.outputChoiceChanged();
if(!document.querySelector('#export-help').textContent.includes('at least one'))throw Error('Empty choice guidance missing');
api.show({id:'podcast',status:{stage:'Finished'},plan:null,podcast:true,export_outputs:['spotify']});
if(api.outputChoices().join()!=='spotify'||!document.querySelector('#jobs').innerHTML.includes('Download podcast MP3'))throw Error('Saved podcast choices or download missing');
console.log('YouTube defaults, both/Spotify choices, empty guidance and podcast downloads passed.');

document.querySelector('#export-spotify').checked=true;document.querySelector('#export-youtube').checked=false;document.querySelector('#export-spotify').onchange();
api.show({id:'new-service',status:{stage:'Finished'},plan:null,export_outputs:['youtube']});
if(api.outputChoices().join()!=='spotify')throw Error('Preparing/selecting a service overwrote the user’s destination choice');
