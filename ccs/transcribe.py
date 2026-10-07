from .common import ROOT, BIN, MODELS, read_json, write_json, command, status

REFINEMENT_VERSION = 3

def refinement_windows(transcript, plan):
    """Bound expensive local checks to likely reading announcements, not titles."""
    import re
    from .analyze import refs, READ
    if transcript.get('method') != 'youtube-captions':
        return []
    weak = (plan.get('start') is None or plan.get('end') is None or not plan.get('passage')
            or plan.get('evidence', {}).get('passage', {}).get('requires_local_verification')
            or any(re.search(r'interval|reading.*plausible|multiple bible|ending.*approximate|confirm the bible passage', x, re.I)
                   for x in plan.get('issues', [])))
    if not weak:
        return []
    segments = transcript['segments']; duration = float(plan['duration'])
    candidates = []
    reading_times = [float(x['time']) for x in plan.get('candidates', {}).get('readings', [])]
    for s in segments:
        references = refs(s['text'])
        if not references and not READ.search(s['text']):
            continue
        nearby = [x for x in segments if s['start'] - 65 <= x['start'] <= s['start'] + 65]
        score = 2 if any(READ.search(x['text']) for x in nearby) else 0
        if any(abs(s['start']-t) < 80 for t in reading_times):
            score += 3
        if plan.get('passage') and any(x.split(':')[0] == plan['passage'].split(':')[0] for x in references):
            score += 1
        candidates.append((score, float(s['start'])))
    candidates.sort(key=lambda x: (-x[0], x[1]))
    approximate_end = plan.get('end') is not None and any(re.search(r'ending.*approximate', x, re.I) for x in plan.get('issues', []))
    windows = [(max(0, float(plan['end'])-90), min(duration, float(plan['end'])+30))] if approximate_end else []
    for _, center in candidates:
        start = max(0, center - 30); end = min(duration, start + 150)
        if any(start < old_end and end > old_start for old_start, old_end in windows):
            continue
        windows.append((start, end))
        if len(windows) == 3:
            break
    return sorted(windows)

def merge_refinement(segments, windows, replacements):
    # Caption events overlap. Keep outside events only when their midpoint is outside
    # an excerpt, so crossing caption fragments cannot duplicate the recovered words.
    retained = [s for s in segments if not any(a <= (s['start'] + s['end']) / 2 < b for a, b in windows)]
    return sorted(retained + replacements, key=lambda s: (s['start'], s['end']))

def refine_transcript(job, video, transcript, plan):
    """Verify deficient captions locally without replacing the original transcript."""
    import hashlib, json
    windows = refinement_windows(transcript, plan)
    if not windows:
        return transcript
    provenance = {'version': REFINEMENT_VERSION,
        'original_transcript_sha256': hashlib.sha256(json.dumps(transcript, sort_keys=True).encode()).hexdigest(),
        'source_size': video.stat().st_size, 'source_mtime_ns': video.stat().st_mtime_ns,
        'windows': [list(x) for x in windows], 'model': 'small.en', 'beam_size': 5, 'vad_silence_ms': 500,
        'speech_pad_ms': 400, 'condition_on_previous_text': False}
    fingerprint = hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest()
    cache = job/'transcript-refined.json'
    if cache.exists():
        saved = read_json(cache)
        if saved.get('fingerprint') == fingerprint:
            return saved
    from .render import mono_filter
    from faster_whisper import WhisperModel
    model = WhisperModel('small.en', device='cpu', compute_type='int8', cpu_threads=6, download_root=str(MODELS))
    recovered = []; excerpts = []
    for i, (start, end) in enumerate(windows):
        status(job, 'Checking sermon audio', f'Checking speech excerpt {i+1} of {len(windows)} with local speech recognition')
        audio = job/f'speech-check-{i+1}.wav'
        mono = mono_filter(job, video, start, end-start)
        command([BIN/'ffmpeg', '-y', '-ss', str(start), '-t', str(end-start), '-i', video,
                 '-vn', '-af', mono, '-ac', '1', '-ar', '16000', audio], job, f'speech-check-{i+1}')
        stream, _ = model.transcribe(str(audio), language='en', beam_size=5, vad_filter=True,
            word_timestamps=True, condition_on_previous_text=False,
            vad_parameters={'min_silence_duration_ms': 500, 'speech_pad_ms': 400},
            initial_prompt='Christ Church Southampton. Bible reading, scripture, chapter, verses.')
        local = [{'start': s.start+start, 'end': s.end+start, 'text': s.text.strip(),
                  'words': [{'start': w.start+start, 'end': w.end+start, 'word': w.word} for w in (s.words or [])],
                  'source': 'local-whisper-small.en-check'} for s in stream]
        local = split_gaps(local)
        if local:
            recovered.extend(local); excerpts.append([start, end])
    if not recovered:
        return transcript
    result = {'method': 'youtube-captions-with-local-checks', 'fingerprint': fingerprint,
              'provenance': provenance,
              'original_method': transcript['method'], 'verified_windows': excerpts,
              'segments': merge_refinement(transcript['segments'], excerpts, recovered)}
    write_json(cache, result)
    (job/'transcript-refined.txt').write_text('\n'.join(f"{s['start']:09.2f}–{s['end']:09.2f} {s['text']}" for s in result['segments']), encoding='utf-8')
    return result

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
            result.append({**s,'start':group[0]['start'],'end':group[-1]['end'],'text':''.join(w['word'] for w in group).strip(),'words':group})
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
        model=WhisperModel('small.en',device='cpu',compute_type='int8',cpu_threads=6,download_root=str(MODELS))
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
    (job/'transcript.txt').write_text('\n'.join(f"{s['start']:09.2f}–{s['end']:09.2f} {s['text']}" for s in result['segments']), encoding="utf-8")
    return result
