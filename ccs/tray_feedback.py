"""Shared desktop status: active work wins; otherwise use explicit selection."""
def duration(seconds):
    seconds=max(0,round(seconds or 0))
    return f'{seconds//3600}h {seconds%3600//60}m' if seconds>=3600 else f'{seconds//60}m {seconds%60}s' if seconds>=60 else f'{seconds}s'

def progress_feedback(rows,selected=None):
    current=next((r for r in rows if r.get('status',{}).get('active')),next((r for r in rows if r.get('id')==selected),None))
    if not current:return dict(title='No service selected',task='Ready',detail='Add a service URL or choose a prepared service in the app',timing='',badge='')
    status=current['status'];stage=status.get('stage','Ready');active=status.get('active',False)
    percent=status.get('percent')
    amount=f'{int(percent)}%' if percent is not None else 'Working' if active else ''
    scope=' · current file' if stage=='Downloading' and percent is not None else ''
    task=stage+(f' · {amount}{scope}' if amount else '')
    badge=amount if active else 'Review' if stage=='Needs information' else 'Listen' if stage=='Choose audio' else ''
    detail=status.get('detail','') if active else {'Needs information':'Check clip boundaries, date and title in the app','Choose audio':'Compare the samples and choose audio in the app','Error':'Open the app to view the error and retry','Finished':'Selected exports ready'}.get(stage,'Ready')
    timing=f'{duration(status.get("elapsed_seconds"))} elapsed' if active else 'Waiting for your input' if stage in ('Needs information','Choose audio') else ''
    if active:timing+=' · '+(f'About {duration(status["eta_seconds"])} remaining' if status.get('eta_seconds') is not None else 'Time remaining: estimating…')
    return dict(title=(current.get('plan') or {}).get('title') or ('Service · '+(current.get('plan') or {})['date'] if (current.get('plan') or {}).get('date') else current['id']),task=task,detail=detail[:100],timing=timing,badge=badge)

