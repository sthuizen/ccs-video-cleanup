import subprocess
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from ccs import startup


class LoginStartup(unittest.TestCase):
    @patch('ccs.startup.subprocess.run')
    def test_upgrade_clears_legacy_startup_once_and_preserves_opt_in(self, run):
        with tempfile.TemporaryDirectory() as directory:
            preference = Path(directory) / 'tools/startup.json'
            startup.initialize('ccs-video-cleanup.service', preference)
            self.assertEqual(run.call_args.args[0][2], 'disable')
            self.assertFalse(json.loads(preference.read_text())['enabled'])
            startup.set_enabled('ccs-video-cleanup.service', True, preference)
            run.reset_mock()
            startup.initialize('ccs-video-cleanup.service', preference)
            run.assert_not_called()
            self.assertTrue(json.loads(preference.read_text())['enabled'])

    @patch('ccs.startup.subprocess.run')
    def test_failed_opt_in_keeps_saved_preference(self, run):
        with tempfile.TemporaryDirectory() as directory:
            preference = Path(directory) / 'startup.json'
            preference.write_text('{"enabled": false}')
            run.side_effect = subprocess.CalledProcessError(1, ['systemctl'])
            with self.assertRaises(subprocess.CalledProcessError):
                startup.set_enabled('ccs-video-cleanup.service', True, preference)
            self.assertFalse(json.loads(preference.read_text())['enabled'])

    @patch('ccs.startup.subprocess.run')
    def test_preference_requires_both_services(self, run):
        run.side_effect = [subprocess.CompletedProcess([], 0, 'enabled\n'),
                           subprocess.CompletedProcess([], 1, 'disabled\n')]
        self.assertFalse(startup.enabled('ccs-video-cleanup.service'))
        self.assertEqual(run.call_args.args[0][-1], 'ccs-video-cleanup-tray.service')

    @patch('ccs.startup.subprocess.run')
    def test_switch_changes_both_units_without_stopping_work(self, run):
        for server in ('ccs-video-cleanup.service', 'ccs-video-cleanup-packaged.service'):
            for value, action in ((True, 'enable'), (False, 'disable')):
                startup.set_enabled(server, value)
                self.assertEqual(run.call_args.args[0],
                                 ['systemctl', '--user', action, *startup.units(server)])
                self.assertTrue(run.call_args.kwargs['check'])

    @patch('ccs.startup.subprocess.run')
    def test_failed_change_is_reported(self, run):
        run.side_effect = subprocess.CalledProcessError(1, ['systemctl'])
        with self.assertRaises(subprocess.CalledProcessError):
            startup.set_enabled('ccs-video-cleanup.service', True)
