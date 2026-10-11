"""Local, revisioned listening trials. Never writes production audio caches."""
import json
import math
import subprocess
import uuid
import numpy as np
from .common import BIN, command, exclusive, process_options, read_json, write_json, seconds
from .acquire import video_path
from . import audio

DEFAULTS = dict(suppression=20, hiss=8, rumble=75, clarity=0, compression=1, loudness=-20)
BOUNDS = dict(suppression=(0,30), hiss=(0,12), rumble=(40,140), clarity=(0,4), compression=(1,3), loudness=(-24,-16))
PRESETS = [
    ('natural', 'Natural voice', 'Gentler noise removal; protects soft words and the room’s natural sound.', {**DEFAULTS, 'suppression':8, 'hiss':3}),
    ('balanced', 'Balanced cleanup', 'The established church settings. Start by listening here.', DEFAULTS),
    ('strong', 'Stronger cleanup', 'More background reduction; check for thin or watery quiet words.', {**DEFAULTS, 'suppression':28, 'hiss':10}),
]

def parameters(value):
    if not isinstance(value, dict) or set(value)-set(BOUNDS):
        raise ValueError('Use the audio controls supplied by the app.')
    result={**DEFAULTS, **value}
    for key,(lo,hi) in BOUNDS.items():
        number=result[key]
        if isinstance(number,bool) or not isinstance(number,(int,float)) or not math.isfinite(number) or not lo<=number<=hi:
            raise ValueError(f'{key} must be between {lo} and {hi}.')
        result[key]=float(number)
    return result

def settings(value):
    p=parameters(value); result=dict(audio.profile())
    if not p['suppression']: result.pop('enhancer',None); result.pop('enhancer_sha256',None)
    elif result.get('enhancer'): result['attenuation_limit_db']=p['suppression']
    chain=[f"highpass=f={p['rumble']}", 'lowpass=f=10000',
           f"afftdn=nf=-40:nr={max(.01,p['hiss'])}:tn=1:gs=8:om={'o' if p['hiss'] else 'i'}",
           'agate=threshold=0.004:ratio=1.5:range=0.5:attack=10:release=300:knee=4:detection=rms']
    if p['clarity']: chain.append(f"equalizer=f=2500:t=q:w=0.8:g={p['clarity']}")
    if p['compression']>1:
        chain.append(f"acompressor=threshold=0.0630957:ratio={p['compression']}:attack=20:release=250:makeup=1:knee=2.828:detection=rms")
    result.update(filter=','.join(chain), target_lufs=p['loudness'], controls=p, review_version=1)
    if not result.get('enhancer'): result['method']='ffmpeg-gentle-speech-cleanup'
    return result

def identity(job, plan):
    video=video_path(job); stat=video.stat()
    return dict(start=float(plan['start']), end=float(plan['end']), source=str(video),
                source_size=stat.st_size, source_modified=stat.st_mtime_ns)

def selected_profile(job, plan):
    path=job/'audio-choice.json'
    if path.exists():
        saved=read_json(path)
        if saved['selection']==identity(job,plan): return settings(saved['parameters'])
    return audio.profile()

def windows(job, plan, mono):
    """Rank bounded excerpts by voiced RMS using existing transcript coverage.

    This proposes listening locations, not semantic speaker identification.
    """
    start,end=float(plan['start']),float(plan['end']); length=min(18.,end-start)
    if length<5: raise ValueError('Select at least five seconds for an audio comparison.')
    transcript=read_json(job/'transcript.json') if (job/'transcript.json').exists() else {}
    segments=transcript.get('segments',[])
    candidates=np.linspace(start,end-length,min(24,max(2,int((end-start)/length))))
    ranked=[]
    for t in candidates:
        overlaps=[s for s in segments if s.get('text','').strip() and '[music]' not in s.get('text','').lower() and s['start']<t+length and s['end']>t]
        if segments and not overlaps: continue
        raw=subprocess.check_output([str(BIN/'ffmpeg'),'-v','error','-ss',str(t),'-i',str(video_path(job)),
            '-t',str(length),'-vn','-af',mono,'-ar','8000','-f','f32le','-'], **process_options())
        data=np.frombuffer(raw,dtype='<f4'); frame=160
        if len(data)<frame: continue
        rms=np.sqrt(np.mean(data[:len(data)//frame*frame].reshape(-1,frame)**2,axis=1))
        if overlaps:
            times=t+np.arange(len(rms))*.02
            mask=np.zeros(len(rms),dtype=bool)
            for s in overlaps: mask|=(times>=s['start'])&(times<s['end'])
            if np.mean(mask)<.45: continue
            rms=rms[mask]
        active=rms[rms>max(.0001,float(np.percentile(rms,20)))] if len(rms) else np.array([])
        if len(active): ranked.append((float(np.median(active)),float(t)))
    if not ranked: raise ValueError('No usable speech sample found. Choose sample times manually.')
    ranked.sort(); quiet=ranked[max(0,int((len(ranked)-1)*.2))][1]
    other=[x for x in ranked if abs(x[1]-quiet)>=length]
    loud=(other or ranked)[-1][1]
    return [dict(label='Quiet voice',start=quiet,duration=length),dict(label='Louder voice',start=loud,duration=length)]

def validate_samples(plan, values):
    length=min(18.,float(plan['end'])-float(plan['start']))
    if length<5: raise ValueError('Select at least five seconds for an audio comparison.')
    if not isinstance(values,list) or len(values)!=2: raise ValueError('Choose a quiet and a louder sample time.')
    result=[]
    for label,value in zip(('Quiet voice','Louder voice'),values):
        t=seconds(value)
        if not math.isfinite(t) or not float(plan['start'])<=t<=float(plan['end'])-length:
            raise ValueError(f'{label} sample must fit inside the selected clip ({length:g} seconds).')
        result.append(dict(label=label,start=t,duration=length))
    return result

def measure(job,path):
    command([BIN/'ffmpeg','-i',path,'-af','loudnorm=I=-20:TP=-2:LRA=50:print_format=json','-f','null','-'],job,'trial-measure')
    import re
    found=re.findall(r'\{\s*"input_i".*?\}',(job/'trial-measure.log').read_text(errors='replace'),re.S)
    if not found: raise RuntimeError('Cannot measure the listening trial.')
    return json.loads(found[-1])

@exclusive
def create(job, plan, sample_times=None, custom=None):
    from .render import mono_filter
    selection=identity(job,plan)
    root=job/'audio-trials'/uuid.uuid4().hex; root.mkdir(parents=True)
    mono=mono_filter(root,video_path(job),selection['start'],selection['end']-selection['start'])
    samples=validate_samples(plan,sample_times) if sample_times is not None else windows(job,plan,mono)
    old=job/'audio-trials.json'
    previous=read_json(old) if old.exists() else None
    retain=bool(custom is not None and previous and previous['selection']==selection and previous['samples']==samples)
    choices=list(PRESETS) if not retain else []
    if custom is not None: choices.append(('custom','Your adjustment','Your tuned settings; compare with the previous trials.',parameters(custom)))
    trials=[]
    for name,label,description,params in choices:
        folder=root/name; folder.mkdir(); processed=[]
        configured=settings(params)
        for i,sample in enumerate(samples):
            work=folder/str(i); work.mkdir()
            path,_=audio.prepare(work,video_path(job),sample['start'],sample['duration'],mono,configured)
            processed.append(path)
        joined=folder/'joined.wav'
        command([BIN/'ffmpeg','-y','-i',processed[0],'-i',processed[1],'-filter_complex','[0:a][1:a]concat=n=2:v=0:a=1[out]',
                 '-map','[out]','-c:a','pcm_f32le',joined],folder,'trial-join')
        norm,summary=audio.normalization(measure(folder,joined),configured)
        clips=[]
        for i,path in enumerate(processed):
            output=folder/f'{i}.m4a'
            command([BIN/'ffmpeg','-y','-i',path,'-af',norm+',aformat=sample_fmts=s32','-c:a','aac','-b:a','128k',output],folder,'trial-encode')
            decoded=subprocess.check_output([str(BIN/'ffmpeg'),'-v','error','-i',str(output),'-f','f32le','-'], **process_options())
            signal=np.frombuffer(decoded,dtype='<f4')
            if not len(signal) or not np.isfinite(signal).all(): raise RuntimeError('Invalid preview audio.')
            clips.append(str(output.relative_to(job)))
        trials.append(dict(id=name,label=label,description=description,parameters=parameters(params),clips=clips,playback=summary,profile=configured))
    # Source reference uses one shared gain across both excerpts, preserving their contrast.
    reference=[]
    for i,sample in enumerate(samples):
        path=root/f'original-{i}.wav'
        command([BIN/'ffmpeg','-y','-ss',str(sample['start']),'-i',video_path(job),'-t',str(sample['duration']),
                 '-vn','-af',mono,'-ar','48000','-c:a','pcm_f32le',path],root,'reference-extract')
        reference.append(path)
    joined=root/'original-joined.wav'
    command([BIN/'ffmpeg','-y','-i',reference[0],'-i',reference[1],'-filter_complex','[0:a][1:a]concat=n=2:v=0:a=1[out]',
             '-map','[out]','-c:a','pcm_f32le',joined],root,'reference-join')
    norm,_=audio.normalization(measure(root,joined),{**audio.profile(),'target_lufs':-20})
    originals=[]
    for i,path in enumerate(reference):
        output=root/f'original-{i}.m4a'
        command([BIN/'ffmpeg','-y','-i',path,'-af',norm,'-c:a','aac','-b:a','128k',output],root,'reference-encode')
        originals.append(str(output.relative_to(job)))
    result=dict(revision=root.name,selection=selection,samples=samples,trials=trials,originals=originals,
                enhancer_available=bool(audio.profile().get('enhancer')))
    if retain: result['trials']=previous['trials'][:3]+trials
    write_json(root/'manifest.json',result)
    write_json(old,result)
    return result

def tested_choice(job,plan,revision,trial_id):
    manifest=read_json(job/'audio-trials.json') if (job/'audio-trials.json').exists() else {}
    if manifest.get('revision')!=revision or manifest.get('selection')!=identity(job,plan):
        raise ValueError('The clip or previews changed. Recreate and listen to the current audio tests first.')
    trial=next((t for t in manifest['trials'] if t['id']==trial_id),None)
    if not trial: raise ValueError('Choose one of the tested audio versions.')
    # Never accept filter strings/executable paths from a browser request.
    configured=settings(trial['parameters'])
    if configured!=trial['profile']: raise ValueError('The audio tools changed. Recreate the previews first.')
    return configured

def choose(job,plan,revision,trial_id):
    configured=tested_choice(job,plan,revision,trial_id)
    write_json(job/'audio-choice.json',dict(selection=identity(job,plan),parameters=configured['controls'],revision=revision,trial=trial_id))
    return configured
