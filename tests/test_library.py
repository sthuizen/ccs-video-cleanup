import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ccs import library
from ccs.common import write_json

class Library(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.jobs=self.root/'jobs';self.jobs.mkdir()
        self.patches=[patch('ccs.library.JOBS',self.jobs),patch('ccs.common.LOCK',self.root/'lock')]
        for p in self.patches:p.start()
        library._tickets.clear()

    def tearDown(self):
        for p in self.patches:p.stop()
        self.temp.cleanup()

    def job(self,name,finished=True):
        job=self.jobs/name;job.mkdir();write_json(job/'plan.json',dict(title='Sermon '+name,date='2026-10-11'))
        (job/'source.mp4').write_bytes(b'source');(job/'audio-trials').mkdir();(job/'audio-trials'/'sample.m4a').write_bytes(b'sample')
        if finished:
            (job/'finished.mp4').write_bytes(b'video');write_json(job/'validation.json',dict(full_decode='passed'))
        return job

    def test_two_checks_token_is_single_use_and_original_external_file_survives(self):
        job=self.job('one');outside=self.root/'original.mp4';outside.write_bytes(b'original')
        write_json(job/'source-path.json',dict(path=str(outside)))
        review=library.preview('one')
        with patch('ccs.library.trash',side_effect=lambda p:p.rename(self.root/'trashed')) as trash:
            for phrase,ack in [('DELETE',False),('wrong',True)]:
                with self.assertRaises(ValueError):library.delete(review['token'],phrase,ack)
            trash.assert_not_called()
            self.assertEqual(library.delete(review['token'],'DELETE',True)['deleted'],['one'])
            with self.assertRaises(ValueError):library.delete(review['token'],'DELETE',True)
        self.assertEqual(outside.read_bytes(),b'original');self.assertFalse(job.exists());self.assertTrue((self.root/'trashed'/'audio-trials'/'sample.m4a').exists())

    def test_master_requires_exact_reviewed_set(self):
        self.job('one');self.job('unfinished',False);review=library.preview(all_services=True)
        self.assertEqual(review['phrase'],'DELETE ALL');self.assertEqual(len(review['jobs']),2)
        self.job('added')
        with patch('ccs.library.trash') as trash:
            with self.assertRaises(ValueError):library.delete(review['token'],'DELETE ALL',True)
            trash.assert_not_called()

    def test_modified_media_expired_and_invalid_paths_are_rejected(self):
        job=self.job('one');review=library.preview('one');(job/'source.mp4').write_bytes(b'new source')
        with patch('ccs.library.trash') as trash:
            with self.assertRaises(ValueError):library.delete(review['token'],'DELETE',True)
            library._tickets[review['token']]['expires']=0
            with self.assertRaises(ValueError):library.delete(review['token'],'DELETE',True)
            trash.assert_not_called()
        for name in ['../one','..','/tmp','missing']:
            with self.assertRaises(ValueError):library.preview(name)

    def test_symlink_jobs_are_rejected(self):
        job=self.job('one')
        try:
            (self.jobs/'link').symlink_to(job, target_is_directory=True)
        except OSError as error:
            if getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows account does not have symlink privilege')
            raise
        with self.assertRaises(ValueError):library.preview('link')

    def test_active_pipeline_and_unfinished_single_delete_are_blocked(self):
        self.job('unfinished',False)
        with self.assertRaises(ValueError):library.preview('unfinished')
        with patch('ccs.library.busy',return_value=True):
            with self.assertRaises(ValueError):library.preview(all_services=True)
        self.job('one');review=library.preview('one')
        from ccs.locking import file_lock
        with file_lock(self.root/'lock'),patch('ccs.library.trash') as trash:
            with self.assertRaises(ValueError):library.delete(review['token'],'DELETE',True)
            trash.assert_not_called()
