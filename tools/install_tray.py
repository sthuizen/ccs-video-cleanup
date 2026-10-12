"""Install the Linux tray controller for this source checkout."""
import os
from pathlib import Path
import subprocess

def install():
    if os.name!='posix':raise SystemExit('This tray installer is for Linux desktops.')
    root=Path(__file__).resolve().parent.parent
    units=Path.home()/'.config/systemd/user';units.mkdir(parents=True,exist_ok=True)
    (units/'ccs-video-cleanup-tray.service').write_text(f'''[Unit]
Description=Christ Church Video Cleanup desktop tray
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
WorkingDirectory={root}
ExecStart=/usr/bin/python3 "{root}/tools/tray.py"
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=3
TimeoutStopSec=40

[Install]
WantedBy=default.target
''')
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    # Installation starts the tray now without opting the user into login startup.
    subprocess.run(['systemctl','--user','start','ccs-video-cleanup-tray.service'],check=True)

if __name__=='__main__':install()
