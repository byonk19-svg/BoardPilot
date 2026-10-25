"""Exercise the launcher through its public entry point and real loopback API."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import urllib.request

import psutil
import pytest

from woodwork.launcher import LaunchError, launch


REPOSITORY = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Native Windows desktop launcher')


def configuration(tmp_path):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    path = tmp_path / 'launcher with spaces.json'
    path.write_text(json.dumps({'repository': str(REPOSITORY),
                               'data_root': str(tmp_path / 'saved projects'),
                               'port': port}), encoding='utf-8')
    return path


def read_json(url):
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=5) as response:
        return json.load(response)


def stop_owned(result):
    if result and result['started_pid']:
        try:
            process = psutil.Process(result['started_pid'])
            owned = [process, *process.children(recursive=True)]
        except psutil.NoSuchProcess:
            return
        for process in reversed(owned):
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(owned, timeout=10)
        assert not alive, f'Owned service processes did not stop: {[process.pid for process in alive]}'


def test_cold_start_opens_only_after_ready_and_second_click_reuses_saved_store(tmp_path):
    config = configuration(tmp_path)
    opened = []
    result = None

    def browser(url):
        assert read_json(url + 'api/v1/health')['status'] == 'ready'
        opened.append(url)
        return True

    try:
        result = launch(config, open_browser=browser)
        assert result['started_pid'] and not result['reused']
        second = launch(config, open_browser=browser)
        assert second['reused'] and second['started_pid'] is None
        runtime = read_json(result['url'] + 'api/v1/runtime')
        assert Path(runtime['data_root']) == tmp_path / 'saved projects'
        assert opened == [result['url'], result['url']]
    finally:
        stop_owned(result)


def test_simultaneous_shortcut_processes_start_only_one_service(tmp_path):
    config = configuration(tmp_path)
    command = [sys.executable, '-c',
               'import json,sys; from woodwork.launcher import launch; '
               'print(json.dumps(launch(sys.argv[1],open_browser=lambda url:True,startup_timeout=15)))',
               str(config)]
    results = []
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            completed = list(pool.map(lambda _: subprocess.run(command, capture_output=True, text=True,
                                                               timeout=40), range(2)))
        for process in completed:
            if process.returncode == 0:
                results.append(json.loads(process.stdout))
        assert all(process.returncode == 0 for process in completed), [p.stderr for p in completed]
        assert sorted(result['reused'] for result in results) == [False, True]
    finally:
        for result in results:
            stop_owned(result)


def test_restart_keeps_saved_design_and_refreshes_the_browser_session(tmp_path):
    config = configuration(tmp_path)
    result = None
    try:
        result = launch(config, open_browser=lambda url: True)
        url = result['url']
        csrf = read_json(url + 'api/v1/session')['csrf_token']
        spec = read_json(url + 'api/v1/templates')['templates'][0]['default_spec']
        body = json.dumps({'title': 'Launcher reconnect sample', 'spec': spec}).encode()
        request = urllib.request.Request(url + 'api/v1/projects', data=body,
                                         headers={'Content-Type': 'application/json', 'X-Woodwork-CSRF': csrf})
        created = read_json(request)
        process = psutil.Process(result['started_pid'])
        owned = [process, *process.children(recursive=True)]
        stop_owned(result)
        result = None
        _, alive = psutil.wait_procs(owned, timeout=0)
        assert not alive, f'Owned service processes survived shutdown: {[process.pid for process in alive]}'
        with socket.socket() as probe:
            probe.settimeout(1)
            assert probe.connect_ex(('127.0.0.1', json.loads(config.read_text())['port'])) != 0
        result = launch(config, open_browser=lambda url: True)
        assert not result['reused']
        restored = read_json(url + 'api/v1/projects/' + created['project']['id'])
        assert restored['project']['latest_accepted_revision_id'] == created['revision']['id']
        assert read_json(url + 'api/v1/session')['csrf_token'] != csrf
    finally:
        stop_owned(result)


def test_other_store_on_the_port_is_preserved_and_is_not_opened(tmp_path):
    config = configuration(tmp_path)
    result = None
    opened = []
    try:
        result = launch(config, open_browser=lambda url: True)
        different = json.loads(config.read_text())
        different['data_root'] = str(tmp_path / 'another store')
        other_config = tmp_path / 'other.json'
        other_config.write_text(json.dumps(different))
        with pytest.raises(LaunchError, match='Another service or project store'):
            launch(other_config, open_browser=lambda url: opened.append(url))
        assert not opened
        assert not Path(different['data_root']).exists()
        assert read_json(result['url'] + 'api/v1/health')['status'] == 'ready'
    finally:
        stop_owned(result)


def test_failed_startup_preserves_store_and_a_later_retry_can_start(tmp_path):
    config = configuration(tmp_path)
    data_root = tmp_path / 'saved projects'
    data_root.write_text('Meaningful existing file, not a directory')
    with pytest.raises(LaunchError, match='stopped during startup'):
        launch(config, open_browser=lambda url: True)
    assert data_root.read_text() == 'Meaningful existing file, not a directory'
    # Select another disposable store; never reset the failed location.
    settings = json.loads(config.read_text())
    settings['data_root'] = str(tmp_path / 'valid store')
    config.write_text(json.dumps(settings))
    result = None
    try:
        result = launch(config, open_browser=lambda url: True)
        assert read_json(result['url'] + 'api/v1/health')['status'] == 'ready'
    finally:
        stop_owned(result)


def test_shortcut_installation_preserves_unrelated_shortcuts_and_records_explicit_store(tmp_path):
    shortcut = tmp_path / 'My local workshop.lnk'
    store = tmp_path / 'existing bookcase store'
    command = ['powershell.exe', '-NoProfile', '-File', str(REPOSITORY / 'scripts/install-launcher.ps1'),
               '-DataRoot', str(store), '-ShortcutPath', str(shortcut)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    settings = json.loads((store / 'desktop-launcher.json').read_text(encoding='utf-8-sig'))
    assert Path(settings['data_root']) == store and settings['port'] == 8777
    assert shortcut.is_file()
    assert subprocess.run(command, capture_output=True, timeout=15).returncode == 0
    original = shortcut.read_bytes()
    other = command.copy()
    other[other.index('-DataRoot') + 1] = str(tmp_path / 'another store')
    refused = subprocess.run(other, capture_output=True, text=True, timeout=15)
    assert refused.returncode != 0 and 'different shortcut' in refused.stderr
    assert shortcut.read_bytes() == original
    assert not (tmp_path / 'another store').exists()


def test_startup_deadline_cleans_only_owned_service_and_retry_recovers(tmp_path):
    config = configuration(tmp_path)
    with pytest.raises(LaunchError, match='did not become ready'):
        launch(config, open_browser=lambda url: True, startup_timeout=0)
    result = None
    try:
        result = launch(config, open_browser=lambda url: True)
        assert not result['reused']
    finally:
        stop_owned(result)
