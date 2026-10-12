#!/usr/bin/env python3
"""Build the two illustrated, versioned operator PDFs from actual UI captures."""
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,PageBreak,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.colors import HexColor,white
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_LEFT
from PIL import Image as PILImage

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'output/pdf';SHOTS=ROOT/'docs/screenshots';OUT.mkdir(parents=True,exist_ok=True)
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='GuideTitle',fontName='Helvetica-Bold',fontSize=27,leading=31,textColor=HexColor('#132535'),spaceAfter=15))
styles.add(ParagraphStyle(name='GuideHeading',fontName='Helvetica-Bold',fontSize=20,leading=24,textColor=HexColor('#132535'),spaceAfter=14))
styles.add(ParagraphStyle(name='GuideBody',fontName='Helvetica',fontSize=11,leading=16,spaceAfter=10,textColor=HexColor('#263c4e')))
styles.add(ParagraphStyle(name='GuideNote',fontName='Helvetica',fontSize=9,leading=12,spaceAfter=12,textColor=HexColor('#526779')))
styles.add(ParagraphStyle(name='GuideCode',fontName='Courier',fontSize=9,leading=13,spaceAfter=12))
styles.add(ParagraphStyle(name='GuideCell',fontName='Helvetica',fontSize=9.5,leading=13))

def p(text,kind='GuideBody'):return Paragraph(text,styles[kind])
def shot(name,height=255,crop=None):
    path=SHOTS/name
    if crop:
        image=PILImage.open(path);image=image.crop(crop)
        target=ROOT/'tmp/pdfs'/('crop-'+name);target.parent.mkdir(parents=True,exist_ok=True);image.save(target);path=target
    with PILImage.open(path) as im:w,h=im.size
    scale=min(499/w,height/h)
    return Image(str(path),width=w*scale,height=h*scale,hAlign='LEFT')
def footer(canvas,doc):
    canvas.setStrokeColor(HexColor('#fa9a2b'));canvas.setLineWidth(2);canvas.line(48,44,547,44)
    canvas.setFont('Helvetica',9);canvas.setFillColor(HexColor('#526779'))
    canvas.drawString(48,29,'Christ Church Video Cleanup | 1.4.1 | '+doc.platform)
    canvas.drawRightString(547,29,str(doc.page))
def page(story,title):
    if story:story.append(PageBreak())
    story.append(p(title,'GuideHeading'))
def steps(story,items):
    for n,text in enumerate(items,1):story.append(p(f'<b>{n}.</b> {text}'))

def guide(platform):
    s=[];is_win=platform=='Windows'
    s += [p('Christ Church<br/>Video Cleanup','GuideTitle'),p(platform+' user guide - version 1.4.1','GuideHeading'),p('From a completed service to a sermon video, podcast audio, or both.'),p('Keep the computer awake and connected while downloading. Use headphones to compare quiet speech, word endings and background noise. The app processes one service at a time.')]
    s.append(p('Install and open','GuideHeading'))
    if is_win:
        steps(s,['Download <b>ccs-video-cleanup_1.4.1_windows_x64_setup.exe</b> from the private GitHub release. Use a 64-bit Intel/AMD Windows 10 or 11 PC.','Run the installer. Open <b>Christ Church Video Cleanup</b> from the desktop or Start menu. The Start menu also includes this PDF, your saved files and the setup log.','Keep the PC online while the first-run browser page prepares local tools. Approve the Microsoft C++ prerequisite prompt if it appears. Use Retry if setup reports a recoverable failure.'])
        s.append(p('The installer is unsigned: Windows may show an unknown-publisher prompt. Check the source and SHA-256 checksum; do not disable Windows protection. No system Python or cloud AI account is needed.','GuideNote'))
    else:
        steps(s,['Download the <b>1.4.1 amd64 .deb</b> and checksum from the private GitHub release. Targets: Ubuntu 24.04 LTS and Debian 13; enable Ubuntu universe if needed.','In the download folder, run the commands below. Run setup as your normal user, without sudo.','Open <b>Christ Church Video Cleanup</b> from the applications menu. First setup downloads and checks local tools and models.'])
        s += [p('sha256sum -c ccs-video-cleanup_1.4.1_amd64.deb.sha256<br/>sudo apt install ./ccs-video-cleanup_1.4.1_amd64.deb<br/>ccs-video-cleanup setup','GuideCode'),p('Optional church logo: ccs-video-cleanup setup --logo /path/to/logo.png. Otherwise the intro uses text branding.','GuideNote')]
    s.append(p('Get installers and checksum files: <link href="https://github.com/thenailedone/ccs-video-cleanup/releases/tag/v1.4.1" color="#b76a0e">GitHub release v1.4.1</link>. Repository access is required. Allow several GB for tools/models and additional space for recordings.','GuideNote'))

    page(s,'1. Choose a service and your outputs')
    steps(s,['For a new service, paste its completed YouTube URL. Choose <b>Check resolutions</b> if it has not checked automatically. Highest available is the default; a lower resolution makes a smaller video. Then choose <b>Prepare sermon</b>.','For a saved service, choose it under <b>Prepared services</b>. A fresh launch deliberately selects nothing. A saved job must be selected before its review, samples and exports appear.','Under <b>Where will you share this sermon?</b>, choose YouTube video, Spotify podcast audio, or both. You can change this before creating the exports.'])
    s += [shot('service.png',210),Spacer(1,10),shot('destinations.png',115,(20,425,1053,580)),p('YouTube creates an MP4 with the church intro. Spotify creates an MP3 with the same tested voice settings and no silent title-card lead-in. These choices create local files; they do not publish anything.','GuideNote')]
    s.append(p(('Windows starts with anonymous download access. ' if is_win else 'Linux starts with Firefox download access. ')+'If YouTube asks for verification, sign into YouTube in Firefox and enter firefox under Download access. Clear that field for anonymous access. Never share your cookies.','GuideNote'))

    page(s,'2. Check the clip and intro details')
    s.append(p('After analysis, Step 2 opens when details need review. Use the pinned step buttons to return to any available step. Sections collapse to keep the next action clear.'))
    s += [shot('review.png',270),Spacer(1,12)]
    steps(s,['Check the first and last spoken words against the original service. Enter start/end as <b>HH:MM:SS</b>. Include the intended reading and sermon; stop before unwanted music or announcements.','Check the actual service date, Bible passage and title. A descriptive title should reflect the recorded words. Do not use the upload date or assume an announcement slide is the service date.','Choose <b>Save details and make audio tests</b>. The activity indicator shows that quiet and louder voice samples are being made.'])
    s.append(p('If no sermon interval was found, start and end stay blank. Play the source and use Evidence and candidate sections / the timestamped transcript to identify the desired portion. Baptisms and other unusual services may require manual selection.','GuideNote'))

    page(s,'3. Listen and choose the voice cleanup')
    s += [p('Use the same headphones and device volume for every comparison. Listen to both Quiet voice and Louder voice for each preset.'),shot('listen.png',290),Spacer(1,12)]
    steps(s,['Start with <b>Balanced cleanup</b>. Try <b>Natural voice</b> if soft words are damaged; try <b>Stronger cleanup</b> if too much background noise remains.','If a preset sounds good, choose its orange <b>Choose and create</b> button. Its wording follows your selected destinations: video, podcast audio, or both. Step 4 is then marked Done.','If it needs work, choose <b>Choose and tweak audio</b>. This opens Step 4 with that preset loaded.'])
    s.append(p('Check soft prayer, final consonants and pauses. If speech sounds watery, thin or metallic, prefer gentler processing. Room reflections, coughs and nearby voices cannot always be removed cleanly.','GuideNote'))

    page(s,'4. Tweak, retest and reset')
    s += [shot('tweak.png',235),Spacer(1,10)]
    data=[['Control','Small changes to try']]
    for a,b in [('Background noise reduction','Lower if soft words disappear; higher removes more room noise.'),('Steady hiss','For fan/hiss; reduce if consonants sound metallic.'),('Low rumble','Higher removes low hum; lower if deep voices sound thin.'),('Voice clarity','Small lift helps consonants; too much sharpens hiss and s sounds.'),('Even out voice levels','Higher narrows quiet/loud differences; can raise room noise.'),('Listening volume','Closer to -16 LUFS is louder; peak protection remains on.')]:data.append([p(a,'GuideCell'),p(b,'GuideCell')])
    table=Table(data,colWidths=[155,344],hAlign='LEFT');table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#192938')),('TEXTCOLOR',(0,0),(-1,0),white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,0),10),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,1),(-1,-1),.3,HexColor('#ccd5dc'))]));s.append(table)
    s += [Spacer(1,12),p('Change one control at a time. Open <b>What this changes</b> for help. Choose <b>Recreate test with my adjustments</b>, then listen to Your adjustment. Repeat until satisfied. Untested changes cannot be used for export.'),p('<b>Reset to chosen preset</b> restores the original preset. Recreate the test after resetting. When happy, choose <b>Use this adjustment and create</b> for your selected exports.')]

    page(s,'5. Check, download and share')
    s += [shot('exports.png',185,(20,135,1053,315)),Spacer(1,12),shot('exports-video.png',220),Spacer(1,12)]
    steps(s,['Wait for <b>Finished</b> in Step 5. Play the video intro and check the first/last words, framing and voice. Listen to the podcast beginning/end too.','For YouTube, choose <b>Download full-quality sermon</b>. This downloads finished.mp4; the lighter browser preview is only for checking.','For Spotify, choose <b>Download podcast MP3</b>. It is mono MP3 at 48 kHz and 128 kbps, using the same chosen cleanup and volume settings. The app fully decodes and checks the file before offering it.'])
    s.append(p('Upload the MP4 in YouTube Studio. Upload the MP3 as a new audio episode in Spotify for Creators, then enter the episode details there. <link href="https://support.spotify.com/ag/creators/article/publishing-audio-episodes/" color="#b76a0e">Spotify accepts mono/stereo MP3, M4A and WAV</link>. Publication remains your choice.','GuideNote'))

    page(s,'Saved services, tray and troubleshooting')
    s.append(p('<b>Keep or delete saved files.</b> Sources, samples, analysis and exports stay in the job folder for reuse. Open Manage saved services (closed by default), choose a trash button, review the named service, tick the acknowledgment and type DELETE. Delete all requires DELETE ALL. Files move to Trash / Recycle Bin; space is reclaimed when it is emptied. Deletion is blocked during processing.'))
    if is_win and (SHOTS/'windows-tray.png').exists():s += [shot('windows-tray.png',180),Spacer(1,10)]
    else:s += [shot('listen.png',45,(20,5,1053,104)),Spacer(1,10)]
    s.append(p('<b>Background services.</b> Closing the browser keeps work running. '+('Find the church icon beside the clock or in the hidden-icons overflow. Hover for the current task; right-click for progress and elapsed/remaining time.' if is_win else 'Use the orange church tray icon for the current task, progress and elapsed/remaining time. A compatible desktop tray host is required; the packaged tray uses user systemd.')+' Login startup is off by default. Select <b>Start automatically at login</b> to enable it; clear the checkmark to disable it without stopping current work. Choose Open Christ Church Video Cleanup to reconnect. Choose Quit and stop services to stop the app. Active desktop work asks first; stopping can require unfinished output to be recreated.'))
    s.append(p('<b>Ready versus Review.</b> Fresh launch shows Ready until you select a service. Active background work takes priority. Review means missing clip details; Listen means an audio choice is needed. The pinned bar stays visible while you scroll.'))
    s.append(p('<b>If something seems stuck:</b> check the pinned task and Processing steps; estimates may be unavailable during analysis. Needs information is waiting for your details, not downloading. Select the saved service and open Step 2. If YouTube requests sign-in, use Download access. For connection/setup errors, reopen the shortcut and inspect the setup/server logs.'))
    s.append(p('<b>Update safely.</b> Finish processing, quit services through the tray, then install the newer package. Jobs and cached models are preserved. Back up jobs before uninstalling or clearing saved services.'))
    location='%LOCALAPPDATA%\\CCSVideoCleanup' if is_win else '~/.local/share/ccs-video-cleanup (or XDG_DATA_HOME)'
    s.append(p('<b>Saved data:</b> '+location+'. '+('Start menu: Video files and evidence; Setup log; User guide (PDF).' if is_win else 'Installed PDF: /usr/share/doc/ccs-video-cleanup/. Source-checkout data remains in its project folder.'),'GuideNote'))
    s.append(p('Browser screenshots show the unchanged 1.4.0 interface using a synthetic Example sermon. The browser interface is shared by Linux and Windows; dates may display differently by locale. The Windows tray image is from the 1.4.0 test desktop; the new login startup checkbox is described above.','GuideNote'))
    doc=SimpleDocTemplate(str(OUT/f'CCS-Video-Cleanup-{platform}-Guide.pdf'),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=48,bottomMargin=62,title=f'Christ Church Video Cleanup 1.4.1 - {platform} user guide',author='Christ Church Southampton')
    doc.platform=platform;doc.build(s,onFirstPage=footer,onLaterPages=footer)
    print(doc.filename)

if __name__=='__main__':
    for platform in ('Linux','Windows'):guide(platform)
