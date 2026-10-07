"""Signal-level checks for constant gain, soft suppression and cached audio."""
from pathlib import Path
import subprocess
import os
import tempfile
import unittest
from unittest.mock import patch
import wave

import numpy as np

from ccs import audio
from ccs.common import BIN


@unittest.skipUnless((BIN/('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')).is_file(), 'Local FFmpeg is required')
class AudioSignalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rate = 48000

    def tearDown(self):
        self.tmp.cleanup()

    def wav(self, name, samples):
        path = self.root/name
        with wave.open(str(path), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(self.rate)
            stream.writeframes((np.clip(samples, -1, 1)*32767).astype('<i2').tobytes())
        return path

    def read(self, path):
        # FFmpeg emits floating PCM for the cache; decode either format equally.
        raw = subprocess.check_output([str(BIN/'ffmpeg'), '-v', 'error', '-i', str(path),
                                       '-f', 'f32le', '-ar', str(self.rate), '-ac', '1', '-'])
        return np.frombuffer(raw, '<f4')

    def apply(self, path, filters, name='result.wav'):
        result = self.root/name
        subprocess.run([str(BIN/'ffmpeg'), '-v', 'error', '-y', '-i', str(path),
                        '-af', filters, '-c:a', 'pcm_f32le', str(result)], check=True)
        return self.read(result)

    def settings(self):
        return {'version': audio.VERSION, 'filter': audio.FILTER,
                'normalization': 'constant-gain-with-peak-limiter', 'target_lufs': -20,
                'maximum_gain_db': 18, 'limiter_peak_dbfs': -2,
                'method': 'ffmpeg-gentle-speech-cleanup'}

    def test_constant_gain_does_not_raise_pauses_relative_to_voice(self):
        t = np.arange(self.rate*3)/self.rate
        samples = .001*np.sin(2*np.pi*330*t)
        speech = (t >= 1) & (t < 2)
        samples[speech] += .03*np.sin(2*np.pi*180*t[speech])
        # A large brief noise transient must activate limiting without automatic
        # makeup turning up either distant pause when it has passed.
        samples[(t >= 1.75) & (t < 1.76)] += .85
        source = self.wav('source.wav', samples)
        original = self.read(source)
        filters, report = audio.normalization({'input_i': '-38', 'input_tp': '-0.5'}, self.settings())
        processed = self.apply(source, filters)
        self.assertEqual(len(processed), len(original))
        self.assertEqual(report['normalization_type'], 'constant')
        self.assertLessEqual(np.max(np.abs(processed)), 10**(-2/20)+.001)
        expected_gain = 10**(18/20)
        for start, end in ((.3, .6), (1.1, 1.4), (2.3, 2.6)):
            sl = slice(int(start*self.rate), int(end*self.rate))
            actual = np.sqrt(np.mean(processed[sl]**2)/np.mean(original[sl]**2))
            self.assertAlmostEqual(actual/expected_gain, 1, delta=.02)
        self.assertLess(abs(int(np.argmax(processed))-int(np.argmax(original))), self.rate*.002)

    def test_gain_is_capped_and_silence_is_rejected(self):
        _, report = audio.normalization({'input_i': '-65', 'input_tp': '-10'}, self.settings())
        self.assertEqual(report['gain_db'], 18)
        self.assertTrue(report['gain_capped'])
        for loudness, peak in (('-inf', '-inf'), ('nan', '-10'), ('-30', 'inf')):
            with self.assertRaisesRegex(ValueError, 'silent or invalid'):
                audio.normalization({'input_i': loudness, 'input_tp': peak}, self.settings())
        _, report = audio.normalization({'input_i': '-12', 'input_tp': '-1'}, self.settings())
        self.assertEqual(report['gain_db'], -8)

    def test_soft_speech_and_end_of_cut_are_preserved(self):
        # Continuous low voice harmonics beyond the chosen cut give the FFT
        # filter legitimate tail context; replacing the final 25 ms with silence
        # would visibly truncate this signal.
        t = np.arange(int(self.rate*1.3))/self.rate
        samples = .012*np.sin(2*np.pi*180*t) + .004*np.sin(2*np.pi*540*t)
        source = self.wav('quiet-voice.wav', samples)
        job = self.root/'job'; job.mkdir()
        output, _ = audio.prepare(job, source, 0, 1, 'aformat=channel_layouts=mono', self.settings())
        processed = self.read(output)
        self.assertEqual(len(processed), self.rate)
        interior = np.sqrt(np.mean(processed[int(.4*self.rate):int(.8*self.rate)]**2))
        tail = np.sqrt(np.mean(processed[int(.99*self.rate):]**2))
        self.assertGreater(interior, .002, 'Quiet voice should not be gated to silence')
        self.assertGreater(tail/interior, .5, 'End syllables must retain FFT tail context')
        marker = (job/'audio-settings.json').stat().st_mtime_ns
        cached, _ = audio.prepare(job, source, 0, 1, 'aformat=channel_layouts=mono', self.settings())
        self.assertEqual(cached, output)
        self.assertEqual((job/'audio-settings.json').stat().st_mtime_ns, marker)

    def test_filtered_voice_envelope_has_no_remaining_fft_delay(self):
        t = np.arange(self.rate*2)/self.rate
        envelope = np.zeros_like(t)
        for lo, hi in ((.35, .55), (.80, .98), (1.2, 1.5)):
            envelope[(t >= lo) & (t < hi)] = 1
        samples = envelope*(.04*np.sin(2*np.pi*180*t)+.012*np.sin(2*np.pi*540*t))
        source = self.wav('bursts.wav', samples)
        job = self.root/'aligned'; job.mkdir()
        output, _ = audio.prepare(job, source, .2, 1.6, 'aformat=channel_layouts=mono', self.settings())
        actual = self.read(output)
        reference = self.read(source)[int(.2*self.rate):int(1.8*self.rate)]
        frame = 240  # Five-ms RMS envelope avoids frequency-response phase shifts.
        a = np.sqrt(np.mean(actual.reshape(-1, frame)**2, axis=1))
        b = np.sqrt(np.mean(reference.reshape(-1, frame)**2, axis=1))
        correlation = np.correlate(a, b, mode='full')
        lag = int(np.argmax(correlation))-(len(b)-1)
        self.assertLessEqual(abs(lag), 2, 'The 25-ms FFT delay must be compensated')

    def test_failed_prepare_cannot_stamp_success_or_replace_cache(self):
        source = self.wav('source.wav', np.ones(self.rate)*.01)
        job = self.root/'job'; job.mkdir()
        existing = job/'cleaned-audio.wav'; existing.write_bytes(b'old completed cache')
        with patch.object(audio, 'command', side_effect=RuntimeError('simulated failed decoder')):
            with self.assertRaisesRegex(RuntimeError, 'failed decoder'):
                audio.prepare(job, source, 0, 1, 'aformat=channel_layouts=mono', self.settings())
        self.assertFalse((job/'audio-settings.json').exists())
        self.assertEqual(existing.read_bytes(), b'old completed cache')

    def test_default_enhancer_integrity_failure_is_detected_before_execution(self):
        directory = self.root/'.tools/bin'; directory.mkdir(parents=True)
        (directory/('deep-filter.exe' if os.name == 'nt' else 'deep-filter')).write_bytes(b'changed executable')
        with patch.object(audio, 'DATA_ROOT', self.root), patch.object(audio, 'BIN', directory), patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'checksum changed'):
                audio.profile()

    def test_installed_model_stays_local_and_returns_exact_duration(self):
        settings = audio.profile()
        if not settings.get('enhancer'):
            self.skipTest('Verified optional speech enhancer is not installed')
        t = np.arange(int(self.rate*1.4))/self.rate
        envelope = .7+.3*np.sin(2*np.pi*3*t)
        samples = envelope*(.04*np.sin(2*np.pi*180*t)+.02*np.sin(2*np.pi*540*t))
        source = self.wav('voice.wav', samples)
        job = self.root/'neural'; job.mkdir()
        with patch('urllib.request.urlopen', side_effect=AssertionError('No network during enhancement')):
            output, _ = audio.prepare(job, source, 0, 1, 'aformat=channel_layouts=mono', settings)
        processed = self.read(output)
        self.assertEqual(len(processed), self.rate)
        self.assertTrue(np.isfinite(processed).all())
        self.assertGreater(np.sqrt(np.mean(processed[-480:]**2)), .00001,
                           'Model/FFT tail context must not be replaced with hard silence')
        self.assertFalse((job/'audio-work').exists())


if __name__ == '__main__':
    unittest.main()
