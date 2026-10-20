"""Offline Windows desktop entry point. Uses the already-installed runtime only."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

from woodwork import __version__


class LaunchError(RuntimeError):
    """A startup problem that can be shown without a terminal."""


def _configuration(path):
    try:
        config = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        repository = Path(config['repository'])
        data_root = Path(config['data_root'])
        port = config.get('port', 8777)
        if not repository.is_absolute() or not data_root.is_absolute():
            raise ValueError('Paths must be absolute.')
        if any(str(p).startswith(('\\\\', '//')) for p in (repository, data_root)):
            raise ValueError('Use local disk paths, not network shares.')
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError('Invalid local port.')
        repository, data_root = repository.resolve(), data_root.resolve()
        if repository != Path(__file__).resolve().parents[4]:
            raise ValueError('This shortcut belongs to another checkout. Reinstall its shortcut.')
        if data_root.is_relative_to(repository):
            raise ValueError('Keep saved projects outside the source checkout.')
        return repository, data_root, port
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise LaunchError(f'Cannot read the launcher settings: {path}\n{error}') from error


def _json(url):
    # Ignore system HTTP proxies and refuse redirects: launch probes stay on loopback.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(url, timeout=1) as response:
        return json.loads(response.read(1024 * 1024))


def _ready(url, repository, data_root):
    try:
        health, runtime = _json(url + 'api/v1/health'), _json(url + 'api/v1/runtime')
        matches = (health.get('status') == 'ready' and health.get('app_version') == __version__
                   and Path(runtime.get('data_root', '')).resolve() == data_root
                   and Path(runtime.get('application_root', '')).resolve() == repository)
        if not matches:
            raise LaunchError('Another service or project store is using the app port. '
                              'Close that service before opening this shortcut. No projects were changed.')
        return True
    except LaunchError:
        raise
    except (OSError, ValueError, AttributeError) as error:
        raise LaunchError('The app port is occupied, but it is not responding as this '
                          'Woodworking Planner. No projects were changed.') from error


@contextmanager
def _startup_lock(port, timeout):
    if os.name != 'nt':
        raise LaunchError('The desktop shortcut launcher currently supports Windows only.')
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateMutexW(None, False, f'Local\\WoodworkingPlanner-start-{port}')
    if not handle:
        raise LaunchError('Windows could not reserve the app startup lock. Try opening it again.')
    acquired = False
    try:
        acquired = kernel.WaitForSingleObject(handle, int(timeout * 1000)) in (0, 0x80)
        if not acquired:
            raise LaunchError('Another launcher is still starting the app. Wait a moment and try again.')
        yield
    finally:
        if acquired:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def launch(config_path, *, open_browser=webbrowser.open, startup_timeout=45):
    """Wait for this checkout/store, then open it. Return the owned PID for diagnostics."""
    repository, data_root, port = _configuration(config_path)
    with _startup_lock(port, startup_timeout + 5):
        return _launch(config_path, repository, data_root, port, open_browser, startup_timeout)


def _launch(config_path, repository, data_root, port, open_browser, startup_timeout):
    url = f'http://127.0.0.1:{port}/'
    python = repository / '.venv/Scripts/python.exe'
    if not python.is_file():
        raise LaunchError('The installed Python runtime is missing. Restore the prepared .venv '
                          'or run the documented setup before using this shortcut. Nothing was downloaded.')
    if not (repository / 'apps/web/dist/index.html').is_file():
        raise LaunchError('The built application is missing. Run the documented local build first. '
                          'Nothing was downloaded.')
    process = None
    with socket.socket() as probe:
        probe.settimeout(1)
        occupied = probe.connect_ex(('127.0.0.1', port)) == 0
    if occupied:
        _ready(url, repository, data_root)
    else:
        logs = Path(config_path).resolve().parent / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        log_path = logs / f'service-{time.time_ns()}.log'
        environment = {**os.environ, 'WOODWORK_DATA_ROOT': str(data_root),
                       'CADGEN_TELEMETRY': '0', 'CADGEN_UPDATE_CHECK': '0'}
        with log_path.open('ab', buffering=0) as log:
            process = subprocess.Popen(
                [str(python), '-m', 'uvicorn', 'woodwork.api:create_app', '--factory',
                 '--host', '127.0.0.1', '--port', str(port), '--no-access-log'],
                cwd=repository, env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == 'nt' else 0,
            )
        deadline = time.monotonic() + startup_timeout
        try:
            while True:
                if process.poll() is not None:
                    raise LaunchError(f'The local service stopped during startup. See {log_path}')
                try:
                    if _ready(url, repository, data_root):
                        break
                except LaunchError:
                    if time.monotonic() >= deadline:
                        raise LaunchError(f'The local service did not become ready. See {log_path}')
                time.sleep(0.2)
        except BaseException:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            raise
    if not open_browser(url):
        raise LaunchError(f'The app is running, but Windows could not open your browser. '
                          f'Open {url} in your browser. Your saved projects are available.')
    return {'url': url, 'reused': process is None, 'started_pid': process.pid if process else None}


def main():
    parser = argparse.ArgumentParser(description='Open the offline Woodworking Planner.')
    parser.add_argument('--config', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = launch(args.config)
        if sys.stdout:
            print(json.dumps(result))
        return 0
    except Exception as error:
        message = str(error)
        try:
            log = args.config.resolve().parent / 'launcher-error.log'
            with log.open('a', encoding='utf-8') as output:
                output.write(f'{time.ctime()}: {message}\n')
            message += f'\n\nDetails: {log}'
        except OSError:
            pass
        if sys.stderr:
            print(message, file=sys.stderr)
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, 'Woodworking Planner could not open', 0x10)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
