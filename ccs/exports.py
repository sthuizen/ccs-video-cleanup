"""Upload-ready exports from the same reviewed, conditioned PCM master."""
import json
import re
from .common import BIN, command, probe, status, read_json, write_json, exclusive
from .acquire import video_path
from .audio import prepare
from .audio_review import identity, selected_profile
from .render import render, validate, mono_filter

def destinations(value=None):
    value=['youtube'] if value is None else value
    if not isinstance(value,list) or not value or any(v not in ('youtube','spotify') for v in value):
        raise ValueError('Choose YouTube video, Spotify podcast audio, or both.')
    return [v for v in ('youtube','spotify') if v in value]

def podcast_ready(job,plan):
    marker=job/'podcast-validation.json'
    if not plan or not (job/'podcast.mp3').is_file() or not marker.exists():return False
    saved=read_json(marker)
    return (saved.get('full_decode')=='passed' and saved.get('selection')==identity(job,plan)
            and saved.get('audio_profile')==selected_profile(job,plan)
            and saved.get('metadata')=={k:plan[k] for k in ('title','date','passage')})

@exclusive
def podcast(job,plan):
    validate(plan)
    if plan.get('issues') and not plan.get('confirmed'):raise ValueError('Confirm the clip details before exporting.')
    start=float(plan['start']);duration=float(plan['end'])-start
    source=video_path(job);profile=selected_profile(job,plan)
    mono=mono_filter(job,source,start,duration)
    audio,norm=prepare(job,source,start,duration,mono,profile)
    temporary=job/'podcast.partial.mp3'
    status(job,'Creating podcast','Encoding Spotify-compatible MP3 with your chosen audio settings',total_seconds=duration,log_file='podcast-encode.log')
    command([BIN/'ffmpeg','-y','-i',audio,'-af',norm,'-t',str(duration),'-vn',
             '-c:a','libmp3lame','-b:a','128k','-ar','48000','-ac','1','-id3v2_version','3',
             '-metadata',f"title={plan['title']}",'-metadata','artist=Christ Church Southampton',
             '-metadata',f"date={plan['date']}",temporary],job,'podcast-encode')
    checked=probe(temporary);stream=checked['streams'][0];actual=float(checked['format']['duration'])
    if len(checked['streams'])!=1 or stream['codec_name']!='mp3' or stream['channels']!=1 or int(stream['sample_rate'])!=48000 or abs(actual-duration)>.5:
        raise RuntimeError('Podcast format or duration validation failed.')
    status(job,'Checking podcast','Decoding the full podcast and checking audio peaks',total_seconds=duration,log_file='podcast-check.log')
    command([BIN/'ffmpeg','-v','info','-xerror','-i',temporary,'-af','loudnorm=I=-20:TP=-2:LRA=50:print_format=json','-f','null','-'],job,'podcast-check')
    measurements=re.findall(r'\{\s*"input_i".*?\}',(job/'podcast-check.log').read_text(encoding='utf-8',errors='replace'),re.S)
    if not measurements:raise RuntimeError('Podcast audio measurement is missing.')
    measured=json.loads(measurements[-1])
    if float(measured['input_tp'])>-.5:raise RuntimeError('Podcast exceeds the safe audio peak limit.')
    temporary.replace(job/'podcast.mp3')
    write_json(job/'podcast-validation.json',dict(full_decode='passed',selection=identity(job,plan),audio_profile=profile,
        metadata={k:plan[k] for k in ('title','date','passage')},duration=actual,expected_duration=duration,
        codec='mp3',channels=1,sample_rate=48000,bitrate=128000,audio_lufs=float(measured['input_i']),
        audio_true_peak_db=float(measured['input_tp']),audio_master_source='Conditioned PCM with the chosen normalization; no video intro silence'))
    return job/'podcast.mp3'

@exclusive
def create(job,outputs=None,stabilize=True):
    outputs=destinations(outputs);plan=read_json(job/'plan.json');validate(plan)
    write_json(job/'export-settings.json',{'outputs':outputs})
    if 'youtube' in outputs:render(job,stabilize,finish=False)
    if 'spotify' in outputs:podcast(job,plan)
    status(job,'Finished','Your chosen exports are ready: '+', '.join(outputs))
