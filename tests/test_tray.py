import importlib.util
from pathlib import Path
import unittest

from ccs import tray_feedback as tray

class TrayProgress(unittest.TestCase):
    def test_download_percentage_scope_and_eta(self):
        row=dict(id='video',plan=None,status=dict(stage='Downloading',active=True,percent=42.9,elapsed_seconds=75,eta_seconds=180,detail='Downloading video'))
        feedback=tray.progress_feedback([row],'video')
        self.assertEqual(feedback['badge'],'42%')
        self.assertIn('current file',feedback['task'])
        self.assertIn('1m 15s elapsed',feedback['timing'])
        self.assertIn('3m 0s remaining',feedback['timing'])

    def test_active_job_wins_and_unknown_progress_is_honest(self):
        done=dict(id='done',status=dict(stage='Finished',active=False))
        active=dict(id='active',status=dict(stage='Preparing audio tests',active=True,percent=None,elapsed_seconds=10))
        feedback=tray.progress_feedback([done,active])
        self.assertEqual(feedback['title'],'active')
        self.assertEqual(feedback['badge'],'Working')
        self.assertIn('estimating',feedback['timing'])

    def test_waiting_for_review_and_finished_feedback(self):
        row=dict(id='video',plan=dict(title='Sermon'),status=dict(stage='Needs information',active=False,detail='Supply the clip'))
        feedback=tray.progress_feedback([row],'video')
        self.assertEqual(feedback['badge'],'Review');self.assertEqual(feedback['timing'],'Waiting for your input')
        row['status']=dict(stage='Finished',active=False,detail='/internal/finished.mp4',percent=100)
        feedback=tray.progress_feedback([row],'video');self.assertEqual(feedback['detail'],'Selected exports ready');self.assertEqual(feedback['badge'],'')

    def test_fresh_launch_ignores_saved_waiting_jobs(self):
        rows=[dict(id='old',status=dict(stage='Needs information',active=False))]
        feedback=tray.progress_feedback(rows)
        self.assertEqual(feedback['task'],'Ready')
        self.assertEqual(feedback['badge'],'')
        self.assertEqual(feedback['title'],'No service selected')
        self.assertEqual(tray.progress_feedback(rows,'missing')['task'],'Ready')
        self.assertEqual(tray.progress_feedback(rows,'old')['badge'],'Review')

    def test_background_work_wins_over_selected_saved_service(self):
        rows=[dict(id='old',status=dict(stage='Needs information',active=False)),
              dict(id='new',status=dict(stage='Downloading',active=True,percent=20))]
        self.assertEqual(tray.progress_feedback(rows,'old')['badge'],'20%')
