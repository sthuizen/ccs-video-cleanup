import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class Registry:
    HKEY_CURRENT_USER = 'user'
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self):
        self.values = {}

    def OpenKey(self, hive, path):
        if hive != self.HKEY_CURRENT_USER:
            raise AssertionError('Startup must belong to the current user')
        self.path = path
        return self

    def CreateKeyEx(self, hive, path, reserved, access):
        return self.OpenKey(hive, path)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def QueryValueEx(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        return self.values[name]

    def SetValueEx(self, key, name, reserved, kind, value):
        self.values[name] = (value, kind)

    def DeleteValue(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        del self.values[name]


class WindowsStartup(unittest.TestCase):
    def setUp(self):
        self.registry = Registry()
        source = Path(__file__).resolve().parents[1] / 'packaging/windows/startup.py'
        spec = importlib.util.spec_from_file_location('windows_startup_test', source)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, winreg=self.registry):
            spec.loader.exec_module(self.module)

    def test_default_off_enable_disable_preserves_other_apps(self):
        self.registry.values['AnotherApp'] = ('unrelated', 1)
        self.assertFalse(self.module.enabled())
        self.module.set_enabled(True)
        self.assertTrue(self.module.enabled())
        self.assertEqual(self.registry.path, r'Software\Microsoft\Windows\CurrentVersion\Run')
        self.module.set_enabled(False)
        self.module.set_enabled(False)
        self.assertFalse(self.module.enabled())
        self.assertEqual(self.registry.values, {'AnotherApp': ('unrelated', 1)})

    def test_login_command_quotes_paths_and_does_not_open_browser(self):
        self.module.__file__ = '/test/My church/app/windows/startup.py'
        self.assertEqual(self.module.command(),
                         '"/test/My church/runtime/pythonw.exe" '
                         '"/test/My church/app/windows/launcher.py" --background')

    def test_stale_registration_is_not_shown_as_this_installation_enabled(self):
        self.registry.values[self.module.NAME] = ('old installation', 1)
        self.assertFalse(self.module.enabled())
