from .common import ROOT, BIN, read_json, write_json, command, status

def captions(job):
    files=sorted(job.glob('source.en*.json3'))
    if not files: return None
    segments=[]
    for event in read_json(files[0]).get('events',[]):
        text=''.join(s.get('utf8','') for s in event.get('segs',[])).strip()
        if not text: continue
        start=event.get('tStartMs',0)/1000
        segments.append({'start':start,'end':start+event.get('dDurationMs',0)/1000,'text':text})
    return segments or None

def split_gaps(segments):
    result=[]
    for s in segments:
        words=s.get('words',[])
        if not words:
            result.append(s); continue
        groups=[[]]
        for word in words:
            if groups[-1] and word['start']-groups[-1][-1]['end']>1.5: groups.append([])
            groups[-1].append(word)
        for group in groups:
            result.append({'start':group[0]['start'],'end':group[-1]['end'],'text':''.join(w['word'] for w in group).strip(),'words':group})
    return result

def transcribe(job, video):
    cache=job/'transcript.json'
    if cache.exists():
        result=read_json(cache); result['segments']=split_gaps(result['segments']); return result
    segments=captions(job)
    if segments:
        result={'method':'youtube-captions','segments':segments}
    else:
        status(job,'Preparing speech audio','Extracting the voice channel for local transcription')
        audio=job/'speech.wav'
        from .render import mono_filter
        from .common import probe
        duration=float(probe(video)['format']['duration'])
        status(job,'Preparing speech audio','Extracting the voice channel for local transcription',total_seconds=duration)
        mono=mono_filter(job,video,duration*.5,min(30,duration*.5))
        command([BIN/'ffmpeg','-y','-i',video,'-vn','-af',mono,'-ac','1','-ar','16000',audio],job,'speech-audio')
        status(job,'Transcribing','Loading the local speech model',percent=0)
        from faster_whisper import WhisperModel
        model=WhisperModel('small.en',device='cpu',compute_type='int8',cpu_threads=6,download_root=str(ROOT/'.models/whisper'))
        stream, info=model.transcribe(str(audio),language='en',beam_size=3,vad_filter=True,word_timestamps=True,
            initial_prompt='Christ Church Southampton. Bible reading, sermon, scripture, chapter, verses. Let us pray.')
        segments=[]
        for s in stream:
            segments.append({'start':s.start,'end':s.end,'text':s.text.strip(),
                'words':[{'start':w.start,'end':w.end,'word':w.word} for w in (s.words or [])]})
            if len(segments)%5==0:
                status(job,'Transcribing',f'Processed up to {int(s.end)//60} minutes; local speech recognition',percent=min(99.9,s.end/duration*100))
                write_json(job/'transcript.partial.json',{'segments':segments})
        result={'method':'local-whisper-small.en','segments':segments}
    result['segments']=split_gaps(result['segments'])
    write_json(cache,result)
    (job/'transcript.txt').write_text('\n'.join(f"{s['start']:09.2f}–{s['end']:09.2f} {s['text']}" for s in result['segments']))
    return result
