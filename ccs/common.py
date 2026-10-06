from pathlib import Path
import json, os, subprocess, time
ROOT = Path(__file__).resolve().parent.parent
BIN = Path(os.environ.get('CCS_BIN_DIR', str(ROOT / '.tools/bin')))
DATA_ROOT = Path(os.environ.get('CCS_DATA_DIR', str(ROOT)))
JOBS = DATA_ROOT / 'jobs'
LOCK = DATA_ROOT / '.tools/pipeline.lock'
MODELS = Path(os.environ.get('CCS_MODEL_DIR', str(ROOT / '.models/whisper')))
LOGO = Path(os.environ.get('CCS_LOGO', str(ROOT / 'assets/church-logo.png')))
YTDLP = Path(os.environ.get('CCS_YTDLP', str(ROOT / '.venv/bin/yt-dlp')))
os.environ['PATH'] = str(BIN) + os.pathsep + os.environ.get('PATH', '')
os.environ.setdefault('OMP_NUM_THREADS', '6')
def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False))
    tmp.replace(path)
def read_json(path): return json.loads(Path(path).read_text())
def status(job, stage, detail='', **progress):
    print(f'{stage}: {detail}', flush=True)
    now=time.time(); path=job/'status.json'
    previous=read_json(path) if path.exists() else {}
    history=previous.get('steps',[])
    if stage=='Queued': previous={}; history=[]
    if previous.get('stage')!=stage:
        if previous.get('stage') and previous['stage'] not in ('Finished','Error','Needs information'):
            history=history+[{'stage':previous['stage'], 'elapsed_seconds':max(0,now-previous.get('started_at',previous.get('updated',now))), 'completed':stage!='Error'}]
        record={'stage':stage,'started_at':now,'run_started_at':previous.get('run_started_at',now),'steps':history}
    else:
        record=previous
        record.setdefault('started_at',previous.get('updated',now))
    record.update(detail=detail,updated=now,**progress)
    write_json(path,record)
def command(args, job, name):
    path=job/'status.json'
    if path.exists():
        record=read_json(path); record.update(log_file=name+'.log',log_started_at=time.time())
        write_json(path,record)
    with (job/(name+'.log')).open('w') as log:
        result = subprocess.run([str(x) for x in args], stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        tail=(job/(name+'.log')).read_text(errors='replace')[-3000:]
        raise RuntimeError(f'{name} failed ({result.returncode}): {tail}')
def probe(path):
    return json.loads(subprocess.check_output([str(BIN/'ffprobe'),'-v','error','-show_streams','-show_chapters','-show_format','-of','json',str(path)]))
def timestamp(t):
    t=round(float(t)); return f'{t//3600:02d}:{t//60%60:02d}:{t%60:02d}'
def seconds(value):
    if isinstance(value,(int,float)): return float(value)
    parts=str(value).strip().split(':')
    if len(parts)>3: raise ValueError('Use seconds or HH:MM:SS')
    return sum(float(p)*60**i for i,p in enumerate(reversed(parts)))

# A shared process lock prevents a desktop job and CLI job from writing the same media.
import fcntl, functools, threading
_lock_state=threading.local()
def exclusive(fn):
    @functools.wraps(fn)
    def wrapped(*args,**kwargs):
        if getattr(_lock_state,'depth',0): return fn(*args,**kwargs)
        lockpath=LOCK; lockpath.parent.mkdir(parents=True,exist_ok=True)
        with lockpath.open('a') as handle:
            try: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise ValueError('Another video is processing. Wait for it to finish.')
            _lock_state.depth=1
            try: return fn(*args,**kwargs)
            finally:
                _lock_state.depth=0; fcntl.flock(handle,fcntl.LOCK_UN)
    return wrapped

def busy():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open('a') as handle:
        try: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return True
        fcntl.flock(handle,fcntl.LOCK_UN)
        return False
