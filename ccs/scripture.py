"""Local lexical verse matching against a cached public-domain Bible, without AI."""
import re
from collections import Counter
from .common import ROOT
NAMES=['Genesis','Exodus','Leviticus','Numbers','Deuteronomy','Joshua','Judges','Ruth','1 Samuel','2 Samuel','1 Kings','2 Kings','1 Chronicles','2 Chronicles','Ezra','Nehemiah','Esther','Job','Psalms','Proverbs','Ecclesiastes','Song of Solomon','Isaiah','Jeremiah','Lamentations','Ezekiel','Daniel','Hosea','Joel','Amos','Obadiah','Jonah','Micah','Nahum','Habakkuk','Zephaniah','Haggai','Zechariah','Malachi','Matthew','Mark','Luke','John','Acts','Romans','1 Corinthians','2 Corinthians','Galatians','Ephesians','Philippians','Colossians','1 Thessalonians','2 Thessalonians','1 Timothy','2 Timothy','Titus','Philemon','Hebrews','James','1 Peter','2 Peter','1 John','2 John','3 John','Jude','Revelation']
CODES='GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV'.split()
STOP=set('a an the of and or to for in on at by as is are be it that this those who you your he his they their we our i my with will do does have has from but not them when'.split())
def tokens(text):
    text=text.lower().replace('judgement','judgment').replace('gospel','good news').replace('people','men')
    return set(re.sub(r'(?:ing|ed|s)$','',x) for x in re.findall(r'[a-z]+',text) if x not in STOP and len(x)>2)
def infer_reading(reference,segments,reading_time):
    m=re.match(r'(.+?) (\d+)',reference)
    if not m or m[1] not in NAMES:return None
    path=ROOT/'assets/bible/engwebp_vpl.txt'
    if not path.exists():return None
    code=CODES[NAMES.index(m[1])]; chapter=int(m[2]); verses=[]
    for line in path.read_text().splitlines():
        v=re.match(rf'{code} {chapter}:(\d+) (.+)',line)
        if v:verses.append((int(v[1]),tokens(v[2]),v[2]))
    if not verses:return None
    after=[s for s in segments if reading_time<=s['start']<=reading_time+420]
    finish=next((s['start'] for s in after if s['start']>reading_time+40 and re.search(r'thanks (?:so much|very much)|thank you.{0,20}(?:reading|pete)|my name is|my welcome',s['text'],re.I)),reading_time+300)
    after=[s for s in after if s['start']<finish]
    matches=[]
    for i,s in enumerate(after):
        text=''; alternatives=[]
        for j in range(i,min(i+4,len(after))):
            if j>i and after[j]['start']-after[j-1]['end']>4: break
            text+=' '+after[j]['text']; t=tokens(text)
            if len(t)<5: continue
            scored=sorted(((len(t&v)/max(1,len(t|v)),n) for n,v,_ in verses),reverse=True)
            best,n=scored[0]; margin=best-scored[1][0] if len(scored)>1 else best
            if best>=.32 and margin>=.07:
                alternatives.append({'verse':n,'time':s['start'],'score':round(best,3),'quote':text.strip()})
        if alternatives: matches.append(max(alternatives,key=lambda x:x['score']))
    if len(matches)<4:return None
    # An ordered run distinguishes an actual reading from random sermon quotations.
    ordered=[]
    for match in matches:
        if not ordered or match['verse']>=ordered[-1]['verse']: ordered.append(match)
    if len(set(x['verse'] for x in ordered))<4:return None
    lo=ordered[0];hi=ordered[-1]
    return {'passage':f'{m[1]} {chapter}:{lo["verse"]}–{hi["verse"]}',
        'reading_starts':lo['time'],'reading_ends':finish,'matches':ordered,
        'confidence':'supported' if lo['score']>=.4 and hi['score']>=.4 else 'review'}
