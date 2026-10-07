"""Speech cleanup with bounded suppression and constant playback gain.

Dynamic loudness normalization can bring room noise up during pauses. Use one
gain for the entire selection and a peak limiter with automatic makeup disabled.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
from .common import BIN, DATA_ROOT, command, read_json, status, write_json
from .audio_setup import SHA256, WINDOWS_SHA256

VERSION = 2
FILTER = ('highpass=f=75,lowpass=f=10000,afftdn=nf=-40:nr=8:tn=1:gs=8,'
          'agate=threshold=0.004:ratio=1.5:range=0.5:attack=10:release=300:knee=4:detection=rms')

def profile():
    configured = os.environ.get('CCS_SPEECH_ENHANCER')
    enhancer = Path(configured) if configured else (BIN/'deep-filter.exe' if os.name == 'nt' else DATA_ROOT/'.tools/bin/deep-filter')
    if configured and not enhancer.is_file():
        raise ValueError('The configured speech enhancer is missing. Run its setup or correct CCS_SPEECH_ENHANCER.')
    result = {'version': VERSION, 'filter': FILTER, 'normalization': 'constant-gain-with-peak-limiter',
              'target_lufs': -20, 'maximum_gain_db': 18, 'limiter_peak_dbfs': -2,
              'method': 'ffmpeg-gentle-speech-cleanup'}
    if enhancer.is_file():
        with enhancer.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if not configured and digest != (WINDOWS_SHA256 if os.name == 'nt' else SHA256):
            raise ValueError('The speech enhancer checksum changed. Run python -m ccs.audio_setup to restore the verified tool.')
        result.update(method='deepfilternet3-and-gentle-speech-cleanup', enhancer=str(enhancer.resolve()),
                      enhancer_sha256=digest, attenuation_limit_db=20)
    return result

def normalization(measured, settings):
    loudness = float(measured['input_i'])
    peak = float(measured['input_tp'])
    if not math.isfinite(loudness) or not math.isfinite(peak):
        raise ValueError('Selected audio is silent or invalid; check the cut points.')
    gain = min(settings['maximum_gain_db'], settings['target_lufs']-loudness)
    # A constant gain cannot pump room noise. The limiter only turns excessive
    # peaks down, never turns quiet sections up. Compensate its lookahead latency.
    limit = 10**(settings['limiter_peak_dbfs']/20)
    return (f'volume={gain:.6f}dB,alimiter=limit={limit:.9f}:attack=5:release=80:level=false:latency=true',
            {'gain_db': gain, 'input_lufs': loudness, 'input_true_peak_db': peak,
             'target_lufs': settings['target_lufs'], 'normalization_type': 'constant',
             'gain_capped': gain < settings['target_lufs']-loudness})

def prepare(job, video, start, duration, mono, settings):
    """Cache enhanced audio separately; stamp only after all steps succeed."""
    key = {'profile': settings, 'source': str(video), 'source_size': video.stat().st_size,
           'source_modified': video.stat().st_mtime_ns, 'start': start, 'duration': duration, 'mono': mono}
    output = job/'cleaned-audio.wav'; marker = job/'audio-settings.json'
    if output.is_file() and marker.is_file() and read_json(marker).get('key') == key:
        return output, read_json(marker)['normalization_filter']
    work = job/'audio-work'; work.mkdir(exist_ok=True)
    raw = work/'source.wav'
    status(job, 'Cleaning audio', 'Extracting the checked voice channel', total_seconds=duration)
    before = min(.2, start); context_duration = duration+before+.15
    command([BIN/'ffmpeg', '-y', '-ss', str(start-before), '-i', video,
             '-map', '0:a:0', '-vn', '-af', mono+',apad=pad_dur=0.15', '-t', str(context_duration),
             '-ar', '48000', '-c:a', 'pcm_s16le', raw], job, 'audio-extract')
    enhanced = raw
    if settings.get('enhancer'):
        status(job, 'Enhancing voice', 'Reducing background noise locally; suppression is limited to protect speech', total_seconds=duration)
        model_out = work/'enhanced'; model_out.mkdir(exist_ok=True)
        for old in model_out.glob('*.wav'): old.unlink()
        command([settings['enhancer'], '-D', '-a', str(settings['attenuation_limit_db']), '-o', model_out, raw], job, 'speech-enhance')
        generated = list(model_out.glob('*.wav'))
        if len(generated) != 1:
            raise RuntimeError('Speech enhancement did not return exactly one audio file.')
        enhanced = generated[0]
    # afftdn has 25 ms of algorithmic delay at 48 kHz. Shift it out; fill the
    # trailing delay with silence so the voice stays in sync and duration is exact.
    filtering = settings['filter']+f',atrim=start={before+.025},asetpts=PTS-STARTPTS,apad'
    staged = job/'cleaned-audio.tmp.wav'
    command([BIN/'ffmpeg', '-y', '-i', enhanced, '-af', filtering, '-t', str(duration),
             '-ar', '48000', '-ac', '1', '-c:a', 'pcm_f32le', staged], job, 'audio-filter')
    status(job, 'Cleaning audio', 'Measuring speech for constant playback gain', total_seconds=duration)
    command([BIN/'ffmpeg', '-i', staged, '-af', 'loudnorm=I=-20:TP=-2:LRA=50:print_format=json',
             '-f', 'null', '-'], job, 'loudness-measure')
    text = (job/'loudness-measure.log').read_text(encoding='utf-8', errors='replace')
    found = re.findall(r'\{\s*"input_i".*?\}', text, re.S)
    if not found: raise RuntimeError('FFmpeg did not return loudness measurements.')
    measured = json.loads(found[-1]); norm, summary = normalization(measured, settings)
    staged.replace(output)
    write_json(job/'loudness.json', {**measured, 'playback': summary})
    write_json(marker, {'key': key, 'normalization_filter': norm, 'playback': summary,
                        'fft_delay_compensated_seconds': .025, 'enhancer_delay_compensated': True,
                        'method': settings['method']})
    shutil.rmtree(work)
    return output, norm
