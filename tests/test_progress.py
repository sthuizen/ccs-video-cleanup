import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from ccs.common import status, read_json
from ccs.progress import snapshot

class Progress(unittest.TestCase):
    def test_updates_preserve_step_timer_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp)
            with patch('ccs.common.time.time',side_effect=[100,110,130]):
                status(job,'Transcribing','Starting',percent=0)
                status(job,'Transcribing','Continuing',percent=25)
                self.assertEqual(read_json(job/'status.json')['started_at'],100)
                status(job,'Reading slides','Starting')
            record=read_json(job/'status.json')
            self.assertEqual(record['steps'][0]['elapsed_seconds'],30)
            self.assertNotIn('percent',record)
            view=snapshot(job,record,now=140)
            self.assertEqual(view['elapsed_seconds'],10)
            self.assertEqual(view['total_elapsed_seconds'],40)

    def test_ffmpeg_percentage_and_eta(self):
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp); (job/'render.log').write_text('frame=500 time=00:00:25.00 speed=2.00x\n')
            view=snapshot(job,{'stage':'Rendering','started_at':100,'total_seconds':100,'log_file':'render.log'},now=120)
            self.assertEqual(view['percent'],25)
            self.assertEqual(view['eta_seconds'],38)

    def test_download_eta_is_current_file_not_whole_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp); (job/'download.log').write_text('[download]  25.0% of 100MiB at 1MiB/s ETA 01:15\n')
            view=snapshot(job,{'stage':'Downloading','started_at':100},now=125)
            self.assertEqual(view['percent'],25)
            self.assertEqual(view['eta_seconds'],75)
            self.assertEqual(view['progress_scope'],'Current download file')

    def test_unknown_work_has_no_invented_percentage(self):
        with tempfile.TemporaryDirectory() as tmp:
            view=snapshot(Path(tmp),{'stage':'Finding sermon','started_at':100},now=110)
            self.assertIsNone(view['percent']); self.assertIsNone(view['eta_seconds'])

    def test_waiting_timer_stops_and_error_does_not_complete_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp)
            with patch('ccs.common.time.time',side_effect=[100,110]):
                status(job,'Downloading','Starting')
                status(job,'Error','Failed')
            record=read_json(job/'status.json')
            self.assertFalse(record['steps'][0]['completed'])
            self.assertEqual(snapshot(job,record,now=1000)['elapsed_seconds'],0)
