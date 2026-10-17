"""Supervise application-owned workers with bounded output and whole-tree cleanup.

Windows atomically creates the suspended worker in a non-breakaway kill-on-close
Job Object with PROC_THREAD_ATTRIBUTE_JOB_LIST, then resumes its initial thread.
No caller-controlled code is accepted
by the HTTP layer; this low-level API receives trusted arguments from the app.

Win32 contracts: https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
https://learn.microsoft.com/en-us/windows/win32/toolhelp/snapshots-of-the-system
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute
"""
from __future__ import annotations

import atexit
import codecs
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import psutil

LOG_LIMIT = 256 * 1024
TAIL_LIMIT = 64 * 1024
EVENT_LINE_LIMIT = 16 * 1024


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    cancelled: bool
    timed_out: bool
    elapsed_seconds: float
    peak_rss_bytes: int
    log_tail: str


class ProcessContainmentError(RuntimeError):
    """The owned tree could not be safely contained or confirmed stopped."""


if sys.platform == "win32":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    SIZE_T = ctypes.c_size_t
    ULONG_PTR = ctypes.c_size_t
    LONGLONG = ctypes.c_longlong

    class _BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", LONGLONG), ("PerJobUserTimeLimit", LONGLONG),
            ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", SIZE_T),
            ("MaximumWorkingSetSize", SIZE_T), ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ULONG_PTR), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class _IOCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", _BasicLimits), ("IoInfo", _IOCounters),
            ("ProcessMemoryLimit", SIZE_T), ("JobMemoryLimit", SIZE_T),
            ("PeakProcessMemoryUsed", SIZE_T), ("PeakJobMemoryUsed", SIZE_T)]

    class _BasicAccounting(ctypes.Structure):
        _fields_ = [("TotalUserTime", LONGLONG), ("TotalKernelTime", LONGLONG),
            ("ThisPeriodTotalUserTime", LONGLONG), ("ThisPeriodTotalKernelTime", LONGLONG),
            ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
            ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD)]

    class _StartupInfo(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

    class _StartupInfoEx(ctypes.Structure):
        _fields_ = [("StartupInfo", _StartupInfo), ("lpAttributeList", ctypes.c_void_p)]

    class _ProcessInformation(ctypes.Structure):
        _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                   ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

    class _ProcessIdList(ctypes.Structure):
        _fields_ = [("NumberOfAssignedProcesses", wintypes.DWORD), ("NumberOfProcessIdsInList", wintypes.DWORD),
                   ("ProcessIdList", ULONG_PTR * 1024)]

    _kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    _SIGNATURES = {
        "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
        "SetInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
        "QueryInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
        "IsProcessInJob": ([wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)], wintypes.BOOL),
        "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        "ResumeThread": ([wintypes.HANDLE], wintypes.DWORD),
        "InitializeProcThreadAttributeList": ([ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(SIZE_T)], wintypes.BOOL),
        "UpdateProcThreadAttribute": ([ctypes.c_void_p, wintypes.DWORD, ULONG_PTR, ctypes.c_void_p, SIZE_T, ctypes.c_void_p, ctypes.c_void_p], wintypes.BOOL),
        "DeleteProcThreadAttributeList": ([ctypes.c_void_p], None),
        "CreateProcessW": ([wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(_StartupInfoEx), ctypes.POINTER(_ProcessInformation)], wintypes.BOOL),
        "WaitForSingleObject": ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
        "GetExitCodeProcess": ([wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
        "TerminateProcess": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
    }
    for _name, (_argtypes, _restype) in _SIGNATURES.items():
        getattr(_kernel, _name).argtypes = _argtypes
        getattr(_kernel, _name).restype = _restype


class _WindowsProcess:
    """Small documented Win32 process/pipe interface; membership exists at birth."""
    def __init__(self, args, *, cwd, env, job):
        self.args = [os.fspath(argument) for argument in args]
        self.returncode = None
        self.handle = self.thread_handle = None
        read_fd, write_fd = os.pipe()
        attributes = None
        information = _ProcessInformation()
        try:
            with open(os.devnull, "rb", buffering=0) as stdin:
                output_handle = msvcrt.get_osfhandle(write_fd)
                input_handle = msvcrt.get_osfhandle(stdin.fileno())
                os.set_handle_inheritable(output_handle, True)
                os.set_handle_inheritable(input_handle, True)
                size = SIZE_T()
                # The sizing call deliberately fails with the required buffer size.
                _kernel.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
                if not size.value:
                    raise ctypes.WinError(ctypes.get_last_error())
                attribute_buffer = ctypes.create_string_buffer(size.value)
                attributes = ctypes.cast(attribute_buffer, ctypes.c_void_p)
                if not _kernel.InitializeProcThreadAttributeList(attributes, 2, 0, ctypes.byref(size)):
                    attributes = None
                    raise ctypes.WinError(ctypes.get_last_error())
                jobs = (wintypes.HANDLE * 1)(job.handle)
                handles = (wintypes.HANDLE * 2)(output_handle, input_handle)
                for key, value in ((0x0002000D, jobs), (0x00020002, handles)):
                    if not _kernel.UpdateProcThreadAttribute(attributes, 0, key, ctypes.byref(value), ctypes.sizeof(value), None, None):
                        raise ctypes.WinError(ctypes.get_last_error())
                startup = _StartupInfoEx()
                startup.StartupInfo.cb = ctypes.sizeof(startup)
                startup.StartupInfo.dwFlags = 0x00000100  # STARTF_USESTDHANDLES
                startup.StartupInfo.hStdInput = input_handle
                startup.StartupInfo.hStdOutput = output_handle
                startup.StartupInfo.hStdError = output_handle
                startup.lpAttributeList = attributes
                command = ctypes.create_unicode_buffer(subprocess.list2cmdline(self.args))
                entries = []
                for key, value in sorted(env.items(), key=lambda item: item[0].casefold()):
                    if not isinstance(key, str) or not isinstance(value, str) or "\0" in key+value or "=" in key:
                        raise ValueError("Invalid trusted worker environment.")
                    entries.append(key + "=" + value)
                environment = ctypes.create_unicode_buffer("\0".join(entries) + "\0\0")
                flags = 0x00000004 | 0x08000000 | 0x00080000 | 0x00000400
                # CREATE_SUSPENDED | CREATE_NO_WINDOW | EXTENDED_STARTUPINFO_PRESENT
                # | CREATE_UNICODE_ENVIRONMENT. Unsupported atomic Job assignment fails closed.
                if not _kernel.CreateProcessW(self.args[0], command, None, None, True, flags,
                    environment, os.fspath(cwd), ctypes.byref(startup), ctypes.byref(information)):
                    raise ctypes.WinError(ctypes.get_last_error())
                self.handle, self.thread_handle = information.hProcess, information.hThread
                self.pid = information.dwProcessId
                self.stdout = os.fdopen(read_fd, "rb", buffering=0)
                read_fd = None
        except BaseException:
            self.close()
            raise
        finally:
            if attributes is not None:
                _kernel.DeleteProcThreadAttributeList(attributes)
            os.close(write_fd)
            if read_fd is not None:
                os.close(read_fd)

    def resume(self):
        previous = _kernel.ResumeThread(self.thread_handle)
        if previous == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        if previous != 1:
            raise ProcessContainmentError("Initial worker thread was not suspended exactly once.")
        _kernel.CloseHandle(self.thread_handle)
        self.thread_handle = None

    def poll(self):
        if self.returncode is not None:
            return self.returncode
        state = _kernel.WaitForSingleObject(self.handle, 0)
        if state == 258:  # WAIT_TIMEOUT
            return None
        if state != 0:  # WAIT_OBJECT_0
            raise ctypes.WinError(ctypes.get_last_error())
        code = wintypes.DWORD()
        if not _kernel.GetExitCodeProcess(self.handle, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.returncode = code.value
        return self.returncode

    def wait(self, timeout=None):
        duration = 0xFFFFFFFF if timeout is None else min(math.ceil(timeout*1000), 0xFFFFFFFE)
        state = _kernel.WaitForSingleObject(self.handle, duration)
        if state == 258:
            raise subprocess.TimeoutExpired(self.args, timeout)
        if state != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        return self.poll()

    def kill(self):
        if self.poll() is None and not _kernel.TerminateProcess(self.handle, 1) and self.poll() is None:
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        for name in ("thread_handle", "handle"):
            handle = getattr(self, name, None)
            if handle:
                _kernel.CloseHandle(handle)
                setattr(self, name, None)


class _WindowsJob:
    def __init__(self):
        self.lock = threading.RLock()
        self.handle = _kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = _ExtendedLimits()
        # No BREAKAWAY_OK or SILENT_BREAKAWAY_OK; descendants inherit this job.
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not _kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.get_last_error()
            self.close()
            raise ctypes.WinError(error)

    def assign_and_resume(self, process):
        contained = wintypes.BOOL()
        if not _kernel.IsProcessInJob(process.handle, self.handle, ctypes.byref(contained)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not contained:
            raise ProcessContainmentError("Worker lacks its atomic Job Object membership.")
        process.resume()

    def active_count(self):
        with self.lock:
            if not self.handle:
                return 0
            info = _BasicAccounting()
            if not _kernel.QueryInformationJobObject(self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None):
                raise ctypes.WinError(ctypes.get_last_error())
            return info.ActiveProcesses

    def pids(self):
        with self.lock:
            if not self.handle:
                return []
            info = _ProcessIdList()
            if not _kernel.QueryInformationJobObject(self.handle, 3, ctypes.byref(info), ctypes.sizeof(info), None):
                raise ctypes.WinError(ctypes.get_last_error())
            return list(info.ProcessIdList[:info.NumberOfProcessIdsInList])

    def terminate(self):
        with self.lock:
            if self.handle and not _kernel.TerminateJobObject(self.handle, 1):
                raise ctypes.WinError(ctypes.get_last_error())

    def confirm_stopped(self):
        deadline = time.monotonic() + 4
        while self.active_count():
            if time.monotonic() >= deadline:
                raise ProcessContainmentError("Owned Windows Job Object still has active processes after termination.")
            time.sleep(0.01)

    def close(self):
        with self.lock:
            if self.handle:
                _kernel.CloseHandle(self.handle)
                self.handle = None


class _PosixGroup:
    def __init__(self, process):
        self.process = process
        self.pgid = process.pid

    def pids(self):
        return [p.pid for p in psutil.process_iter() if self._in_group(p.pid)]

    def _in_group(self, pid):
        try:
            return os.getpgid(pid) == self.pgid
        except ProcessLookupError:
            return False

    def terminate(self):
        try:
            os.killpg(self.pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def confirm_stopped(self):
        deadline = time.monotonic() + 4
        while True:
            active = []
            for pid in self.pids():
                try:
                    if psutil.Process(pid).status() != psutil.STATUS_ZOMBIE:
                        active.append(pid)
                except psutil.NoSuchProcess:
                    pass
            if not active:
                return
            if time.monotonic() >= deadline:
                raise ProcessContainmentError("Owned process group still has active processes after termination.")
            time.sleep(0.01)

    def close(self):
        pass


class _SecretRedactor:
    """Streaming prefix matching prevents a secret split across reads from leaking."""
    def __init__(self, env):
        self.secrets = sorted({str(value) for name, value in env.items()
            if any(token in name.upper() for token in ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")) and len(str(value)) >= 4}, key=len, reverse=True)
        self.prefixes = {secret[:i] for secret in self.secrets for i in range(1, len(secret)+1)}
        self.pending = ""

    def feed(self, text, final=False):
        if not self.secrets:
            return text
        output = []
        for character in text:
            self.pending += character
            while self.pending and self.pending not in self.prefixes:
                output.append(self.pending[0])
                self.pending = self.pending[1:]
            if self.pending in self.secrets:
                output.append("[REDACTED]")
                self.pending = ""
        if final and self.pending:
            output.append(self.pending)
            self.pending = ""
        return "".join(output)


class _OutputDrain:
    def __init__(self, process, path, env, callback):
        self.process, self.path, self.callback = process, path, callback
        self.buffer = bytearray()
        self.pending_line = ""
        self.discard_line = False
        self.redactor = _SecretRedactor(env)
        self.error = None
        self.next_flush = 0.0
        self.thread = threading.Thread(target=self._read, name="woodwork-output-drain", daemon=True)

    def start(self):
        self.thread.start()

    def _append(self, text):
        self.buffer.extend(text.encode("utf-8"))
        if len(self.buffer) > LOG_LIMIT:
            del self.buffer[:-LOG_LIMIT]
        for character in text:
            if character == "\n":
                if not self.discard_line and self.callback:
                    try:
                        event = json.loads(self.pending_line)
                    except (ValueError, TypeError):
                        event = None
                    if isinstance(event, dict) and isinstance(event.get("stage"), str):
                        self.callback(event)
                self.pending_line = ""
                self.discard_line = False
            elif not self.discard_line:
                self.pending_line += character
                if len(self.pending_line) > EVENT_LINE_LIMIT:
                    self.pending_line = ""
                    self.discard_line = True
        if time.monotonic() >= self.next_flush:
            self.path.write_bytes(self.buffer)
            self.next_flush = time.monotonic() + 0.25

    def _read(self):
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        try:
            while block := os.read(self.process.stdout.fileno(), 8192):
                self._append(self.redactor.feed(decoder.decode(block)))
            self._append(self.redactor.feed(decoder.decode(b"", final=True), final=True))
            self.path.write_bytes(self.buffer)
        except BaseException as error:
            self.error = error

    def finish(self):
        self.thread.join(timeout=4)
        if self.thread.is_alive():
            raise ProcessContainmentError("Owned worker stdout did not close after tree termination.")
        if self.error:
            raise self.error
        # Ignore an incomplete UTF-8 codepoint at the beginning of the bounded tail.
        return bytes(self.buffer[-TAIL_LIMIT:]).decode("utf-8", errors="ignore")


class ProcessSupervisor:
    def __init__(self):
        self.shutdown = threading.Event()
        self.lock = threading.RLock()
        self.owned = set()
        atexit.register(self.close)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.shutdown.set()
        atexit.unregister(self.close)
        with self.lock:
            owned = list(self.owned)
        for container in owned:
            container.terminate()
            container.confirm_stopped()

    def run(self, args, *, cwd, env, log_path, timeout_seconds=120, cancel_event=None, on_event=None):
        if self.shutdown.is_set():
            raise RuntimeError("Process supervisor is closed.")
        if not args or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("Trusted arguments and a positive finite deadline are required.")
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        deadline = started + timeout_seconds
        container = process = output = None
        cancelled = timed_out = False
        peak_rss = 0
        try:
            with self.lock:
                if self.shutdown.is_set():
                    raise RuntimeError("Process supervisor is closed.")
                if sys.platform == "win32":
                    container = _WindowsJob()
                    process = _WindowsProcess(args, cwd=cwd, env=env, job=container)
                    container.assign_and_resume(process)
                else:
                    process = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
                    container = _PosixGroup(process)
                self.owned.add(container)
            output = _OutputDrain(process, path, env, on_event)
            output.start()
            while True:
                rss = 0
                for pid in container.pids():
                    try:
                        rss += psutil.Process(pid).memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                peak_rss = max(peak_rss, rss)
                if self.shutdown.is_set() or (cancel_event is not None and cancel_event.is_set()):
                    cancelled = True
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    break
                if process.poll() is not None:
                    break
                if output.error:
                    raise output.error
                time.sleep(0.02)
            # Also clean descendants left behind by a successful or crashed parent.
            container.terminate()
            process.wait(timeout=4)
            container.confirm_stopped()
            tail = output.finish()
            return ProcessResult(process.returncode, cancelled, timed_out, time.monotonic()-started, peak_rss, tail)
        finally:
            try:
                try:
                    if container is not None:
                        container.terminate()
                finally:
                    if process is not None and process.poll() is None:
                        # Also end the suspended parent if assignment failed.
                        process.kill()
                        process.wait(timeout=4)
                    if container is not None:
                        container.confirm_stopped()
            finally:
                if container is not None:
                    with self.lock:
                        self.owned.discard(container)
                    container.close()  # Kill-on-close even when cleanup diagnostics fail.
                if output is not None and output.thread.is_alive():
                    output.thread.join(timeout=4)
                if process is not None and process.stdout is not None:
                    process.stdout.close()
                if isinstance(process, _WindowsProcess):
                    process.close()
