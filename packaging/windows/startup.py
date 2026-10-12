"""Opt-in Windows login startup for the current user only."""
import argparse
from pathlib import Path
import winreg

KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME = 'CCSVideoCleanup'


def command():
    install = Path(__file__).resolve().parents[2]
    # Match the installer's path refresh, including paths without spaces.
    return f'"{install / "runtime/pythonw.exe"}" "{install / "app/windows/launcher.py"}" --background'


def enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as key:
            value, kind = winreg.QueryValueEx(key, NAME)
            return kind == winreg.REG_SZ and value == command()
    except FileNotFoundError:
        return False


def set_enabled(value):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as key:
        if value:
            winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, command())
        else:
            try:
                winreg.DeleteValue(key, NAME)
            except FileNotFoundError:
                pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'enable', 'disable'))
    args = parser.parse_args()
    if args.action == 'status':
        print('enabled' if enabled() else 'disabled')
    else:
        set_enabled(args.action == 'enable')
