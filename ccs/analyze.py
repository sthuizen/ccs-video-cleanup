"""Conservative, deterministic interpretation of cached transcript and slide evidence."""
import re
from collections import Counter
from datetime import datetime
from .common import read_json, write_json, status, probe, timestamp
BOOKS='Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|(?:[123]\\s*)?Samuel|(?:[12]\\s*)?Kings|(?:[12]\\s*)?Chronicles|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song of (?:Songs|Solomon)|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|(?:[123]\\s*)?John|Acts|Romans|[12]\\s*Corinthians|Galatians|Ephesians|Philippians|Colossians|[12]\\s*Thessalonians|[12]\\s*Timothy|Titus|Philemon|Hebrews|James|[12]\\s*Peter|Jude|Revelation'
REF=re.compile(r'\b('+BOOKS+r')[\s,]+(?:(?:the )?beginning of\s+)?(?:chapter\s+)?(\d{1,3})(?:\s*[:.,]\s*(\d{1,3})(?:\s*[–—-]\s*(\d{1,3}))?|\s*(?:vers(?:es?|e)?|from verse)\s+(\d{1,3})(?:\s*(?:to|through|[–—-])\s*(\d{1,3}))?)?',re.I)
SMALL=['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen']
NUM={w:i for i,w in enumerate(SMALL)}; NUM.update({'twenty':20,'thirty':30,'forty':40,'fifty':50,'sixty':60,'seventy':70,'eighty':80,'ninety':90})
READ=re.compile(r'(?:bible|scripture|our|the|first|second|today.s) reading|reading (?:today|this morning|from|is)|(?:turn|open|looking) (?:with me |your bibles |our bibles )?(?:to|at)|going to read|read (?:together|from)',re.I)
CLOSE=re.compile(r"(?:we.re|we are|let.s|let us|going to|shall we|please) (?:now |all |stand (?:and |to )?)?(?:sing|stand and sing)|(?:our|the) (?:last|final|closing|next) (?:song|hymn)|(?:band|musicians|music team).{0,35}(?:come|lead)|\b(?:please |let.s |let us )?stand (?:up |and )?together\b|(?:finish|close|conclude).{0,25}(?:sing|song)",re.I)

def reading_candidates(segments):
    """Match announcements across caption fragments, then verify reference-only cues.

    Captions can omit the announcement or put the verse range in a later cue.
    A bare reference is never enough: an ordered local Bible match must follow.
    """
    from .scripture import infer_reading
    candidates=[]
    for i,segment in enumerate(segments):
        context=' '.join(x['text'] for x in segments[i:i+4] if x['start']<=segment['end']+25)
        references=refs(context)
        if not references:
            continue
        explicit=bool(READ.search(segment['text'])) and not bool(re.search(r'keep.{0,30}open',segment['text'],re.I))
        if not explicit and not refs(segment['text']):
            continue
        passages=[]
        for reference in references:
            # Only extend a chapter reference with an explicit nearby verse range.
            # Stop at another book reference and exclude page numbers and sermon points.
            if ':' not in reference:
                for later in segments[i+1:]:
                    if later['start']>segment['end']+120: break
                    if refs(later['text']): break
                    m=re.match(r'^(?:[>\s]+)?(?:vers(?:es?|e)?\s+)?(\d{1,3})\s*[–—-]\s*(\d{1,3})(?:\b|$)',normalized(later['text']))
                    if m and int(m[1])<=int(m[2]):
                        reference+=f':{int(m[1])}–{int(m[2])}'
                        break
            passages.append(reference)
        alignments=[infer_reading(reference,segments,segment['start']) for reference in dict.fromkeys(passages)]
        alignments=[x for x in alignments if x]
        alignment=max(alignments,key=lambda x:(x['confidence']=='supported',len(set(m['verse'] for m in x['matches'])))) if alignments else None
        if explicit or alignment:
            candidates.append({'time':segment['start'],'end':segment['end'],'text':segment['text'],
                               'passages':list(dict.fromkeys(passages)),'index':i,
                               'kind':'announcement' if explicit else 'reference and ordered scripture',
                               'alignment':alignment,
                               'reader_intro':{'time':segment['start'],'quote':segment['text']} if re.search(r'(?:our|the|bible|scripture|today.s) reading(?: today| this morning)? (?:is|comes|from)',segment['text'],re.I) else None})
    grouped=[]
    for candidate in candidates:
        if grouped and candidate['time']-grouped[-1]['time']<100:
            previous=grouped[-1]
            previous['passages']=list(dict.fromkeys(previous['passages']+candidate['passages']))
            if candidate.get('reader_intro'): previous['reader_intro']=candidate['reader_intro']
            if candidate['kind']=='announcement' and previous['kind']!='announcement':
                for field in ('time','end','text','index','kind'):
                    previous[field]=candidate[field]
            if candidate['alignment'] and (not previous['alignment'] or
                len(set(x['verse'] for x in candidate['alignment']['matches']))>len(set(x['verse'] for x in previous['alignment']['matches']))):
                previous['alignment']=candidate['alignment']
        else: grouped.append(candidate.copy())
    return grouped


def clamp_sections(plan):
    """Keep inferred chapter boundaries consistent with the operator's final cut."""
    start,end=plan.get('start'),plan.get('end')
    if start is None or end is None or end<=start:
        return
    kept=[]
    for original in plan.get('sections',[]):
        section=original.copy()
        for field in ('start','end'):
            if section.get(field) is not None:
                section[field]=max(start,min(end,section[field]))
        if section.get('start') is not None and section.get('end') is not None and section['end']<=section['start']:
            continue
        kept.append(section)
    if not kept:
        kept=[{'name':'Selected reading and sermon','start':start,'end':end}]
    kept[0]['start']=start
    kept[-1]['end']=end
    plan['sections']=kept
    plan['sermon_points']=[point for point in plan.get('sermon_points',[]) if start<=point['start']<end]


def normalized(text):
    text=re.sub(r'\b(first|second|third)\s+(John|Peter|Corinthians|Thessalonians|Timothy|Samuel|Kings|Chronicles)\b',lambda m:str({'first':1,'second':2,'third':3}[m[1].lower()])+' '+m[2],text,flags=re.I)
    words=r'\b(?:'+ '|'.join(NUM)+r')(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?\b'
    return re.sub(words,lambda m:str(sum(NUM[x] for x in re.split('[- ]',m[0].lower()))),text,flags=re.I)

def refs(text):
    out=[]
    for m in REF.finditer(normalized(text)):
        book=re.sub(r'\s+',' ',m[1].title()).replace('Song Of','Song of')
        verse=m[3] or m[5]; end=m[4] or m[6]
        value=f'{book} {int(m[2])}'
        if verse: value+=':'+str(int(verse))
        if end: value+='–'+str(int(end))
        out.append(value)
    return out

def dates(text):
    matches=re.findall(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b',text,re.I)
    results=[]
    for day,month,year in matches:
        try: results.append(datetime.strptime(f'{day} {month} {year}','%d %B %Y').date().isoformat())
        except ValueError: pass
    results.extend(re.findall(r'\b20\d{2}-\d{2}-\d{2}\b',text))
    return results

def analyze(job, video, transcript, screens):
    status(job,'Finding sermon','Matching reading announcements, scripture references and closing-song cues')
    from .transcribe import split_gaps
    segs=split_gaps(transcript['segments']); info=read_json(job/'source.info.json')
    duration=float(probe(video)['format']['duration'])
    grouped=reading_candidates(segs)
    endings=[{'time':x['start'],'end':x['end'],'text':x['text'],'index':i}
             for i,x in enumerate(segs) if CLOSE.search(x['text'])]
    pairs=[]
    for r in grouped:
        for e in endings:
            length=e['time']-r['time']
            if 12*60<=length<=65*60:
                speech=sum(max(0,min(x['end'],e['time'])-max(x['start'],r['time'])) for x in segs if x['end']>r['time'] and x['start']<e['time'])
                score=min(1,speech/max(1,length))
                pairs.append((score,r,e))
                break
    pairs.sort(key=lambda x:x[0],reverse=True)
    issues=[]; evidence={}
    start=end=passage=title=date=None
    if pairs:
        score,r,e=pairs[0]
        start=max(0,r['time']-1); end=e['time']
        closing_prayers=[x for x in segs if e['time']-100<x['end']<=e['time'] and re.search(r'\bamen[.!]?\s*$',x['text'],re.I)]
        handoffs=[]
        for i,x in enumerate(segs):
            if not r['time']+900<x['start']<e['time'] or e['time']-x['start']>600 or i==0: continue
            text=' '.join(y['text'] for y in segs[i:i+2])
            if not re.match(r'(?:thank you|thanks (?:so much|very much))\s+[A-Za-z]+',text,re.I): continue
            previous=segs[i-1]
            recent=' '.join(y['text'] for y in segs[max(0,i-12):i])
            if re.search(r'pray|prayer|bow our heads',recent,re.I) and re.search(r'amen|jesus christ',previous['text'],re.I):
                handoffs.append((previous,x,text))
        if handoffs:
            prayer,host,host_text=handoffs[-1]
            end=min(host['start']+.5,prayer['end']+.5)
            closing_prayers=[prayer]
        elif closing_prayers:
            prayer=closing_prayers[-1]; end=min(e['time'],prayer['end']+.5)
        else:
            issues.append('The sermon ending is approximate. Confirm the last words before the closing song.')
        evidence['start']={'source':'transcript','time':r['time'],'quote':r['text']}
        evidence['end']={'source':'transcript','time':end,'quote':e['text'],'closing_song_cue':e['time']}
        if handoffs: evidence['end']['speaker_handoff']={'time':host['start'],'quote':host_text}
        if closing_prayers: evidence['end']['closing_prayer']={'time':prayer['end'],'quote':prayer['text']}
        # A song announcement can be part of a sermon illustration. Keep the candidate reviewable.
        if score<.5: issues.append('The proposed interval contains substantial silence or music; confirm the reading and sermon boundaries.')
        if len(pairs)>1 and pairs[1][1]['time']!=r['time'] and abs(score-pairs[1][0])<.15:
            issues.append('More than one reading/sermon interval is plausible; confirm the start and end.')
        passage=Counter(r['passages']).most_common(1)[0][0]
        if r.get('alignment'): passage=r['alignment']['passage']
        evidence['passage']={'source':r['kind'],'candidates':r['passages'],
                             'announcement_time':r['time'],
                             'requires_local_verification':r['kind']=='reference and ordered scripture'}
        nearby=[x for x in screens if start-60<=x['time']<=start+300]
        slide_refs=[p for x in nearby for p in refs(x['text'])]
        if slide_refs:
            full=[p for p in slide_refs if p.startswith(passage.split(':')[0]) and ':' in p]
            if full: passage=Counter(full).most_common(1)[0][0]
        # Speech-recognized verse numbers can be wrong; require corroboration or flag them.
        from .scripture import infer_reading
        alignment=r.get('alignment') or infer_reading(passage,segs,r['time'])
        if alignment and alignment['confidence']=='supported':
            passage=alignment['passage']
            start=max(r['time'],alignment['reading_starts']-.7)
            evidence['passage']['verse_matching']=alignment
            evidence['start']={'source':'spoken scripture matched to local Bible text','time':start,'quote':alignment['matches'][0]['quote']}
            intro=r.get('reader_intro')
            if intro and 0<=alignment['reading_starts']-intro['time']<=30:
                start=max(0,intro['time']-.7)
                evidence['start']={'source':'reader announcement followed by matched scripture','time':start,
                                   'quote':intro['quote'],'scripture_match_time':alignment['reading_starts']}
                evidence['passage']['announcement_time']=intro['time']
        if passage not in slide_refs and not (alignment and alignment['confidence']=='supported'):
            issues.append('Confirm the Bible passage; it is recognized from speech but not corroborated by a legible slide.')
        if len(grouped)>1 and len(pairs)>1:
            issues.append('Multiple Bible readings were detected; confirm which belongs to the sermon.')
    else:
        if grouped:
            strongest=max(grouped,key=lambda x:(bool(x.get('alignment')),len(x.get('alignment',{}).get('matches',[]) if x.get('alignment') else [])))
            alignment=strongest.get('alignment')
            passage=alignment['passage'] if alignment else strongest['passages'][0]
            start=max(0,(alignment['reading_starts']-.7) if alignment else strongest['time']-1)
            evidence['start']={'source':'reading candidate; ending unresolved','time':start,'quote':strongest['text']}
            intro=strongest.get('reader_intro')
            if alignment and intro and 0<=alignment['reading_starts']-intro['time']<=30:
                start=max(0,intro['time']-.7)
                evidence['start']={'source':'reader announcement; ending unresolved','time':start,'quote':intro['quote']}
            evidence['passage']={'source':'reading evidence','candidates':strongest['passages'],
                                 'announcement_time':strongest['time'],
                                 'requires_local_verification':strongest['kind']=='reference and ordered scripture'}
            if alignment: evidence['passage']['verse_matching']=alignment
        if start is not None:
            issues.append('No reliable sermon ending found. Confirm the end using the timestamped transcript and source video.')
        else:
            issues.append('No unambiguous reading-to-sermon interval found. Supply start and end using the timestamped transcript and source video.')
    date_candidates=[]
    for x in screens:
        date_candidates.extend(dates(x['text']))
    date_candidates.extend(dates(info.get('title','')))
    if date_candidates:
        date=Counter(date_candidates).most_common(1)[0][0]
        evidence['date']={'source':'on-screen text or video title (not upload date)','candidates':list(dict.fromkeys(date_candidates))}
        if len(set(date_candidates))>1: issues.append('Conflicting service dates found; confirm the date.')
    else: issues.append('No service date found in the video or its title. Supply the sermon date.')
    # Explicit spoken titles are also suitable; incidental sermon phrases are not.
    spoken_titles=[]
    for x in segs:
        m=re.search(r'(?:sermon|talk|message|title) (?:today |this morning )?(?:is (?:called |entitled )?|is entitled |is called |called )+[\"“]?([^.!?]{5,100})',x['text'],re.I)
        if m and (start is None or start-120<=x['start']<=start+600): spoken_titles.append((m[1].strip(' ,\"'),x['start']))
    # Titles are never invented from incidental phrases. Find explicitly labelled titles only.
    titles=spoken_titles.copy()
    for x in screens:
        for line in x['text'].splitlines():
            m=re.match(r'(?:sermon|talk|message)\s*(?:title)?\s*[:–—-]\s*(.{5,100})$',line,re.I)
            if m: titles.append((m[1].strip(),x['time']))
    if titles:
        title=Counter(t[0] for t in titles).most_common(1)[0][0]
        evidence['title']={'source':'explicit spoken or on-screen title','candidates':titles}
    else: issues.append('No explicit sermon title found in the recording. Supply a descriptive title.')
    plan={'version':1,'start':start,'end':end,'passage':passage,'title':title,'date':date,
          'duration':duration,'issues':issues,'evidence':evidence,
          'candidates':{'readings':grouped,'closing_songs':endings},'confirmed':False}
    plan['sections']=[{'name':'Bible reading','start':start,'end':evidence.get('passage',{}).get('verse_matching',{}).get('reading_ends')},{'name':'Sermon and closing prayer','start':evidence.get('passage',{}).get('verse_matching',{}).get('reading_ends'),'end':end}]
    if start is not None and end is not None:
        prayer_cues=[x for x in segs if end-150<x['start']<end and re.search(r'bow our heads|end with.{0,35}now|let(?: us|.s) pray',x['text'],re.I)]
        if prayer_cues:
            prayer_start=prayer_cues[-1]['start']
            plan['sections'][-1]['name']='Sermon'
            plan['sections'][-1]['end']=prayer_start
            plan['sections'].append({'name':'Closing prayer','start':prayer_start,'end':end})
        point_cues=[]
        for i,x in enumerate(segs):
            if not start+180<x['start']<end-180: continue
            context=' '.join(y['text'] for y in segs[i:i+2])
            match=re.search(r'(what you [a-z]+ matters more than (?:what you [a-z]+|who you are))',context,re.I)
            if match:
                label=match[1].capitalize()
                if label not in [y['name'] for y in point_cues]:point_cues.append({'name':label,'start':x['start']})
        for i,x in enumerate(segs):
            if not start+180<x['start']<end-180:continue
            context=' '.join(y['text'] for y in segs[i:i+2])
            if re.search(r'doesn.t matter what you know.{0,90}about what you do',context,re.I):
                label='What you do matters more than what you know'
                if label not in [y['name'] for y in point_cues]:point_cues.append({'name':label,'start':x['start']})
        plan['sermon_points']=sorted(point_cues,key=lambda x:x['start'])
    existing=job/'review.json'
    if existing.exists():
        overrides=read_json(existing)
        for k in ('start','end','passage','title','date'): 
            if overrides.get(k) is not None: plan[k]=overrides[k]
        plan['confirmed']=overrides.get('confirmed',False)
    clamp_sections(plan)
    write_json(job/'plan.json',plan)
    return plan
