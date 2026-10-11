/* Review the exact files before a separate, typed deletion confirmation. */
let deletionReview=null,libraryKey=null;
function storageSize(bytes){return bytes>=1073741824?(bytes/1073741824).toFixed(1)+' GB':(bytes/1048576).toFixed(1)+' MB'}
function libraryPaint(){
 const list=document.querySelector('#saved-services');if(!list)return;
 const busy=rows.some(r=>r.audio_busy),key=JSON.stringify(rows.map(r=>[r.id,r.plan?.title,r.plan?.date,r.can_delete,r.audio_busy]));
 if(key!==libraryKey){
  libraryKey=key;
  list.innerHTML=rows.length?rows.map(r=>`<div class="saved-service"><button class="secondary saved-open" data-service="${esc(r.id)}">${esc(r.plan?.date||r.id)}${r.plan?.title?' · '+esc(r.plan.title):''}</button>${r.can_delete?`<button class="trash-button secondary" data-trash="${esc(r.id)}" aria-label="Delete ${esc(r.plan?.title||r.id)}" title="Move saved service and its files to Trash">&#128465; Delete</button>`:'<small>Processing or unfinished</small>'}</div>`).join(''):'<p>No saved services.</p>';
  list.querySelectorAll('[data-service]').forEach(b=>b.onclick=()=>{selected=b.dataset.service;lastKey='';refresh()});
  list.querySelectorAll('[data-trash]').forEach(b=>b.onclick=()=>deletionOpen(b.dataset.trash));
 }
 const all=document.querySelector('#delete-all');all.disabled=busy||!rows.length;all.onclick=()=>deletionOpen(null);
 document.querySelector('#library-help').textContent=busy?'Deletion is unavailable while a service is processing.':'Deleting moves the saved source, audio samples, analysis and finished exports to your computer’s Trash. Empty Trash later to reclaim the space.';
}
async function deletionOpen(id){
 const dialog=document.querySelector('#delete-dialog');
 try{
  deletionReview=await post('/api/delete-preview',id?{id}:{all:true});
  document.querySelector('#delete-title').textContent=id?'Delete this saved service?':'Delete all saved services?';
  document.querySelector('#delete-summary').textContent=`${deletionReview.jobs.length} service(s) · ${storageSize(deletionReview.bytes)}. Their saved videos, samples and analysis will move to Trash. Local source files outside the app are preserved.`;
  document.querySelector('#delete-items').innerHTML=deletionReview.jobs.map(j=>`<li>${esc(j.date||'')} ${esc(j.title)}</li>`).join('');
  document.querySelector('#delete-checks').hidden=true;
  document.querySelector('#delete-next').hidden=false;
  document.querySelector('#delete-confirm').hidden=true;
  document.querySelector('#delete-confirm').disabled=true;
  document.querySelector('#delete-ack').checked=false;document.querySelector('#delete-phrase').value='';
  document.querySelector('#delete-error').textContent='';
  document.querySelector('#delete-next').onclick=()=>{
   document.querySelector('#delete-checks').hidden=false;document.querySelector('#delete-next').hidden=true;document.querySelector('#delete-confirm').hidden=false;
   document.querySelector('#delete-phrase-label').textContent='Type '+deletionReview.phrase+' to confirm';document.querySelector('#delete-phrase').focus();
  };
  const changed=()=>{document.querySelector('#delete-confirm').disabled=!(document.querySelector('#delete-ack').checked&&document.querySelector('#delete-phrase').value===deletionReview.phrase)};
  document.querySelector('#delete-ack').onchange=changed;document.querySelector('#delete-phrase').oninput=changed;
  document.querySelector('#delete-cancel').onclick=()=>dialog.close();document.querySelector('#delete-confirm').onclick=deletionConfirm;
  dialog.showModal();document.querySelector('#delete-cancel').focus();
 }catch(e){document.querySelector('#notice').textContent=e.message}
}
async function deletionConfirm(){
 const confirm=document.querySelector('#delete-confirm');confirm.disabled=true;
 try{
  const result=await post('/api/delete',{token:deletionReview.token,phrase:document.querySelector('#delete-phrase').value,acknowledged:document.querySelector('#delete-ack').checked});
  if(result.deleted.includes(selected)){selected=null;lastKey=''}
  document.querySelector('#delete-dialog').close();document.querySelector('#notice').textContent=`Moved ${result.deleted.length} service(s) to Trash. Restore them from your computer’s Trash if needed.`;
  await refresh();
 }catch(e){document.querySelector('#delete-error').textContent=e.message;await refresh()}
}
