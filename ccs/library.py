"""Explicit, short-lived confirmations for moving saved jobs to desktop Trash."""
import os
import secrets
import subprocess
import threading
import time
from pathlib import Path
from .common import JOBS, busy, exclusive, read_json

_tickets={}
_guard=threading.Lock()

def job_path(jid):
    if not isinstance(jid,str) or not jid or Path(jid).name!=jid or jid in ('.','..'):
        raise ValueError('Invalid service')
    path=JOBS/jid
    if path.is_symlink() or not path.is_dir() or path.resolve().parent!=JOBS.resolve():
        raise ValueError('Saved service not found')
    return path

def finished(path):
    checked=path/'validation.json'
    podcast=path/'podcast-validation.json'
    return ((path/'finished.mp4').is_file() and checked.exists() and read_json(checked).get('full_decode')=='passed') or ((path/'podcast.mp3').is_file() and podcast.exists() and read_json(podcast).get('full_decode')=='passed')

def inventory(path):
    entries=[]
    for root,dirs,files in os.walk(path,followlinks=False):
        for name in dirs+files:
            child=Path(root)/name;s=child.lstat()
            entries.append((str(child.relative_to(path)),s.st_size,s.st_mtime_ns,s.st_ino))
    return sorted(entries)

def preview(jid=None,all_services=False):
    if busy():raise ValueError('Wait for processing to finish before deleting saved services.')
    paths=sorted((p for p in JOBS.iterdir() if p.is_dir() and not p.is_symlink()),key=lambda p:p.name) if all_services else [job_path(jid)]
    if not paths:raise ValueError('There are no saved services to delete.')
    if not all_services and not finished(paths[0]):raise ValueError('Only finished services can be deleted individually.')
    saved=[]
    for path in paths:
        job_path(path.name)
        plan=read_json(path/'plan.json') if (path/'plan.json').exists() else {}
        entries=inventory(path)
        saved.append(dict(id=path.name,title=plan.get('title') or path.name,date=plan.get('date'),bytes=sum(e[1] for e in entries),snapshot=entries))
    token=secrets.token_urlsafe(32);phrase='DELETE ALL' if all_services else 'DELETE'
    with _guard:
        for old in list(_tickets):
            if _tickets[old]['expires']<time.monotonic():del _tickets[old]
        _tickets[token]=dict(expires=time.monotonic()+300,jobs=saved,phrase=phrase,all=all_services)
    return dict(token=token,phrase=phrase,jobs=[{k:v for k,v in j.items() if k!='snapshot'} for j in saved],bytes=sum(j['bytes'] for j in saved))

def trash(path):
    if os.name!='nt':
        subprocess.run(['gio','trash',str(path)],check=True,capture_output=True,text=True)
    else:
        import ctypes
        from ctypes import wintypes
        class Operation(ctypes.Structure):
            _fields_=[('hwnd',wintypes.HWND),('wFunc',wintypes.UINT),('pFrom',wintypes.LPCWSTR),('pTo',wintypes.LPCWSTR),('fFlags',wintypes.WORD),('aborted',wintypes.BOOL),('maps',ctypes.c_void_p),('title',wintypes.LPCWSTR)]
        operation=Operation(None,3,str(path)+'\0\0',None,0x40|0x10|0x400,False,None,None)
        result=ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
        if result or operation.aborted:raise ValueError('Could not move the service to the Recycle Bin.')

@exclusive
def delete(token,phrase,acknowledged):
    with _guard:
        ticket=_tickets.get(token)
        if not ticket or ticket['expires']<time.monotonic():raise ValueError('Confirmation expired. Review the deletion again.')
        if acknowledged is not True or phrase!=ticket['phrase']:raise ValueError('Complete both deletion checks.')
        if ticket['all']:
            current=sorted(p.name for p in JOBS.iterdir() if p.is_dir() and not p.is_symlink())
            if current!=[j['id'] for j in ticket['jobs']]:raise ValueError('The saved services changed. Review the deletion again.')
        paths=[]
        for job in ticket['jobs']:
            path=job_path(job['id'])
            if inventory(path)!=job['snapshot']:raise ValueError('A service changed. Review the deletion again.')
            paths.append(path)
        del _tickets[token]
        deleted=[]
        for path in paths:
            try:trash(path)
            except Exception as exc:
                raise ValueError(f'Could not move {path.name} to Trash. {len(deleted)} service(s) moved; refresh the list and try again.') from exc
            deleted.append(path.name)
    return dict(deleted=deleted)
