"""Read bounded process logs and expose honest step progress and estimates."""
import re, time
from .common import read_json

TERMINAL={'Finished','Error','Needs information'}

def tail(path):
    if not path.exists(): return ''
    with path.open('rb') as handle:
        handle.seek(max(0,path.stat().st_size-24000))
        return handle.read().decode(errors='replace')

def snapshot(job, record, plan=None, now=None):
    result=dict(record); now=time.time() if now is None else now
    stage=result.get('stage','Downloaded')
    started=result.get('started_at',result.get('updated',now))
    terminal=stage in TERMINAL
    elapsed=max(0,(result.get('updated',now) if terminal else now)-started)
    percent=result.get('percent'); eta=None; scope=result.get('progress_scope','This step')
    log_name=result.get('log_file')
    # Support jobs begun by older versions, without treating unrelated logs as active.
    if not log_name:
        log_name={'Downloading':'download.log','Rendering':'render.log','Measuring camera movement':'stabilize-measure.log','Cleaning audio':'loudness-measure.log'}.get(stage)
    log=tail(job/log_name) if log_name else ''
    total=result.get('total_seconds')
    if total is None and plan and stage in ('Rendering','Measuring camera movement','Cleaning audio'):
        total=float(plan['end'])-float(plan['start'])
    if stage=='Downloading':
        matches=re.findall(r'\[download\]\s+([\d.]+)%.*?(?:ETA\s+(\d+(?::\d+){1,2})|$)',log,re.M)
        if matches:
            value,remaining=matches[-1];percent=min(99.9,float(value));scope='Current download file'
            if remaining:
                eta=sum(float(p)*60**i for i,p in enumerate(reversed(remaining.split(':'))))
    elif total and log:
        times=re.findall(r'time=(\d+):(\d+):(\d+\.\d+)',log)
        if times:
            h,m,s=times[-1];processed=int(h)*3600+int(m)*60+float(s)
            percent=min(99.9,max(0,processed/total*100))
            speeds=re.findall(r'speed=\s*([\d.]+)x',log)
            if speeds and float(speeds[-1])>0: eta=max(0,total-processed)/float(speeds[-1])
    if percent is not None:
        percent=min(100,max(0,float(percent)))
        if eta is None and stage!='Downloading' and 2<=percent<100 and elapsed>=3:
            eta=elapsed*(100-percent)/percent
    if terminal:
        percent=100 if stage=='Finished' else None;eta=None
    result.update(elapsed_seconds=round(elapsed),percent=percent,eta_seconds=round(eta) if eta is not None else None,
                  progress_scope=scope,active=not terminal,
                  total_elapsed_seconds=round(sum(x.get('elapsed_seconds',0) for x in result.get('steps',[]))+elapsed))
    return result
