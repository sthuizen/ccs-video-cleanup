"""Cross-process, non-blocking file locks for Linux and Windows."""
import errno
import os
from contextlib import contextmanager
from pathlib import Path

class LockBusy(Exception):
    pass

@contextmanager
def file_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            # Windows byte-range locks require a real byte and a consistent offset.
            if path.stat().st_size == 0:
                handle.write(b'0'); handle.flush()
            handle.seek(0)
            try: msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK): raise LockBusy() from exc
                raise
            try: yield
            finally:
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try: fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc: raise LockBusy() from exc
            try: yield
            finally: fcntl.flock(handle, fcntl.LOCK_UN)
