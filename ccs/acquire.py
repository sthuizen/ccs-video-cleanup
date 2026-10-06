import hashlib, re
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .common import ROOT, BIN, JOBS, command, read_json, write_json, status

def job_for(source):
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
    job=JOBS/vid; job.mkdir(parents=True,exist_ok=True)
    write_json(job/'input.json',{'source':canonical})
    return job,canonical

def acquire(job, source, cookies=None):
    if not source.startswith('https:'):
        write_json(job/'source-path.json',{'path':source})
        if not (job/'source.info.json').exists(): write_json(job/'source.info.json',{'title':Path(source).stem})
        return Path(source)
    target=job/'source.mp4'
    if target.exists(): return target
    status(job,'Downloading','Downloading original video, metadata and any English captions')
    # Rank by reported video/audio bitrate before resolution or codec preference.
    args=[ROOT/'.venv/bin/yt-dlp','--no-playlist','--newline','--sleep-requests','1','--js-runtimes','deno','--write-info-json','--write-subs','--write-auto-subs','--sub-langs','en.*','--sub-format','json3','--merge-output-format','mp4','--remux-video','mp4','-f','bv+ba/b','-S','vbr,abr','--format-sort-force','-o',job/'source.%(ext)s']
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
