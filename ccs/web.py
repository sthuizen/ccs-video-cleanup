"""Loopback-only desktop interface; one media job at a time."""
import json, mimetypes, threading, urllib.parse, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from .common import ROOT, JOBS, read_json, write_json, status, seconds, busy
from .acquire import job_for, available_resolutions, resolution
from .cli import process
from .progress import snapshot
from .preview import ready as preview_ready
from .render import render, validate
from . import audio_review, library
from . import exports
from .common import exclusive
LOCK=threading.Lock()
SELECTED=None  # Browser selection is session state, never restored from saved jobs.

def background(job, fn):
    if not LOCK.acquire(blocking=False): raise ValueError('Another video is processing. Wait for it to finish first.')
    def work():
        try: fn()
        except Exception as exc: status(job,'Error',str(exc))
        finally: LOCK.release()
    threading.Thread(target=work,daemon=True).start()

def output_readiness(job, plan, stage):
    """Only offer media that has completed processing for the current review."""
    processed=finished=False
    if not plan:return processed,finished
    media=job/'media-settings.json'
    if stage!='Rendering' and media.exists() and (job/'sermon.mp4').exists():
        saved=read_json(media)
        if plan.get('start') is not None and plan.get('end') is not None:
            processed=saved.get('start')==float(plan['start']) and saved.get('duration')==float(plan['end'])-float(plan['start'])
    validation=job/'validation.json'
    if stage in ('Finished','Preparing preview','Preparing audio tests','Choose audio') and validation.exists() and (job/'finished.mp4').exists():
        checked=read_json(validation)
        matches=all(checked.get('plan',{}).get(k)==plan.get(k) for k in ('start','end','title','date','passage','video_height'))
        finished=matches and checked.get('full_decode')=='passed' and checked.get('audio_channels')==1
    choice=job/'audio-choice.json'
    if choice.exists() and read_json(choice).get('selection')==audio_review.identity(job,plan):
        expected=audio_review.selected_profile(job,plan)
        processed=processed and read_json(media).get('audio_profile')==expected
        finished=finished and read_json(validation).get('audio_profile')==expected
    return processed,finished

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,data,code=200):
        body=json.dumps(data).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        url=urllib.parse.urlparse(self.path); parts=url.path.strip('/').split('/')
        if url.path=='/api/health':
            import os
            return self.reply({'app':'ccs-video-cleanup','instance':os.environ.get('CCS_APP_ID',''),'version':os.environ.get('CCS_APP_VERSION','local')})
        if url.path=='/api/selection': return self.reply({'id':SELECTED})
        if url.path=='/api/tray':
            from .tray_feedback import progress_feedback
            rows=[]
            for j in JOBS.iterdir():
                if j.is_dir() and (j/'status.json').exists():
                    p=read_json(j/'plan.json') if (j/'plan.json').exists() else None
                    rows.append(dict(id=j.name,plan=p,status=snapshot(j,read_json(j/'status.json'),p)))
            return self.reply(dict(feedback=progress_feedback(rows,SELECTED),busy=busy() or LOCK.locked(),desktop_active=LOCK.locked()))
        if url.path=='/api/jobs':
            result=[]
            for j in sorted(JOBS.glob('*'),key=lambda p:p.stat().st_mtime,reverse=True):
                if j.is_dir():
                    row={'id':j.name,'status':read_json(j/'status.json') if (j/'status.json').exists() else {'stage':'Downloaded'},'plan':read_json(j/'plan.json') if (j/'plan.json').exists() else None,'finished':(j/'finished.mp4').exists(),'processed':(j/'sermon.mp4').exists() and (j/'media-settings.json').exists()}
                    stage=row['status']['stage']
                    row['processed'],row['finished']=output_readiness(j,row['plan'],stage)
                    row['podcast']=exports.podcast_ready(j,row['plan'])
                    row['export_outputs']=read_json(j/'export-settings.json')['outputs'] if (j/'export-settings.json').exists() else ['youtube']
                    row['outputs_ready']=all(row['finished'] if v=='youtube' else row['podcast'] for v in row['export_outputs'])
                    row['preview']=row['finished'] and preview_ready(j)
                    row['audio_review']=read_json(j/'audio-trials.json') if (j/'audio-trials.json').exists() else None
                    row['audio_review_current']=bool(row['audio_review'] and row['plan'] and row['audio_review']['selection']==audio_review.identity(j,row['plan']))
                    row['audio_choice']=read_json(j/'audio-choice.json') if (j/'audio-choice.json').exists() else None
                    row['audio_busy']=LOCK.locked() or busy()
                    row['can_delete']=library.finished(j) and not row['audio_busy']
                    row['preview_version']=(j/'finished.mp4').stat().st_mtime_ns if row['preview'] else None
                    row['status']=snapshot(j,row['status'],row['plan'])
                    result.append(row)
            return self.reply(result)
        if url.path=='/': path=ROOT/'ccs/index.html'
        elif url.path=='/library.js': path=ROOT/'ccs/library.js'
        elif url.path=='/audio-review.js': path=ROOT/'ccs/audio-review.js'
        elif url.path=='/logo.png':
            from .common import LOGO
            path=LOGO
        elif len(parts)>=3 and parts[0]=='files':
            path=(JOBS/'/'.join(parts[1:])).resolve()
            if not path.is_relative_to(JOBS.resolve()): return self.reply({'error':'Invalid path'},403)
        else: return self.reply({'error':'Not found'},404)
        if not path.is_file(): return self.reply({'error':'Not found'},404)
        size=path.stat().st_size; begin=0; end=size-1; code=200
        range_header=self.headers.get('Range','')
        if range_header.startswith('bytes='):
            try:
                lo,hi=range_header[6:].split('-',1)
                if lo: begin=int(lo); end=min(int(hi),end) if hi else end
                else: begin=max(0,size-int(hi))
                if not 0<=begin<=end<size: raise ValueError()
                code=206
            except ValueError: return self.reply({'error':'Invalid range'},416)
        self.send_response(code)
        self.send_header('Content-Type',mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(end-begin+1)); self.send_header('Accept-Ranges','bytes')
        if url.path in ('/','/audio-review.js','/library.js'): self.send_header('Cache-Control','no-store')
        if code==206: self.send_header('Content-Range',f'bytes {begin}-{end}/{size}')
        self.end_headers()
        try:
            with path.open('rb') as f:
                f.seek(begin); remaining=end-begin+1
                while remaining>0:
                    chunk=f.read(min(1024*1024,remaining))
                    if not chunk: break
                    self.wfile.write(chunk); remaining-=len(chunk)
        except (BrokenPipeError,ConnectionResetError): pass
    def do_POST(self):
        global SELECTED
        # JSON + custom header disallows cross-origin form submissions to this local app.
        if self.headers.get('X-CCS-Request')!='1' or self.headers.get('Content-Type')!='application/json': return self.reply({'error':'Invalid request'},403)
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>16384: raise ValueError('Request too large')
            data=json.loads(self.rfile.read(n))
            if self.path=='/api/selection':
                jid=data.get('id')
                if jid is not None and (not isinstance(jid,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',jid) or not (JOBS/jid).is_dir()):
                    raise ValueError('Invalid service selection')
                SELECTED=jid
                return self.reply({'id':SELECTED})
            if self.path=='/api/delete-preview':
                if LOCK.locked(): raise ValueError('Wait for processing to finish before deleting saved services.')
                return self.reply(library.preview(data.get('id'),data.get('all') is True))
            if self.path=='/api/delete':
                if not LOCK.acquire(blocking=False): raise ValueError('Wait for processing to finish before deleting saved services.')
                try: result=library.delete(data.get('token'),data.get('phrase'),data.get('acknowledged'))
                finally: LOCK.release()
                return self.reply(result)
            if self.path=='/api/resolutions':
                return self.reply(available_resolutions(data['url'],data.get('cookies')))
            if self.path=='/api/shutdown':
                import os
                if not os.environ.get('CCS_WINDOWS_LAUNCHER') or data.get('instance')!=os.environ.get('CCS_APP_ID'): raise ValueError('Invalid application instance.')
                if (busy() or LOCK.locked()) and not (data.get('force') is True and LOCK.locked()): raise ValueError('Finish the current processing job before closing the app.')
                self.reply({'stopping':True})
                threading.Thread(target=self.server.shutdown,daemon=True).start()
                return
            if self.path=='/api/start':
                if busy() or LOCK.locked(): raise ValueError('Another video is processing.')
                source=data['url']; job,canonical=job_for(source)
                if not canonical.startswith('https:'): raise ValueError('Paste a YouTube URL.')
                height=resolution(data.get('video_height'))
                status(job,'Queued','Preparing this service')
                background(job,lambda:prepare_for_listening(job,canonical,data.get('cookies'),height))
            elif self.path in ('/api/render','/api/audio-tests'):
                jid=data['id']; job=(JOBS/jid).resolve()
                if job.parent!=JOBS.resolve(): raise ValueError('Invalid job')
                plan=read_json(job/'plan.json')
                for k in ('start','end','title','passage','date'):
                    plan[k]=seconds(data[k]) if k in ('start','end') else data[k].strip()
                if self.path=='/api/render':
                    validate(plan)
                    data['outputs']=exports.destinations(data.get('outputs'))
                elif not 0<=float(plan['start'])<float(plan['end'])<=float(plan['duration']): raise ValueError('Choose cut points inside the source video.')
                plan['confirmed']=self.path=='/api/render'
                if busy() or LOCK.locked(): raise ValueError('Another video is processing.')
                if self.path=='/api/render':
                    audio_review.tested_choice(job,plan,data.get('audio_revision'),data.get('audio_trial'))
                    # Choice is validated under the same cross-process lock as rendering.
                    background(job,lambda:render_choice(job,plan,data))
                else:
                    sample_times=data.get('samples'); custom=data.get('parameters')
                    if sample_times is not None: audio_review.validate_samples(plan,sample_times)
                    if custom is not None: audio_review.parameters(custom)
                    background(job,lambda:test_audio(job,plan,sample_times,custom))
            else: return self.reply({'error':'Not found'},404)
            self.reply({'id':job.name})
        except (Exception,) as exc: self.reply({'error':str(exc)},400)


@exclusive
def test_audio(job, plan, samples=None, custom=None):
    status(job,'Preparing audio tests','Finding quiet and louder speech; the full video waits for your choice')
    audio_review.create(job,plan,samples,custom)
    write_json(job/'plan.json',plan)
    write_json(job/'review.json',{k:plan[k] for k in ('start','end','title','passage','date','confirmed')})
    status(job,'Choose audio','Listen to the audio tests, adjust if needed, then choose a version to create the video')

@exclusive
def prepare_for_listening(job, source, cookies, video_height=None):
    process(source,cookies,analyze_only=True,video_height=video_height)
    plan=read_json(job/'plan.json')
    if plan.get('start') is not None and plan.get('end') is not None:
        test_audio(job,plan)

@exclusive
def render_choice(job,plan,data):
    audio_review.choose(job,plan,data.get('audio_revision'),data.get('audio_trial'))
    write_json(job/'review.json',{k:plan[k] for k in ('start','end','title','passage','date','confirmed')})
    write_json(job/'plan.json',plan)
    exports.create(job,data.get('outputs'),not data.get('no_stabilize',False))

def serve(port=8765):
    JOBS.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Christ Church Video Cleanup: http://127.0.0.1:{port}',flush=True)
    try: server.serve_forever()
    finally: server.server_close()
