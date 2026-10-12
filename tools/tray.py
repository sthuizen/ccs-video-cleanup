#!/usr/bin/python3
"""Linux desktop controller, independent of browser windows."""
import ctypes
import ctypes.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
if os.environ.get('CCS_SERVER_SERVICE')=='ccs-video-cleanup-packaged.service':
    os.environ.setdefault('CCS_DATA_DIR',str(Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'ccs-video-cleanup'))
from ccs.common import DATA_ROOT, file_lock, LockBusy

SERVICE=os.environ.get('CCS_SERVER_SERVICE','ccs-video-cleanup.service')
STARTUP_PREFERENCE=DATA_ROOT/'.tools/login-startup.json'
URL='http://127.0.0.1:8765'

from ccs.tray_feedback import progress_feedback
from ccs import startup

def stop_server(force=False):
    """Idle stops take the media lock; systemd stops all server children."""
    from ccs.common import LOCK
    if force:
        subprocess.run(['systemctl','--user','stop',SERVICE],check=True,timeout=30)
    else:
        with file_lock(LOCK):
            subprocess.run(['systemctl','--user','stop',SERVICE],check=True,timeout=30)

class Controller:
    def __init__(self):
        import gi
        gi.require_version('Gtk','3.0')
        from gi.repository import Gtk,GLib
        self.Gtk,self.GLib=Gtk,GLib
        if not Gtk.init_check()[0]:raise RuntimeError('A desktop session is required for the tray.')
        self.stopping=False;self.checking=False;self.latest_busy=None
        # Use the installed Ayatana C library; no extra Python package is needed.
        self.lib=ctypes.CDLL(ctypes.util.find_library('ayatana-appindicator3'))
        functions={
            'app_indicator_new':([ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int],ctypes.c_void_p),
            'app_indicator_set_status':([ctypes.c_void_p,ctypes.c_int],None),
            'app_indicator_set_menu':([ctypes.c_void_p,ctypes.c_void_p],None),
            'app_indicator_set_title':([ctypes.c_void_p,ctypes.c_char_p],None),
            'app_indicator_set_label':([ctypes.c_void_p,ctypes.c_char_p,ctypes.c_char_p],None),
        }
        for name,(args,result) in functions.items():
            function=getattr(self.lib,name);function.argtypes=args;function.restype=result
        self.indicator=self.lib.app_indicator_new(b'ccs-video-cleanup',str(ROOT/'assets/ccs-tray.svg').encode(),0)
        self.lib.app_indicator_set_title(self.indicator,b'Christ Church Video Cleanup')
        self.menu=Gtk.Menu()
        self.status=Gtk.MenuItem(label='Checking service…');self.status.set_sensitive(False);self.menu.append(self.status)
        self.feedback={}
        for key in ('title','detail','timing'):
            item=Gtk.MenuItem(label='');item.set_sensitive(False);self.menu.append(item);self.feedback[key]=item
        self.menu.append(Gtk.SeparatorMenuItem())
        self.startup_item=Gtk.CheckMenuItem(label='Start automatically at login')
        try:
            startup.initialize(SERVICE,STARTUP_PREFERENCE)
            self.startup_item.set_active(startup.enabled(SERVICE))
        except (OSError,subprocess.SubprocessError):
            self.startup_item.set_sensitive(False)
            self.startup_item.set_tooltip_text('Login startup requires installed systemd user services.')
        self.startup_item.connect('toggled',self.toggle_startup)
        self.menu.append(self.startup_item)
        for title,handler in [('Open Christ Church Video Cleanup',self.open_app),('Quit and stop services',self.quit)]:
            item=Gtk.MenuItem(label=title);item.connect('activate',handler);self.menu.append(item)
        self.menu.show_all()
        capsule=ctypes.pythonapi.PyCapsule_GetPointer
        capsule.argtypes=[ctypes.py_object,ctypes.c_char_p];capsule.restype=ctypes.c_void_p
        self.lib.app_indicator_set_menu(self.indicator,capsule(self.menu.__gpointer__,None))
        self.lib.app_indicator_set_status(self.indicator,1)
        GLib.timeout_add_seconds(4,self.poll);self.poll()
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGTERM,self.signal_quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGINT,self.signal_quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGHUP,self.reload)

    def reload(self):
        # Replace only the tray process, leaving the server and workers running.
        os.execv(sys.executable,[sys.executable,str(Path(__file__).resolve())])

    def poll(self):
        if self.checking or self.stopping:return True
        self.checking=True
        def fetch():
            try:
                rows=json.load(urllib.request.urlopen(URL+'/api/jobs',timeout=2))
                selection=json.load(urllib.request.urlopen(URL+'/api/selection',timeout=2))
                busy=any(r.get('audio_busy') for r in rows)
                feedback=progress_feedback(rows,selection.get('id'))
            except Exception:busy=None;feedback=dict(task='Status unavailable · open app to check',title='',detail='',timing='',badge='')
            def update():
                self.checking=False;self.latest_busy=busy;self.status.set_label(feedback['task'])
                for key,item in self.feedback.items():
                    item.set_label(feedback[key] or '');item.set_visible(bool(feedback[key]))
                self.lib.app_indicator_set_label(self.indicator,feedback['badge'].encode(),b'100%')
                self.lib.app_indicator_set_title(self.indicator,('Christ Church Video Cleanup · '+feedback['task']).encode())
                return False
            self.GLib.idle_add(update)
        threading.Thread(target=fetch,daemon=True).start();return True

    def open_app(self,*args):
        command=os.environ.get('CCS_TRAY_OPEN')
        subprocess.Popen([command,'--open'] if command else [str(ROOT/'open-cleanup')],cwd=ROOT)

    def toggle_startup(self,item):
        item.set_sensitive(False)
        value=item.get_active()
        def work():
            error=None
            try:startup.set_enabled(SERVICE,value,STARTUP_PREFERENCE)
            except Exception as exc:error=str(exc)
            actual=startup.enabled(SERVICE)
            def update():
                item.handler_block_by_func(self.toggle_startup)
                item.set_active(actual)
                item.handler_unblock_by_func(self.toggle_startup)
                item.set_sensitive(True)
                if error:self.message('Could not change login startup',error)
                return False
            self.GLib.idle_add(update)
        threading.Thread(target=work,daemon=True).start()

    def message(self,title,text,question=False):
        Gtk=self.Gtk
        dialog=Gtk.MessageDialog(message_type=Gtk.MessageType.QUESTION if question else Gtk.MessageType.ERROR,
                                 buttons=Gtk.ButtonsType.NONE,text=title)
        dialog.format_secondary_text(text)
        if question:
            dialog.add_button('Keep processing',Gtk.ResponseType.CANCEL)
            dialog.add_button('Stop services and quit',Gtk.ResponseType.OK)
            dialog.set_default_response(Gtk.ResponseType.CANCEL)
        else:dialog.add_button('Close',Gtk.ResponseType.CLOSE)
        response=dialog.run();dialog.destroy();return response==Gtk.ResponseType.OK

    def quit(self,*args):
        if self.stopping:return
        from ccs.common import busy
        force=False
        if busy():
            if not self.message('A video is still processing',
                'Stopping now interrupts the current job. The source and saved analysis remain, but unfinished output may need to be recreated.',True):return
            force=True
        self.shutdown(force)

    def shutdown(self,force=False):
        self.stopping=True;self.status.set_label('Stopping services…')
        def work():
            try:stop_server(force)
            except Exception as exc:
                message=str(exc)
                def failed():
                    self.stopping=False;self.message('Could not stop services',message);return False
                self.GLib.idle_add(failed);return
            self.GLib.idle_add(self.Gtk.main_quit)
        threading.Thread(target=work,daemon=True).start()

    def signal_quit(self):
        # A systemd stop of the tray also stops the server and its subprocesses.
        self.shutdown(True);return False

def main():
    try:
        with file_lock(DATA_ROOT/'.tools/tray.lock'):
            app=Controller();app.Gtk.main()
    except LockBusy:pass

if __name__=='__main__':main()
