from .common import BIN, command, probe, status, read_json, write_json
import subprocess

def scan(job, video, interval=30):
    cache=job/'screen-text.json'
    if cache.exists(): return read_json(cache)
    status(job,'Preparing slide images','Sampling video frames for slide recognition',total_seconds=float(probe(video)['format']['duration']))
    frames=job/'frames'; frames.mkdir(exist_ok=True)
    command([BIN/'ffmpeg','-y','-i',video,'-vf',f'fps=1/{interval},scale=1280:-2','-q:v','3',frames/'%05d.jpg'],job,'frames')
    from rapidocr_onnxruntime import RapidOCR
    engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=2)
    paths=sorted(frames.glob('*.jpg'))
    status(job,'Reading slides',f'Reading {len(paths)} sampled frames',percent=0)
    results=[]
    for i,path in enumerate(paths):
        lines,_=engine(str(path))
        text='\n'.join(item[1] for item in (lines or []) if item[2]>=.75)
        results.append({'time':i*interval+interval/2,'text':text,'frame':path.name})
        if i%3==0 or i+1==len(paths): status(job,'Reading slides',f'Read {i+1} of {len(paths)} frames',percent=(i+1)/len(paths)*100)
    write_json(cache,results)
    return results
