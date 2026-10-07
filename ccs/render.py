import json, re, subprocess, os
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .common import ROOT, BIN, LOGO, command, probe, status, write_json, read_json, exclusive, process_options
from .acquire import video_path
from .audio import FILTER as CLEAN, profile as audio_profile, prepare as prepare_audio
INTRO_SECONDS=5

def validate(plan):
    for k in ('start','end','title','passage','date'):
        if plan.get(k) is None or str(plan[k]).strip()=='': raise ValueError(f'Missing {k}; complete the review fields.')
    if not 0<=float(plan['start'])<float(plan['end'])<=float(plan['duration']): raise ValueError('Cut points must be inside the original video, with end after start.')
    datetime.strptime(plan['date'],'%Y-%m-%d')
    if len(plan['title'])>180 or len(plan['passage'])>100: raise ValueError('Please shorten the title or passage.')

def card(job, plan, width, height):
    img=Image.new('RGB',(width,height),'#101e2b'); draw=ImageDraw.Draw(img)
    def font(size,bold=False):
        candidate = (Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts'/('arialbd.ttf' if bold else 'arial.ttf')) if os.name == 'nt' else Path('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf')
        return ImageFont.truetype(str(candidate),max(12,int(size)))
    scale=width/1280
    if LOGO.is_file():
        logo=Image.open(LOGO).convert('RGBA')
        logo.thumbnail((int(width*.65),int(height*.2)))
        img.paste(logo,((width-logo.width)//2,int(height*.11)),logo)
    else:
        draw.text((width/2,height*.2),'Christ Church Southampton',font=font(38*scale,True),anchor='mm',fill='white')
    draw.rectangle((int(width*.1),int(height*.36),int(width*.9),int(height*.365)),fill='#f89b28')
    f=font(50*scale,True)
    words=plan['title'].split(); lines=[]; line=''
    for word in words:
        test=(line+' '+word).strip()
        if draw.textlength(test,font=f)>width*.85 and line: lines.append(line); line=word
        else: line=test
    if line: lines.append(line)
    if len(lines)>3:
        f=font(34*scale,True)
        lines=[]; line=''
        for word in words:
            test=(line+' '+word).strip()
            if draw.textlength(test,font=f)>width*.85 and line: lines.append(line); line=word
            else: line=test
        if line: lines.append(line)
    y=int(height*.43)
    for line in lines:
        draw.text((width/2,y),line,font=f,anchor='mt',fill='white'); y+=int(f.size*1.3)
    draw.text((width/2,max(y+20*scale,height*.73)),plan['passage'],font=font(30*scale),anchor='mt',fill='#f89b28')
    parsed_date=datetime.strptime(plan['date'],'%Y-%m-%d')
    date=f'{parsed_date.day} {parsed_date:%B %Y}'
    draw.text((width/2,height*.87),date,font=font(24*scale),anchor='mt',fill='#c3cfda')
    img.save(job/'intro.png')

def mono_filter(job, video, start, duration):
    """Avoid cancellation in dual-mono feeds; choose cleanest channel if channels oppose."""
    import numpy as np
    args=[str(BIN/'ffmpeg'),'-v','error','-ss',str(start),'-t',str(min(30,duration)),'-i',str(video),'-vn','-ar','16000','-f','f32le','-']
    streams=probe(video)['streams']; channels=next(x['channels'] for x in streams if x['codec_type']=='audio')
    raw=subprocess.check_output(args, **process_options())
    a=np.frombuffer(raw,dtype='<f4').reshape(-1,channels)
    stats={'channels':channels,'rms':[float(np.sqrt(np.mean(a[:,i]**2))) for i in range(channels)]}
    if channels==1: chosen='aformat=channel_layouts=mono'
    elif channels==2:
        corr=float(np.corrcoef(a.T)[0,1]); stats['correlation']=corr if np.isfinite(corr) else None
        if corr<-.2 or min(stats['rms'])<max(stats['rms'])*.1:
            idx=int(np.argmax(stats['rms'])); chosen=f'pan=mono|c0=c{idx}'; stats['choice']=f'channel {idx+1}'
        else: chosen='pan=mono|c0=0.5*c0+0.5*c1'; stats['choice']='average of both channels'
    else: chosen='aformat=channel_layouts=mono'
    write_json(job/'audio-channel-analysis.json',stats)
    return chosen

@exclusive
def prepare_sermon(job, plan, stabilize=True):
    if not 0<=float(plan['start'])<float(plan['end'])<=float(plan['duration']):
        raise ValueError('Invalid cut points')
    video=video_path(job); start=float(plan['start']); duration=float(plan['end'])-start
    streams=probe(video)['streams']; v=next(s for s in streams if s['codec_type']=='video')
    width=v['width']//2*2; height=v['height']//2*2
    rate=v.get('avg_frame_rate','30/1'); num,den=map(int,rate.split('/')); fps=num/den if den else 30
    fps=round(fps,3)
    settings={'start':start,'duration':duration,'source':str(video),'source_size':video.stat().st_size,'source_modified':video.stat().st_mtime_ns,'clean_filter':CLEAN,'audio_profile':audio_profile(),'audio_encoder_input':'s32','stabilize':stabilize,'stabilization_version':3,'width':width,'height':height,'fps':fps}
    if (job/'media-settings.json').exists() and (job/'sermon.mp4').exists() and (job/'cleaned-audio.wav').exists() and (job/'audio-settings.json').exists() and read_json(job/'media-settings.json')==settings:
        return settings
    mono=mono_filter(job,video,start,duration)
    audio,norm=prepare_audio(job,video,start,duration,mono,settings['audio_profile'])
    # Quantize inaudible near-zero float residue before AAC. A full-length
    # near-silence decode/re-encode stalled; S32 completed that reproduction.
    # The precise codec defect is unproven. S32 retains ample source precision.
    norm+=',aformat=sample_fmts=s32'
    old_settings=read_json(job/'media-settings.json') if (job/'media-settings.json').exists() else {}
    video_keys=('start','duration','source','source_size','source_modified','stabilize','stabilization_version','width','height','fps')
    reuse_video=(job/'sermon.mp4').is_file() and all(old_settings.get(k)==settings[k] for k in video_keys)
    if reuse_video:
        status(job,'Rendering','Replacing audio while preserving the already stabilized video',total_seconds=duration,log_file='render.log')
        temporary=job/'sermon.tmp.mp4'
        command([BIN/'ffmpeg','-y','-i',job/'sermon.mp4','-i',audio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-af',norm,'-c:a','aac','-b:a','128k','-ar','48000','-ac','1','-t',str(duration),'-movflags','+faststart',temporary],job,'render')
        temporary.replace(job/'sermon.mp4')
        write_json(job/'media-settings.json',settings)
        return settings
    # Relative transform filename avoids FFmpeg's platform-specific filter path escaping.
    transform=job/'transforms.trf'
    vf=f'fps={fps},format=yuv420p'
    if stabilize:
        status(job,'Measuring camera movement','Conservative two-pass stabilization; modest 3% crop',total_seconds=duration,log_file='stabilize-measure.log')
        measure_settings={k:settings[k] for k in ('start','duration','source','source_size','source_modified','fps')}
        reuse=(job/'transforms.trf').exists() and (job/'measurement-settings.json').exists() and read_json(job/'measurement-settings.json')==measure_settings
        if not reuse:
            with (job/'stabilize-measure.log').open('w') as log:
                subprocess.run([str(BIN/'ffmpeg'),'-y','-threads','6','-ss',str(start),'-t',str(duration),'-i',str(video),'-an','-vf',vf+',vidstabdetect=shakiness=4:accuracy=15:result=transforms.trf','-f','null','-'],cwd=job,stdout=log,stderr=log,check=True, **process_options())
            write_json(job/'measurement-settings.json',measure_settings)
        vf+=',vidstabtransform=input=transforms.trf:smoothing=15:optalgo=gauss:optzoom=0:zoom=3:maxshift=12:maxangle=0.01:crop=black:interpol=bilinear'
    status(job,'Rendering','Encoding the sermon with cleaned mono audio',total_seconds=duration,log_file='render.log')
    with (job/'render.log').open('w') as log:
        subprocess.run([str(BIN/'ffmpeg'),'-y','-threads','6','-ss',str(start),'-t',str(duration),'-i',str(video),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-vf',vf,'-af',norm,'-c:v','libx264','-preset','veryfast','-crf','19','-threads','6','-c:a','aac','-b:a','128k','-ar','48000','-ac','1','-movflags','+faststart','sermon.mp4'],cwd=job,stdout=log,stderr=log,check=True, **process_options())
    write_json(job/'media-settings.json',settings)
    return settings

@exclusive
def render(job, stabilize=True):
    plan=read_json(job/'plan.json'); validate(plan)
    if plan.get('issues') and not plan.get('confirmed'):
        raise ValueError('The analysis needs information or cut-point review. Complete the review before rendering.')
    settings=prepare_sermon(job,plan,stabilize)
    width=settings['width']; height=settings['height']; fps=settings['fps']; duration=settings['duration']
    status(job,'Creating intro','Creating the church title card',total_seconds=INTRO_SECONDS)
    card(job,plan,width,height)
    command([BIN/'ffmpeg','-y','-loop','1','-framerate',str(fps),'-i',job/'intro.png','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t',str(INTRO_SECONDS),'-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-threads','6','-c:a','aac','-b:a','128k','-ar','48000','-ac','1',job/'intro.mp4'],job,'intro-encode')
    first_section=next(iter(plan.get('sections',[])),{}).get('name','Bible reading')
    chapter_starts=[(0,'Intro'),(INTRO_SECONDS,first_section)]
    for section in plan.get('sections',[])[1:]:
        if section.get('start') is not None: chapter_starts.append((INTRO_SECONDS+float(section['start'])-float(plan['start']),section['name']))
    for section in plan.get('sermon_points',[]):
        chapter_starts.append((INTRO_SECONDS+float(section['start'])-float(plan['start']),section['name']))
    chapter_starts=sorted(set((offset,label) for offset,label in chapter_starts if 0<=offset<duration+INTRO_SECONDS))
    meta=[';FFMETADATA1']
    for i,(offset,label) in enumerate(chapter_starts):
        end_offset=chapter_starts[i+1][0] if i+1<len(chapter_starts) else duration+INTRO_SECONDS
        if offset<0 or end_offset<=offset:continue
        label=label.replace('\\','\\\\').replace('=','\\=').replace(';','\\;').replace('#','\\#').replace('\n',' ')
        meta.extend(['[CHAPTER]','TIMEBASE=1/1000',f'START={round(offset*1000)}',f'END={round(end_offset*1000)}',f'title={label}'])
    (job/'chapters.ffmeta').write_text('\n'.join(meta)+'\n', encoding='utf-8')
    write_json(job/'sermon-details.json',{'title':plan['title'],'date':plan['date'],'passage':plan['passage'],'original_cut':{'start':plan['start'],'end':plan['end']},'chapters':[{'time':x,'title':t} for x,t in chapter_starts]})
    (job/'concat.txt').write_text("file 'intro.mp4'\nfile 'sermon.mp4'\n")
    status(job,'Joining intro','Adding the five-second church intro card',total_seconds=duration+INTRO_SECONDS)
    # Encode the enhanced PCM once for the master, with exactly five seconds of
    # initial silence. Avoid a second AAC decode/encode across a concat boundary,
    # its extra codec delay and pathological near-silence encoder state.
    normalized=read_json(job/'audio-settings.json')['normalization_filter']
    joined_audio=normalized+f',adelay={INTRO_SECONDS*1000}:all=1,apad,aformat=sample_fmts=s32'
    command([BIN/'ffmpeg','-y','-f','concat','-safe','1','-i',job/'concat.txt','-i',job/'cleaned-audio.wav','-i',job/'chapters.ffmeta','-map_metadata','2','-map_chapters','2','-map','0:v:0','-map','1:a:0','-af',joined_audio,'-t',str(duration+INTRO_SECONDS),'-c:v','copy','-c:a','aac','-b:a','128k','-ar','48000','-ac','1','-movflags','+faststart',job/'finished.mp4'],job,'concat')
    check=probe(job/'finished.mp4'); a=next(x for x in check['streams'] if x['codec_type']=='audio')
    actual=float(check['format']['duration']); expected=duration+INTRO_SECONDS
    if a['channels']!=1 or abs(actual-expected)>.5: raise RuntimeError('Output duration or mono validation failed.')
    status(job,'Checking video','Decoding the complete video to check the finished file',total_seconds=duration+INTRO_SECONDS)
    command([BIN/'ffmpeg','-stats','-i',job/'finished.mp4','-af','loudnorm=I=-20:TP=-2:LRA=50:print_format=json','-f','null','-'],job,'decode-check')
    measured=re.findall(r'\{\s*"input_i".*?\}',(job/'decode-check.log').read_text(encoding='utf-8',errors='replace'),re.S)
    if not measured: raise RuntimeError('The finished audio measurement is missing.')
    audio_measurement=json.loads(measured[-1])
    if float(audio_measurement['input_tp'])>-.5: raise RuntimeError('The encoded audio exceeds the safe true-peak limit; inspect audio settings.')
    write_json(job/'validation.json',{'audio_channels':a['channels'],'duration':actual,'expected_duration':expected,'full_decode':'passed','stabilized':stabilize,'audio_profile':settings['audio_profile'],'audio_encoder_input':'s32','audio_master_source':'single AAC encode from enhanced PCM with five-second silence','audio_lufs':float(audio_measurement['input_i']),'audio_true_peak_db':float(audio_measurement['input_tp']),'plan':plan})
    from .preview import prepare
    prepare(job)
    status(job,'Finished',str(job/'finished.mp4'))
    return job/'finished.mp4'
