"""Optional visual jitter measurements on static-background patches."""
import subprocess
import numpy as np
from .common import BIN, probe, write_json, process_options

def motion(path,offset,seconds=8):
    import cv2
    v=next(x for x in probe(path)['streams'] if x['codec_type']=='video')
    # Ignore the preacher, leaves and projection; use the upper-left wall.
    raw=subprocess.check_output([str(BIN/'ffmpeg'),'-v','error','-ss',str(offset),'-t',str(seconds),'-i',str(path),'-an','-vf','fps=15,scale=640:-2,crop=180:120:70:15,format=gray','-f','rawvideo','-'], **process_options())
    frames=np.frombuffer(raw,np.uint8).reshape(-1,120,180)
    points=cv2.goodFeaturesToTrack(frames[0],maxCorners=100,qualityLevel=.001,minDistance=5)
    if points is None or len(points)<8:return None
    shifts=[]
    previous=frames[0]
    for frame in frames[1:]:
        points=cv2.goodFeaturesToTrack(previous,maxCorners=100,qualityLevel=.001,minDistance=5)
        if points is None:continue
        after,ok,error=cv2.calcOpticalFlowPyrLK(previous,frame,points,None,winSize=(21,21),maxLevel=2)
        valid=ok[:,0].astype(bool)
        if valid.sum()<8:continue
        delta=(after-points)[valid,0,:]
        shifts.append(np.median(delta,axis=0));previous=frame
    if len(shifts)<20:return None
    from scipy.ndimage import uniform_filter1d
    shifts=np.array(shifts);fast=shifts-uniform_filter1d(shifts,size=15,axis=0,mode='nearest')
    return {'rms_pixels_at_640':float(np.sqrt(np.mean(np.sum(fast**2,axis=1)))),'pairs':len(shifts)}

def compare(job,video,start,duration):
    measurements=[]
    for offset in (min(300,duration/3),min(1200,duration*2/3)):
        before=motion(video,start+offset);after=motion(job/'sermon.mp4',offset)
        if before and after: measurements.append({'offset':offset,'source':before,'output':after})
    write_json(job/'jitter-check.json',{'method':'Static upper-left-wall optical flow, high-frequency motion; sampled check, not whole-video proof','samples':measurements})
    return measurements
