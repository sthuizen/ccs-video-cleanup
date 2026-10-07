#!/usr/bin/env python3
"""Make private, voice-matched listening samples from a completed local job.

Example: .venv/bin/python tools/compare_audio.py JOB_ID --start 3000 --seconds 60
Requires a preserved previous-output/finished.mp4 and its validation.json.
"""
import argparse
import html
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from scipy.signal import correlate, correlation_lags
from ccs.common import BIN, JOBS, read_json
from ccs.acquire import video_path
from ccs.render import mono_filter

RATE = 16000

def decode(path, start, seconds, filters='anull'):
    return np.frombuffer(subprocess.check_output([str(BIN/'ffmpeg'), '-v', 'error',
        '-ss', str(start), '-t', str(seconds), '-i', str(path), '-vn', '-af', filters,
        '-ar', str(RATE), '-ac', '1', '-f', 'f32le', '-']), '<f4').copy()

def db(samples):
    return float(20*np.log10(max(1e-12, float(np.sqrt(np.mean(samples.astype('float64')**2))))))

def comparison(job, start, seconds):
    before = job/'previous-output'
    current = read_json(job/'validation.json'); previous = read_json(before/'validation.json')
    if current.get('full_decode') != 'passed': raise ValueError('Render and validate the current output first.')
    for record in (current, previous):
        if not record['plan']['start'] <= start < start+seconds <= record['plan']['end']:
            raise ValueError('The sample must fit inside both the previous and current cuts.')
    with tempfile.TemporaryDirectory(prefix='ccs-channel-check-') as tmp:
        mono = mono_filter(Path(tmp), video_path(job), start, seconds)
    source = decode(video_path(job), start, seconds, mono)
    samples = {'source': source}
    delays = {'source': 0.}
    for name, path, record in (('previous', before/'finished.mp4', previous), ('new', job/'finished.mp4', current)):
        offset = start-record['plan']['start']+5
        trial = decode(path, offset, seconds+.15)
        # Correlate a voiced portion, bounded to plausible processing/codec latency.
        n = min(RATE*15, len(source), len(trial))
        correlations = correlate(trial[:n], source[:n], method='fft')
        lags = correlation_lags(n, n)
        valid = np.abs(lags) <= int(.12*RATE)
        lag = int(lags[valid][np.argmax(correlations[valid])])
        delays[name] = lag/RATE
        samples[name] = decode(path, offset+lag/RATE, seconds)
    count = min(map(len, samples.values()))//160*160
    samples = {name: values[:count] for name,values in samples.items()}
    levels = np.sqrt(np.mean(source[:count].reshape(-1,160)**2,axis=1))
    voice_mask = np.repeat(levels >= np.quantile(levels,.6),160)
    quiet_mask = np.repeat(levels <= np.quantile(levels,.15),160)
    method = 'source top 40% and bottom 15% of 10 ms energy frames; proxies, not clean speech/noise labels'
    transcript = read_json(job/'transcript.json')
    words = sorted((w for s in transcript['segments'] for w in s.get('words',[])
                    if start <= w['start'] < w['end'] <= start+seconds and w['end']-w['start'] <= 2),
                   key=lambda w:w['start'])
    if words:
        voice = np.zeros(count,dtype=bool); pauses = np.zeros(count,dtype=bool)
        for word in words:
            a = word['start']-start; b = word['end']-start
            margin = (b-a)*.1
            voice[int((a+margin)*RATE):int((b-margin)*RATE)] = True
        for left,right in zip(words,words[1:]):
            if right['start']-left['end'] > .5:
                pauses[int((left['end']-start+.15)*RATE):int((right['start']-start-.15)*RATE)] = True
        if voice.sum() >= RATE and pauses.sum() >= RATE*.5:
            voice_mask = voice; quiet_mask = pauses
            method = 'cached source word centres (middle 80%) and gaps >0.5 seconds with 150 ms margins; pauses may contain crowd sound'
    background_mask = quiet_mask & np.repeat(levels < .01,160)
    target = -28.
    out = job/'comparison'; out.mkdir(exist_ok=True)
    metrics = {'source_start_seconds': start, 'duration_seconds': count/RATE,
               'mask': method, 'sample_rate': RATE,
               'quiet_background_mask': 'same source pause/quiet mask, restricted to 10 ms source frames below -40 dBFS',
               'quiet_background_seconds': float(background_mask.sum()/RATE),
               'target_voice_rms_dbfs': target, 'variants': {}}
    for name, values in samples.items():
        gain = target-db(values[voice_mask]); matched = values*10**(gain/20)
        metrics['variants'][name] = {'alignment_delay_seconds': delays[name], 'gain_for_comparison_db': gain,
                                    'matched_quiet_dbfs': db(matched[quiet_mask]), 'matched_peak_dbfs': db(np.array([np.max(np.abs(matched))]))}
        if background_mask.any():
            metrics['variants'][name]['matched_quiet_background_dbfs'] = db(matched[background_mask])
        subprocess.run([str(BIN/'ffmpeg'), '-v','error','-y','-f','f32le','-ar',str(RATE),'-ac','1',
                        '-i','-','-c:a','libmp3lame','-b:a','128k',str(out/f'{int(start)}-{name}.mp3')],
                        input=matched.astype('<f4').tobytes(), check=True)
    (out/f'{int(start)}-metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    return metrics

def page(job):
    cards = []
    for file in sorted((job/'comparison').glob('*-metrics.json')):
        data = read_json(file); start = data['source_start_seconds']; stamp = f'{int(start)//60:02d}:{int(start)%60:02d}'
        items = ''.join(f'<label>{label}<audio controls preload="metadata" src="comparison/{int(start)}-{name}.mp3"></audio></label>'
                        for name,label in [('source','Original voice channel'),('previous','Previous finished video'),('new','Revised finished video')])
        cards.append(f'<section><h2>Source {stamp} · {data["duration_seconds"]:.0f} seconds</h2>{items}</section>')
    plan=read_json(job/'plan.json'); title = html.escape(plan['title'])
    evidence=plan.get('evidence',{})
    proposed_start=evidence.get('start',{}).get('time')
    proposed_end=evidence.get('end',{}).get('time')
    passage=evidence.get('passage',{}).get('verse_matching',{}).get('passage',plan.get('passage',''))
    detection=''
    if (job/'source.mp4').is_file() and proposed_start is not None and proposed_end is not None:
        def stamp(value):
            return f'{int(value)//3600:02d}:{int(value)//60%60:02d}:{int(value)%60:02d}'
        detection=f'''<section><h2>Detected reading and ending</h2><p>{html.escape(passage)} · suggested start {stamp(proposed_start)} · suggested end {stamp(proposed_end)}</p>
<p>Your saved manual cut is retained in the finished video. The buttons below play the source around the newly detected edges.</p>
<video id="source-player" controls preload="metadata" src="source.mp4" style="width:100%;max-height:450px"></video>
<button data-time="{max(0,proposed_start-4):.3f}">Check reading start</button> <button data-time="{max(0,proposed_end-12):.3f}">Check closing words</button></section>'''
    document = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Listen and compare — {title}</title><style>body{{font:17px system-ui;background:#101e2b;color:#edf3f7;max-width:850px;margin:40px auto;padding:0 22px}}p{{line-height:1.6;color:#bccbd8}}section{{padding:22px;background:#192938;margin:20px 0;border-radius:12px}}label{{display:block;margin:18px 0}}audio{{display:block;width:100%;margin-top:8px}}a{{color:#ffb455}}h2{{font-size:21px}}</style>
<h1>Listen and compare</h1><p>{title}</p><p>The main voice is matched to the same level and the clips are aligned in time. Compare quiet words, room noise, audience sounds and word endings. Please use the same listening volume for all three.</p>
{''.join(cards)}{detection}<p><a href="finished.mp4">Open revised full video</a> · <a href="previous-output/finished.mp4">Open previous full video</a> · <a href="/">Return to the app</a></p>
<script>document.querySelectorAll('audio').forEach(a=>a.addEventListener('play',()=>document.querySelectorAll('audio').forEach(b=>{{if(b!==a)b.pause()}})));document.querySelectorAll('button[data-time]').forEach(b=>b.addEventListener('click',()=>{{const v=document.querySelector('#source-player');v.currentTime=Number(b.dataset.time);v.play()}}))</script></html>'''
    (job/'audio-review.html').write_text(document,encoding='utf-8')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job_id'); parser.add_argument('--start',type=float,required=True)
    parser.add_argument('--seconds',type=float,default=60)
    args = parser.parse_args(); job = (JOBS/args.job_id).resolve()
    if job.parent != JOBS.resolve() or not 5<=args.seconds<=150: parser.error('Choose a job and a sample of 5–150 seconds.')
    print(json.dumps(comparison(job,args.start,args.seconds),indent=2)); page(job)
