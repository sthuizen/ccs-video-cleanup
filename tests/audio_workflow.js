// Exercise the shipped workflow state and reset behaviour without rendering a church job.
const script=await Deno.readTextFile('ccs/audio-review.js');
const elements=new Map(),ids=['natural','balanced','strong'];
const controls=['suppression','hiss','rumble','clarity','compression','loudness'];
const createButtons=[...ids,'custom'].map(id=>element('create-'+id,{create:id}));
const tweakButtons=ids.map(id=>element('tweak-'+id,{tweak:id}));
const resetButton=element('reset',{});resetButton.attrs['data-reset-base']='';
const cards=[...ids,'custom'].map(id=>element('card-'+id,{trial:id}));
const steps=['source','review','audio','tune','output'];
const navButtons=steps.map(id=>element('nav-'+id,{step:id}));
function element(id,dataset={}){if(!elements.has(id))elements.set(id,{id,dataset,value:'',attrs:{},innerHTML:'',textContent:'',classList:{toggle(){}},focus(){this.focused=true},scrollIntoView(){this.scrolled=true},setAttribute(k,v){this.attrs[k]=v},hasAttribute(k){return k in this.attrs},querySelector(){return element('summary-'+id)},querySelectorAll:all});return elements.get(id)}
function all(selector){return selector==='[data-create]'?createButtons:selector==='[data-tweak]'?tweakButtons:selector==='[data-trial]'?cards:selector==='[data-step]'?navButtons:selector==='[data-reset-base]'?[resetButton]:selector==='input[type=range]'?controls.map(k=>element('tune-'+k)):selector==='button'?[...createButtons,...tweakButtons,resetButton,element('audio-custom'),element('audio-continue')]:[]}
const document={querySelector:s=>element(s.replace(/^#/,'')),querySelectorAll:all};
const storage=new Map(),localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)};
const base={suppression:20,hiss:8,rumble:75,clarity:0,compression:1,loudness:-20};
const manifest=(revision,suppression)=>({revision,selection:{start:10,end:100},enhancer_available:true,samples:[{start:10,duration:18,label:'Quiet'},{start:50,duration:18,label:'Loud'}],originals:['one','two'],trials:[...ids.map(id=>({id,label:id,description:'Preset',parameters:{...base,suppression:id==='natural'?8:id==='strong'?28:20},clips:['one','two']})),{id:'custom',label:'Your adjustment',description:'Custom',parameters:{...base,suppression},clips:['one','two']}]});
let row={id:'fixture',status:{stage:'Choose audio',active:false},plan:{start:10,end:100,title:'Title',passage:'Romans 2',date:'2026-10-04'},audio_review_current:true,audio_review:manifest('first',19)};
const sent=[];const post=async(path,data)=>sent.push({path,data});
const api=new Function('document','localStorage','esc','stamp','post','refresh','rows','selected',script+';return {audioReviewMount,audioReviewUpdate,workflowPending,workflowSync,workflowGo,audioReset,audioCreate,get:()=>audioView};')(document,localStorage,String,String,post,async()=>{},[row],row.id);
const form=()=>({id:row.id,start:10,end:100});
api.audioReviewMount(row,form);api.workflowSync(row);
const markup=element('audio-content').innerHTML;
if(markup.includes('data-tweak="custom"'))throw Error('Custom test still offers tweak action');
if(!markup.includes('data-reset-base>Reset to chosen preset'))throw Error('Custom reset missing');
if(!markup.includes('id="step-tune"')||!markup.includes('id="step-audio"'))throw Error('Missing step sections');
tweakButtons[1].onclick();
if(api.get().basePreset!=='balanced'||element('tune-suppression').value!==20||!element('step-tune').open)throw Error('Preset did not open tuning');
if(element('step-audio').open||!element('summary-step-tune').focused)throw Error('Next step is not focused');
element('tune-suppression').value=17;element('tune-suppression').oninput();
if(!api.get().dirty||!createButtons[3].disabled)throw Error('Untested settings can be applied');
api.workflowPending('tune');row={...row,audio_review:manifest('second',17)};api.audioReviewUpdate(row);api.workflowSync(row);
if(!element('adjusted-test').focused)throw Error('Adjusted test did not receive focus');
if(api.get().selected!=='custom'||element('tune-suppression').value!==17)throw Error('New custom test not loaded');
resetButton.onclick();
if(element('tune-suppression').value!==20||api.get().basePreset!=='balanced'||!api.get().dirty)throw Error('Reset lost original preset or enables stale adjustment');
api.workflowPending('tune');row={...row,audio_review:manifest('third',20)};api.audioReviewUpdate(row);api.workflowSync(row);
api.audioReviewMount(row,form); // Reload editor: remembered base must survive.
resetButton.onclick();
if(element('tune-suppression').value!==20||api.get().basePreset!=='balanced')throw Error('Reload lost reset target');
api.workflowGo('review');api.workflowSync(row);
if(!element('step-review').open||element('step-audio').open)throw Error('Polling changed explored step');
for(let i=0;i<3;i++){await createButtons[i].onclick();if(sent[i].data.audio_trial!==ids[i]||sent[i].data.audio_revision!=='third')throw Error('Wrong tested preset submitted')}
console.log('Workflow navigation, custom placement, preset reset across revisions/reload, dirty-state protection, and three direct render actions passed.');
const downloading={id:'new-service',plan:null,status:{stage:'Downloading',active:true}};
api.workflowPending('output');api.workflowSync(downloading);
if(!element('step-source').open||element('step-output').open||api.get()!==null)throw Error('Download kept a previous audio editor or focused Video');
element('summary-step-source').focused=false;element('step-source').scrolled=false;
for(let i=0;i<3;i++)api.workflowSync(downloading);
if(element('summary-step-source').focused||element('step-source').scrolled)throw Error('Download polling steals focus or scrolls back to Service');
if(!element('workflow').innerHTML.includes('1. Service<span>Working</span>'))throw Error('Download step is not marked Working');
console.log('A new download focuses Service and clears prior audio state.');
for(const trial of ['balanced','custom']){
 const rendering={...row,status:{stage:'Rendering',active:true},audio_choice:{revision:row.audio_review.revision,trial}};
 api.workflowSync(rendering);
 if(!element('workflow').innerHTML.includes('4. Tweak<span>✓ Done</span>'))throw Error('Accepted audio leaves Tweak unfinished');
 if(!element('output-wait').textContent.includes('Creating your exports'))throw Error('Render still asks for audio selection');
}
api.audioReviewMount(row,form);
const testing={...row,status:{stage:'Preparing audio tests',active:true},audio_busy:true};
api.audioReviewUpdate(testing);api.workflowSync(testing);
if(element('audio-activity').hidden||!element('workflow').innerHTML.includes('3. Listen<span>Working</span>'))throw Error('Audio samples have no visible working indicator');
api.workflowGo('review');element('step-audio').scrolled=false;
api.workflowSync(testing);
if(!element('step-review').open||element('step-audio').scrolled)throw Error('Sample polling resets the explored step or scroll position');
api.audioReviewUpdate(row);api.workflowSync(row);
if(!element('audio-activity').hidden)throw Error('Audio working indicator remains after completion');
console.log('Sample activity and accepted preset/custom completion states passed.');
