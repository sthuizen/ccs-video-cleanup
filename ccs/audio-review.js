/* In-app listening and tuning. Polling never replaces unsaved form controls. */
let audioView=null;
const audioControls=[
 ['suppression','Background noise reduction',0,30,1,'dB','Higher removes more room noise. Lower this first if quiet words sound watery or disappear. Zero turns off the local speech enhancer.'],
 ['hiss','Steady hiss',0,12,1,'dB','For fan noise and steady hiss. Too much can make consonants metallic. Try small changes of 1–2 dB.'],
 ['rumble','Low rumble',40,140,5,'Hz','Higher removes more handling noise and low hum. Lower it if a deeper voice sounds thin.'],
 ['clarity','Voice clarity',0,4,.5,'dB','A small lift helps consonants stand out. Too much can exaggerate harshness, hiss and “s” sounds.'],
 ['compression','Even out voice levels',1,3,.25,':1','Reduces loud speech before the final volume adjustment. 1 means off. Try 1.5–2 for large level changes; more can bring room noise forward.'],
 ['loudness','Listening volume',-24,-16,1,'LUFS','Closer to −16 is louder. This changes playback volume, not noise separation. Peak protection stays on; actual loudness can be lower when gain is capped.']
];
const workflowSteps=[['source','1. Service'],['review','2. Clip & intro'],['audio','3. Listen'],['tune','4. Tweak'],['output','5. Export']];
let workflowState={job:null,stage:null,revision:null,current:'source',pending:null};
function workflowReset(){
 audioView=null;workflowState={job:null,stage:null,revision:null,current:'source',pending:null};
 const source=document.querySelector('#step-source');if(source)source.open=true;
 workflowPaint(null);
}
function workflowPending(step){workflowState.pending=step}
function workflowGo(step,focus=true){
 const section=document.querySelector('#step-'+step);if(!section)return;
 for(const [id] of workflowSteps){const other=document.querySelector('#step-'+id);if(other&&other!==section)other.open=false}
 document.querySelectorAll('video,audio').forEach(media=>media.pause());
 section.open=true;workflowState.current=step;
 if(focus){section.querySelector('summary')?.focus({preventScroll:true});section.scrollIntoView({behavior:'smooth',block:'start'})}
 workflowPaint(audioView?.row||rows.find(r=>r.id===selected));
}
function workflowPaint(row){
 const nav=document.querySelector('#workflow');if(!nav)return;
 const p=row?.plan,m=row?.audio_review,v=audioView;
 const ready=Boolean(p&&['title','passage','date','start','end'].every(k=>p[k]!=null&&String(p[k]).trim()!==''));
 const accepted=Boolean(row?.audio_choice&&row.audio_review_current&&row.audio_choice.revision===m?.revision);
 const chosen=Boolean(v?.selected||accepted);
 const testing=Boolean(row?.status?.stage==='Preparing audio tests'||v?.testing);
 const stage=row?.status?.stage;
 const rendering=Boolean(row?.status?.active&&['Cleaning audio','Enhancing voice','Measuring camera movement','Rendering','Creating intro','Joining intro','Checking video','Preparing preview','Creating podcast','Checking podcast'].includes(stage));
 const finished=Boolean((row?.outputs_ready??row?.finished)&&stage==='Finished');
 const statuses={source:p?'Done':row?.status?.active?'Working':row?'Needs attention':'Start here',review:ready?'Done':p?'Needs details':'Pending',audio:testing?'Working':chosen?'Done':row?.audio_review_current?'Ready':'Pending',tune:accepted?'Done':v?.dirty?'Needs new test':v?.selected==='custom'?'Test ready':v?.basePreset?'Editing':'Optional',output:finished?'Done':rendering?'Working':chosen&&!v?.dirty?'Ready':'Pending'};
 const enabled={source:true,review:Boolean(p),audio:Boolean(p),tune:Boolean(v?.basePreset||m?.trials.some(t=>t.id==='custom')),output:Boolean(p)};
 const markup=workflowSteps.map(([id,label])=>`<button data-step="${id}" class="${statuses[id]==='Done'?'done':''}" ${workflowState.current===id?'aria-current="step"':''} ${enabled[id]?'':'disabled'}>${label}<span>${statuses[id]==='Done'?'✓ ':''}${statuses[id]}</span></button>`).join('')+'<div id="workflow-live" role="status" aria-live="polite" hidden></div>';
 if(nav.dataset.key!==markup){nav.dataset.key=markup;nav.innerHTML=markup;nav.querySelectorAll('[data-step]').forEach(b=>b.onclick=()=>workflowGo(b.dataset.step))}
 const messages={source:row?.status?.active?'Downloading and analysing your service. Progress appears below; clip and audio steps will open when ready.':'Start with the completed service URL. Download and analysis run locally.',review:'Check the selected reading and sermon, then save any corrections.',audio:'Listen to the three presets. Create your selected exports directly, or choose one to tweak.',tune:v?.dirty?'Settings changed. Recreate the test before using your adjustment.':'Adjust, recreate, and listen. Reset always returns to your chosen preset.',output:finished?'Your exports are ready. Check the beginning and ending before uploading.':rendering?'Your exports are being created. You can explore the completed steps while it runs.':'Exporting starts after you choose tested audio.'};
 document.querySelector('#workflow-next').textContent=testing?'Making quiet and louder audio samples locally. Please wait; the players will appear when ready.':messages[workflowState.current||'source'];
 const make=document.querySelector('#render');if(make)make.disabled=testing||rendering;
 const output=document.querySelector('#output-wait');if(output)output.textContent=rendering?'Creating your exports with the audio you chose. Progress appears above.':messages.output;
}
function workflowSync(row){
 const first=workflowState.job!==row.id;
 if(first){if(audioView?.row.id!==row.id)audioView=null;workflowState.job=row.id;workflowState.stage=null;workflowState.revision=null;workflowState.current=null}
 const stage=row.status.stage,revision=row.audio_review?.revision;
 const stageChanged=stage!==workflowState.stage;
 const newTests=revision&&revision!==workflowState.revision;
 const adjustedReady=newTests&&workflowState.pending==='tune';
 for(const [id] of workflowSteps){const section=document.querySelector('#step-'+id);const summary=section?.querySelector('summary');if(summary)summary.onclick=event=>{if(!section.open){event.preventDefault();workflowGo(id)}}}
 let next=null;
 if(first){next=!row.plan?'source':stage==='Finished'&&(row.outputs_ready??row.finished)?'output':!['title','date','passage'].every(k=>row.plan[k])?'review':'audio'}
 else if(stage!==workflowState.stage){
  if(stage==='Finished'&&(row.outputs_ready??row.finished))next='output';
  else if(['Rendering','Creating podcast','Checking podcast'].includes(stage)&&!['Rendering','Creating intro','Joining intro','Checking video'].includes(workflowState.stage))next='output';
  else if(stage==='Needs information')next='review';
 }
 if(newTests&&workflowState.pending){next=workflowState.pending;workflowState.pending=null}
 if(!row.plan&&(first||workflowState.current!=='source')){next='source'}
 workflowState.stage=stage;workflowState.revision=revision;
 const notice=document.querySelector('#notice');if(stage==='Choose audio'&&notice?.textContent.startsWith('Making'))notice.textContent='Audio samples are ready. Listen below and choose a version.';
 if(row.plan&&stage==='Preparing audio tests'&&(first||stageChanged))next=workflowState.pending==='tune'?'tune':'audio';
 if(next)workflowGo(next,!first&&next!==workflowState.current);
 if(adjustedReady){const test=document.querySelector('#adjusted-test');if(test){test.tabIndex=-1;test.focus({preventScroll:true});test.scrollIntoView({behavior:'smooth',block:'start'})}}
 workflowPaint(row);
}
function presetMemory(row,value){
 const key='ccs-audio-base-'+row.id,selection=row.audio_review?.selection;
 try{
  if(value){localStorage.setItem(key,JSON.stringify({selection,preset:value}));return value}
  const saved=JSON.parse(localStorage.getItem(key)||'null');
  return JSON.stringify(saved?.selection)===JSON.stringify(selection)?saved?.preset:null;
 }catch{return value||null}
}
function audioReviewMount(row,form){
 const previous=audioView;
 audioView={row,form,key:null,selected:null,dirty:false,basePreset:previous?.row.id===row.id?previous.basePreset:presetMemory(row)};
 document.querySelector('#audio-review').innerHTML='<div id="audio-activity" role="status" hidden><strong>Making audio samples…</strong><p>Processing quiet and louder speech locally. This may take a few minutes.</p><progress aria-label="Making audio samples"></progress></div><div id="audio-content"></div>';
 audioReviewUpdate(row);
}
function audioCard(t,m,row,custom=false){
 const clip=(path,label)=>`<label>${esc(label)}<audio controls preload="metadata" src="/files/${encodeURIComponent(row.id)}/${esc(path)}" aria-label="${esc(label)}"></audio></label>`;
 return `<section ${custom?'id="adjusted-test"':''} class="audio-card" data-trial="${esc(t.id)}"><h3>${esc(t.label)}</h3><p>${esc(t.description)}</p>${t.clips.map((p,i)=>clip(p,m.samples[i].label+' · '+t.label)).join('')}<div class="audio-actions"><button data-create="${esc(t.id)}">${typeof outputCreateLabel==='function'?outputCreateLabel(custom):custom?'Use this adjustment and create video':'Choose and create video'}</button>${custom?'<button class="secondary" data-reset-base>Reset to chosen preset</button>':`<button class="secondary" data-tweak="${esc(t.id)}" aria-pressed="false">Choose and tweak audio</button>`}</div></section>`;
}
function audioReviewUpdate(row){
 if(!audioView||audioView.row.id!==row.id)return;
 audioView.row=row;
 const m=row.audio_review,host=document.querySelector('#audio-content');if(!host)return;
 const valid=m&&row.audio_review_current,key=JSON.stringify([m?.revision,valid]);
 if(key===audioView.key){audioBusy(row);return}
 const wasCustom=workflowState.pending==='tune';
 audioView.key=key;audioView.selected=null;audioView.dirty=false;
 const presets=m?.trials.filter(t=>t.id!=='custom')||[];
 if(!presets.some(t=>t.id===audioView.basePreset))audioView.basePreset=null;
 if(!valid){host.innerHTML='<details id="step-audio" class="workflow-section"><summary>3. Listen and choose audio</summary><p>Save the clip details above, then make three listening tests for this selection.</p><button id="audio-make">Make three audio tests</button></details>';document.querySelector('#audio-make').onclick=()=>audioGenerate();audioBusy(row);return}
 const custom=m.trials.find(t=>t.id==='custom');
 const reference=(p,i)=>`<label>${esc(m.samples[i].label)} · original<audio controls preload="metadata" src="/files/${encodeURIComponent(row.id)}/${esc(p)}"></audio></label>`;
 host.innerHTML=`<details id="step-audio" class="workflow-section"><summary>3. Listen and choose audio</summary><p>Listen to quiet and louder speech at the same listening volume. Check word endings and noise between phrases. Choose a preset to create your selected exports, or open its controls to tweak it.</p>${!m.enhancer_available?'<p class="issues">The local speech enhancer is unavailable; these tests use FFmpeg cleanup.</p>':''}
 <details class="sample-picker"><summary>Explore or change sample passages · ${m.samples.map(s=>esc(stamp(s.start))).join(' and ')}</summary><p>Suggested from speech level and the cached transcript. If a sample contains laughter or the wrong speaker, change its source timestamp. Each sample is ${m.samples[0].duration} seconds.</p><div class="grid">${m.samples.map((s,i)=>`<div><label for="sample-${i}">${esc(s.label)} starts (HH:MM:SS)</label><input id="sample-${i}" value="${esc(stamp(s.start))}"><button class="secondary" data-sample="${i}">Use source player position</button></div>`).join('')}</div><p><button id="audio-resample" class="secondary">Make three tests at these times</button></p></details>
 <details><summary>Compare with the original recording</summary><p>The reference has volume adjustment and peak protection, with noise removal off.</p><div class="grid">${m.originals.map(reference).join('')}</div></details>
 <div class="audio-cards">${presets.map(t=>audioCard(t,m,row)).join('')}</div><details><summary>How the listening volume is matched</summary><p>Quiet and louder samples share one volume adjustment per version. The full clip measures volume across the whole selection, so its final gain may differ slightly.</p></details></details>
 <details id="step-tune" class="workflow-section audio-tune"><summary>4. Tweak and test your audio <small>· optional</small></summary><div id="audio-selection" role="status">Choose and tweak a preset in the listening step to load its settings.</div><p id="tune-help">Change one control at a time, recreate the test, then listen. Reset returns to the original preset, even after several adjustments.</p><div class="grid">${audioControls.map(([k,label,lo,hi,step,unit,help])=>`<div><label for="tune-${k}">${label} · <output id="value-${k}"></output> ${unit}</label><input type="range" id="tune-${k}" min="${lo}" max="${hi}" step="${step}" disabled aria-describedby="help-${k}"><details class="control-help"><summary>What this changes</summary><small id="help-${k}">${help}</small></details></div>`).join('')}</div><p><button id="audio-custom" disabled>Recreate test with my adjustments</button>${!custom?' <button id="audio-reset" class="secondary" data-reset-base disabled>Reset to chosen preset</button>':''}</p><p class="adjustment-status" id="adjustment-status" role="status"></p>${custom?audioCard(custom,m,row,true):'<p><button id="audio-continue" disabled>Use chosen preset and create selected exports</button></p>'}</details><p id="audio-error" class="error" role="alert"></p>`;
 document.querySelectorAll('video,audio').forEach(a=>a.onplay=()=>document.querySelectorAll('video,audio').forEach(b=>{if(a!==b)b.pause()}));
 host.querySelectorAll('[data-sample]').forEach(b=>b.onclick=()=>{const player=document.querySelector('#source');if(player)document.querySelector('#sample-'+b.dataset.sample).value=stamp(player.currentTime)});
 host.querySelectorAll('[data-create]').forEach(b=>b.onclick=()=>audioCreate(b.dataset.create));
 host.querySelectorAll('[data-tweak]').forEach(b=>b.onclick=()=>{audioSelect(b.dataset.tweak);workflowGo('tune')});
 host.querySelectorAll('[data-reset-base]').forEach(b=>b.onclick=audioReset);
 document.querySelector('#audio-resample').onclick=()=>audioGenerate(true);
 document.querySelector('#audio-custom').onclick=()=>audioGenerate(true,true);
 for(const [k] of audioControls)document.querySelector('#tune-'+k).oninput=()=>{document.querySelector('#value-'+k).textContent=document.querySelector('#tune-'+k).value;audioView.dirty=true;document.querySelector('#adjustment-status').textContent='Settings changed. Recreate and listen to a new test before creating your exports.';audioBusy(row);workflowPaint(row)};
 if(document.querySelector('#audio-continue'))document.querySelector('#audio-continue').onclick=()=>audioCreate();
 if(custom&&audioView.basePreset&&(wasCustom||row.audio_choice?.trial==='custom'))audioSelect('custom');
 else if(audioView.basePreset)audioSelect(audioView.basePreset);
 else if(row.audio_choice?.revision===m.revision)audioSelect(row.audio_choice.trial);
 if(wasCustom&&custom){document.querySelector('#notice').textContent='Your adjusted test is ready. Listen below, then create your exports or keep tweaking.'}
 audioBusy(row);
}
function audioSelect(id){
 const t=audioView.row.audio_review.trials.find(t=>t.id===id);if(!t)return;
 audioView.selected=id;audioView.dirty=false;
 if(id!=='custom'){audioView.basePreset=id;presetMemory(audioView.row,id)}
 document.querySelectorAll('[data-trial]').forEach(c=>c.classList.toggle('chosen',c.dataset.trial===id));
 document.querySelectorAll('[data-tweak]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.tweak===audioView.basePreset)));
 for(const [k] of audioControls){const input=document.querySelector('#tune-'+k);input.value=t.parameters[k];input.disabled=false;document.querySelector('#value-'+k).textContent=input.value}
 const base=audioView.row.audio_review.trials.find(t=>t.id===audioView.basePreset);
 document.querySelector('#audio-selection').textContent=base?'Chosen preset: '+base.label+'. '+(id==='custom'?'Your adjusted settings are loaded.':'Its original settings are loaded.'):'Your adjusted settings are loaded. Choose a preset in the listening step to enable reset.';
 const custom=audioView.row.audio_review.trials.find(t=>t.id==='custom');
 if(id!=='custom'&&custom)audioView.dirty=audioControls.some(([k])=>t.parameters[k]!==custom.parameters[k]);
 document.querySelector('#adjustment-status').textContent=id==='custom'?'Listen to this adjusted test before using it.':audioView.dirty?'The earlier adjusted test uses different settings. Recreate it to hear the preset settings now loaded.':'Adjust a control, then recreate the listening test.';
 audioBusy(audioView.row);workflowPaint(audioView.row);
}
function audioReset(){
 if(!audioView.basePreset)return;
 audioSelect(audioView.basePreset);
 document.querySelector('#adjustment-status').textContent='Reset to your chosen preset. Recreate the test to replace the previous adjustment.';
 audioView.dirty=Boolean(audioView.row.audio_review.trials.some(t=>t.id==='custom'));
 audioBusy(audioView.row);workflowGo('tune');
}
function audioBusy(row){
 const host=document.querySelector('#audio-review');if(!host)return;
 const busy=Boolean(row.audio_busy||audioView.submitting);
 const activity=document.querySelector('#audio-activity');if(activity)activity.hidden=!(row.status.stage==='Preparing audio tests'||audioView.testing);
 host.querySelectorAll('button').forEach(b=>{
  const needsSelection=['audio-custom','audio-continue'].includes(b.id);
  const reset=b.hasAttribute('data-reset-base');
  const custom=b.dataset.create==='custom';
  if(b.hasAttribute('data-create')&&typeof outputCreateLabel==='function')b.textContent=outputCreateLabel(custom);
  const noOutput=typeof outputChoices==='function'&&!outputChoices().length;
  b.disabled=busy||((b.hasAttribute('data-create')||b.id==='audio-continue')&&noOutput)||(needsSelection&&!audioView.selected)||(reset&&!audioView.basePreset)||((b.id==='audio-continue'||custom)&&audioView.dirty);
 });
 host.querySelectorAll('input[type=range]').forEach(input=>input.disabled=busy||!audioView.selected);
}
async function audioCreate(id){
 if(audioView.submitting||audioView.row.audio_busy)return;
 if(id==='custom'&&audioView.dirty)return;
 if(id){audioSelect(id);if(id!=='custom')audioView.dirty=false}
 if(!audioView.selected||audioView.dirty)return;
 const view=audioView;view.submitting=true;audioBusy(view.row);
 try{const d=view.form();if(typeof outputChoices==='function'){d.outputs=outputChoices();if(!d.outputs.length)throw Error('Choose at least one export destination.')}d.audio_revision=view.row.audio_review.revision;d.audio_trial=view.selected;await post('/api/render',d);document.querySelector('#notice').textContent='Creating your selected exports with the audio you chose…';workflowPending('output');workflowGo('output');await refresh()}
 catch(e){(document.querySelector('#audio-error')||document.querySelector('#notice')).textContent=e.message}
 finally{view.submitting=false;if(audioView===view)audioBusy(view.row)}
}
async function audioGenerate(manual=false,custom=false){
 const view=audioView;if(view.submitting||view.row.audio_busy)return;
 view.submitting=true;view.testing=true;workflowPending(custom?'tune':'audio');audioBusy(view.row);workflowPaint(view.row);
 try{
  const d=view.form(),m=view.row.audio_review;
  if(manual)d.samples=m.samples.map((s,i)=>{const value=document.querySelector('#sample-'+i).value;return value===stamp(s.start)?s.start:value});
  if(custom){d.parameters={};for(const [k] of audioControls)d.parameters[k]=Number(document.querySelector('#tune-'+k).value)}
  await post('/api/audio-tests',d);workflowPending(custom?'tune':'audio');document.querySelector('#notice').textContent='Making listening tests locally. Your exports wait for your choice.';await refresh();
 }catch(e){(document.querySelector('#audio-error')||document.querySelector('#notice')).textContent=e.message}
 finally{view.submitting=false;view.testing=false;if(audioView===view)audioBusy(view.row)}
}
