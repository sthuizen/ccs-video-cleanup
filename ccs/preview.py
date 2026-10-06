"""A lightweight browser copy; the downloadable master is never modified."""
from .common import BIN, command, probe, read_json, write_json, status, exclusive

def signature(job):
    source=job/'finished.mp4'
    return {'source_size':source.stat().st_size,'source_modified':source.stat().st_mtime_ns,'version':1}

def ready(job):
    source=job/'finished.mp4'; settings=job/'preview-settings.json'
    return source.exists() and (job/'preview.mp4').exists() and settings.exists() and read_json(settings)==signature(job)

@exclusive
def prepare(job):
    if ready(job): return job/'preview.mp4'
    source=job/'finished.mp4'; info=probe(source)
    duration=float(info['format']['duration'])
    video=next(s for s in info['streams'] if s['codec_type']=='video')
    ratio=video.get('avg_frame_rate','30/1').split('/');fps=float(ratio[0])/float(ratio[1])
    vf="scale=w='min(1280,iw)':h='min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,format=yuv420p"
    if fps>30: vf+=',fps=30'
    settings=signature(job)
    status(job,'Preparing preview','Creating a lighter browser playback copy; full-quality download is ready',total_seconds=duration)
    temporary=job/'preview.partial.mp4'
    command([BIN/'ffmpeg','-y','-i',source,'-map','0:v:0','-map','0:a:0','-map_metadata','0','-vf',vf,
             '-c:v','libx264','-profile:v','baseline','-level:v','3.1','-bf','0','-preset','veryfast','-crf','24',
             '-maxrate','2M','-bufsize','4M','-threads','6','-c:a','copy','-movflags','+faststart',temporary],job,'preview-encode')
    check=probe(temporary)
    v=next(s for s in check['streams'] if s['codec_type']=='video')
    a=next(s for s in check['streams'] if s['codec_type']=='audio')
    if v['width']>1280 or v['height']>720 or a['channels']!=1 or abs(float(check['format']['duration'])-duration)>.1:
        raise RuntimeError('Browser preview validation failed')
    if signature(job)!=settings: raise RuntimeError('The finished video changed while preparing its preview')
    temporary.replace(job/'preview.mp4');write_json(job/'preview-settings.json',settings)
    write_json(job/'preview-validation.json',{'duration':float(check['format']['duration']),'width':v['width'],'height':v['height'],
               'profile':v.get('profile'),'audio':'copied without re-encoding','audio_channels':a['channels']})
    status(job,'Finished',str(source))
    return job/'preview.mp4'
