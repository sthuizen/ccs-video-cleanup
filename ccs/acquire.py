import hashlib, re, os, sys, json, subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .common import ROOT, BIN, JOBS, YTDLP, command, read_json, write_json, status

def job_for(source, persist=True):
    parsed=urlparse(source)
    if parsed.scheme in ('https','http'):
        if parsed.hostname not in ('www.youtube.com','youtube.com','youtu.be','m.youtube.com'):
            raise ValueError('Please use a YouTube URL, or a local video file through the command line.')
        vid=(parsed.path.strip('/') if parsed.hostname=='youtu.be' else parse_qs(parsed.query).get('v',[None])[0])
        if not vid and parsed.path.startswith(('/live/','/shorts/','/embed/')): vid=parsed.path.split('/')[2]
        if not vid or not re.fullmatch(r'[\w-]{11}',vid): raise ValueError('Cannot identify the YouTube video.')
        canonical='https://www.youtube.com/watch?v='+vid
    else:
        path=Path(source).expanduser().resolve()
        if not path.is_file(): raise ValueError('Video file does not exist.')
        vid='local-'+hashlib.sha256((str(path)+str(path.stat().st_mtime_ns)).encode()).hexdigest()[:12]
        canonical=str(path)
    job=JOBS/vid
    if persist:
        job.mkdir(parents=True,exist_ok=True)
        write_json(job/'input.json',{'source':canonical})
    return job,canonical

def resolution(value):
    if value in (None, ''): return None
    if isinstance(value, bool): raise ValueError('Invalid resolution')
    try: height=int(value)
    except (ValueError, TypeError): raise ValueError('Invalid resolution')
    if str(height)!=str(value) or not 144<=height<=8640: raise ValueError('Invalid resolution')
    return height

def downloader():
    launcher=os.environ.get('CCS_WINDOWS_LAUNCHER')
    return [sys.executable,launcher,'--module','yt_dlp'] if launcher else [YTDLP]

def available_resolutions(source, cookies=None):
    job,source=job_for(source,persist=False)
    if not source.startswith('https:'): raise ValueError('Paste a YouTube URL.')
    cached=job/'source.info.json'
    if cached.exists() and (job/'source.mp4').exists():
        info=read_json(cached)
        cached_height=info.get('height')
    else:
        args=downloader()+['--no-playlist','--skip-download','--dump-single-json','--js-runtimes','deno']
        if cookies: args+=['--cookies-from-browser',cookies]
        args+=[source]
        result=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=120)
        if result.returncode: raise ValueError('Could not check video resolutions. Check the URL and Download access, then try again.')
        info=json.loads(result.stdout);cached_height=None
    heights=sorted({int(f['height']) for f in info.get('formats',[]) if f.get('height') and f.get('vcodec') not in (None,'none') and not f.get('has_drm')},reverse=True)
    if cached_height: heights=sorted(set([int(cached_height)]+[h for h in heights if h<=cached_height]),reverse=True)
    if not heights: raise ValueError('No downloadable video resolutions were found.')
    return dict(resolutions=heights,cached=bool(cached_height),title=info.get('title',''))

def acquire(job, source, cookies=None, video_height=None):
    video_height=resolution(video_height)
    if not source.startswith('https:'):
        write_json(job/'source-path.json',{'path':source})
        if not (job/'source.info.json').exists(): write_json(job/'source.info.json',{'title':Path(source).stem})
        return Path(source)
    target=job/'source.mp4'
    if target.exists(): return target
    status(job,'Downloading','Downloading original video, metadata and any English captions')
    # Prefer the highest allowed resolution, then video/audio bitrate.
    launcher=os.environ.get('CCS_WINDOWS_LAUNCHER')
    prefix=[sys.executable,launcher,'--module','yt_dlp'] if launcher else [YTDLP]
    args=prefix+['--no-playlist','--newline','--sleep-requests','1','--js-runtimes','deno','--write-info-json','--write-subs','--write-auto-subs','--sub-langs','en.*','--sub-format','json3','--merge-output-format','mp4','--remux-video','mp4','-f',(f'bv[height<={video_height}]+ba/b[height<={video_height}]' if video_height else 'bv+ba/b'),'-S','height,vbr,abr','--format-sort-force','-o',job/'source.%(ext)s']
    if cookies: args.extend(['--cookies-from-browser',cookies])
    # Caption failure must not prevent the media download (YouTube often rate-limits captions).
    try: command(args+[source],job,'download')
    except RuntimeError as exc:
        if not target.exists():
            detail=str(exc)
            # Only retry without captions when captions actually caused the failure.
            # Retrying a blocked video immediately adds requests without fixing access.
            caption_error=re.search(r'ERROR:.*(?:subtitles|captions)',detail,re.I)
            if caption_error:
                retry=[x for x in args if x not in ('--write-subs','--write-auto-subs')]
                command(retry+[source],job,'download-retry')
            elif "confirm you’re not a bot" in detail or "confirm you're not a bot" in detail:
                raise RuntimeError('YouTube requires sign-in verification. Set Download access to firefox, open this video in your signed-in Firefox session, then try again. If Firefox access is already selected, wait before retrying.') from exc
            elif '429' in detail:
                raise RuntimeError('YouTube temporarily limited download requests (HTTP 429). Keep Firefox download access selected and wait before retrying.') from exc
            else:
                raise
    return target

def video_path(job):
    p=job/'source-path.json'
    return Path(read_json(p)['path']) if p.exists() else job/'source.mp4'
