"""Loopback-only desktop interface; one media job at a time."""
import json, mimetypes, threading, urllib.parse, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from .common import ROOT, JOBS, read_json, write_json, status, seconds, busy
from .acquire import job_for
from .cli import process
from .progress import snapshot
from .preview import ready as preview_ready
from .render import render, validate
LOCK=threading.Lock()

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
    if stage in ('Finished','Preparing preview') and validation.exists() and (job/'finished.mp4').exists():
        checked=read_json(validation)
        matches=all(checked.get('plan',{}).get(k)==plan.get(k) for k in ('start','end','title','date','passage'))
        finished=matches and checked.get('full_decode')=='passed' and checked.get('audio_channels')==1
    return processed,finished

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,data,code=200):
        body=json.dumps(data).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        url=urllib.parse.urlparse(self.path); parts=url.path.strip('/').split('/')
        if url.path=='/api/jobs':
            result=[]
            for j in sorted(JOBS.glob('*'),key=lambda p:p.stat().st_mtime,reverse=True):
                if j.is_dir():
                    row={'id':j.name,'status':read_json(j/'status.json') if (j/'status.json').exists() else {'stage':'Downloaded'},'plan':read_json(j/'plan.json') if (j/'plan.json').exists() else None,'finished':(j/'finished.mp4').exists(),'processed':(j/'sermon.mp4').exists() and (j/'media-settings.json').exists()}
                    stage=row['status']['stage']
                    row['processed'],row['finished']=output_readiness(j,row['plan'],stage)
                    row['preview']=row['finished'] and preview_ready(j)
                    row['preview_version']=(j/'finished.mp4').stat().st_mtime_ns if row['preview'] else None
                    row['status']=snapshot(j,row['status'],row['plan'])
                    result.append(row)
            return self.reply(result)
        if url.path=='/': path=ROOT/'ccs/index.html'
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
        # JSON + custom header disallows cross-origin form submissions to this local app.
        if self.headers.get('X-CCS-Request')!='1' or self.headers.get('Content-Type')!='application/json': return self.reply({'error':'Invalid request'},403)
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>16384: raise ValueError('Request too large')
            data=json.loads(self.rfile.read(n))
            if self.path=='/api/start':
                if busy() or LOCK.locked(): raise ValueError('Another video is processing.')
                source=data['url']; job,canonical=job_for(source)
                if not canonical.startswith('https:'): raise ValueError('Paste a YouTube URL.')
                status(job,'Queued','Preparing this service')
                background(job,lambda:process(canonical,data.get('cookies')))
            elif self.path=='/api/render':
                jid=data['id']; job=(JOBS/jid).resolve()
                if job.parent!=JOBS.resolve(): raise ValueError('Invalid job')
                plan=read_json(job/'plan.json')
                for k in ('start','end','title','passage','date'):
                    plan[k]=seconds(data[k]) if k in ('start','end') else data[k].strip()
                validate(plan); plan['confirmed']=True
                if busy() or LOCK.locked(): raise ValueError('Another video is processing.')
                write_json(job/'review.json',{k:plan[k] for k in ('start','end','title','passage','date','confirmed')})
                write_json(job/'plan.json',plan)
                background(job,lambda:render(job,not data.get('no_stabilize',False)))
            else: return self.reply({'error':'Not found'},404)
            self.reply({'id':job.name})
        except (Exception,) as exc: self.reply({'error':str(exc)},400)

def serve(port=8765):
    JOBS.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Christ Church Video Cleanup: http://127.0.0.1:{port}',flush=True)
    server.serve_forever()
