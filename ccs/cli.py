import argparse
from .common import read_json, write_json, status, seconds, exclusive
from .acquire import job_for, acquire, video_path
from .transcribe import transcribe, refine_transcript
from .ocr import scan
from .analyze import analyze
from .render import render

@exclusive
def process(source,cookies=None,analyze_only=False):
    job,source=job_for(source)
    video=acquire(job,source,cookies)
    transcript=transcribe(job,video)
    initial=analyze(job,video,transcript,[])
    checked=refine_transcript(job,video,transcript,initial)
    if checked is not transcript:
        transcript=checked
        initial=analyze(job,video,transcript,[])
    needs_screen=any('title' in issue.lower() or 'passage' in issue.lower() for issue in initial['issues'])
    screens=scan(job,video) if needs_screen else []
    plan=analyze(job,video,transcript,screens)
    if plan['issues'] and not plan.get('confirmed'):
        status(job,'Needs information','; '.join(plan['issues']))
    elif not analyze_only: render(job)
    return job

def main():
    p=argparse.ArgumentParser(description='Prepare a Christ Church Southampton sermon using local tools.')
    sub=p.add_subparsers(dest='action',required=True)
    for action in ('run','analyze'):
        s=sub.add_parser(action); s.add_argument('source'); s.add_argument('--cookies-from-browser')
    s=sub.add_parser('render'); s.add_argument('source'); s.add_argument('--no-stabilize',action='store_true')
    s=sub.add_parser('review'); s.add_argument('source'); s.add_argument('--start'); s.add_argument('--end'); s.add_argument('--title'); s.add_argument('--passage'); s.add_argument('--date'); s.add_argument('--confirm',action='store_true')
    s=sub.add_parser('serve'); s.add_argument('--port',type=int,default=8765)
    a=p.parse_args()
    if a.action=='serve':
        from .web import serve
        serve(a.port); return
    job,source=job_for(a.source)
    try:
        if a.action in ('run','analyze'): process(source,a.cookies_from_browser,a.action=='analyze')
        elif a.action=='review':
            plan=read_json(job/'plan.json'); review={}
            for k in ('start','end','title','passage','date'):
                val=getattr(a,k)
                if val is not None: review[k]=seconds(val) if k in ('start','end') else val
            plan.update(review); plan['confirmed']=a.confirm
            review.update({k:plan[k] for k in ('start','end','title','passage','date')}); review['confirmed']=a.confirm
            from .render import validate
            if a.confirm: validate(plan)
            write_json(job/'review.json',review); write_json(job/'plan.json',plan)
            print(job/'plan.json')
        else: render(job,not a.no_stabilize)
    except Exception as exc:
        status(job,'Error',str(exc)); raise SystemExit(str(exc))
if __name__=='__main__': main()
