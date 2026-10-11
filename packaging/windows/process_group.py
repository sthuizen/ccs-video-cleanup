"""Keep server descendants in a Windows job so exiting also stops media tools."""
import ctypes
from ctypes import wintypes as W

class Basic(ctypes.Structure):
    _fields_=[('PerProcessUserTimeLimit',ctypes.c_int64),('PerJobUserTimeLimit',ctypes.c_int64),
              ('LimitFlags',W.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),
              ('ActiveProcessLimit',W.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',W.DWORD),('SchedulingClass',W.DWORD)]
class IO(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint64) for name in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
class Extended(ctypes.Structure):
    _fields_=[('BasicLimitInformation',Basic),('IoInfo',IO)]+[(name,ctypes.c_size_t) for name in ('ProcessMemoryLimit','JobMemoryLimit','PeakProcessMemoryUsed','PeakJobMemoryUsed')]

class ProcessGroup:
    def __init__(self):
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,W.LPCWSTR];kernel.CreateJobObjectW.restype=W.HANDLE
        kernel.SetInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD];kernel.SetInformationJobObject.restype=W.BOOL
        kernel.GetCurrentProcess.restype=W.HANDLE
        kernel.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE];kernel.AssignProcessToJobObject.restype=W.BOOL
        kernel.CloseHandle.argtypes=[W.HANDLE]
        self.handle=kernel.CreateJobObjectW(None,None)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        limits=Extended();limits.BasicLimitInformation.LimitFlags=0x2000
        if not kernel.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(self.handle,kernel.GetCurrentProcess()):
            error=ctypes.get_last_error();kernel.CloseHandle(self.handle);raise ctypes.WinError(error)
        # Deliberately retain the handle until process exit. Closing it manually
        # would also terminate this server, which belongs to the job.
