"""Real owned child trees exercise native containment rather than mocked PIDs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import psutil
import pytest

from woodwork.jobs.process import ProcessSupervisor


def run(supervisor, tmp_path, code, **kwargs):
    script = tmp_path / f"worker_{time.monotonic_ns()}.py"
    script.write_text(code, encoding="utf-8")
    return supervisor.run([sys.executable, "-u", str(script)], cwd=tmp_path,
                          env=dict(os.environ), log_path=tmp_path / "worker.log", **kwargs)


TREE_WORKER = '''
import json, os, subprocess, sys, time
child = subprocess.Popen([sys.executable, "-u", "-c", "import time; time.sleep(60)"])
print(json.dumps({"stage":"generating_geometry", "pid":os.getpid(), "child_pid":child.pid}), flush=True)
while True:
    print(json.dumps({"stage":"inspecting_geometry", "heartbeat":True}), flush=True)
    time.sleep(0.03)
'''


def assert_stopped(pids):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and any(psutil.pid_exists(pid) for pid in pids):
        time.sleep(0.02)
    assert not any(psutil.pid_exists(pid) for pid in pids)


def test_cancel_ends_descendants_within_five_seconds_and_keeps_unrelated_process(tmp_path):
    cancellation = threading.Event()
    seen = []
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    def progress(event):
        if "child_pid" in event:
            seen.extend([event["pid"], event["child_pid"]])
            cancellation.set()
    try:
        with ProcessSupervisor() as supervisor:
            result = run(supervisor, tmp_path, TREE_WORKER, timeout_seconds=20,
                         cancel_event=cancellation, on_event=progress)
        assert result.cancelled and not result.timed_out
        assert result.elapsed_seconds < 5
        assert result.returncode != 0
        assert result.peak_rss_bytes > 0
        assert len(seen) == 2
        assert_stopped(seen)
        assert unrelated.poll() is None
    finally:
        unrelated.terminate()
        unrelated.wait(timeout=5)


def test_heartbeat_cannot_extend_wall_clock_deadline(tmp_path):
    events = []
    with ProcessSupervisor() as supervisor:
        result = run(supervisor, tmp_path, TREE_WORKER, timeout_seconds=0.8, on_event=events.append)
    assert result.timed_out and not result.cancelled
    assert result.elapsed_seconds < 5
    assert len(events) > 3
    initial = next(event for event in events if "child_pid" in event)
    assert_stopped([initial["pid"], initial["child_pid"]])


def test_worker_crash_cleans_descendant_and_next_run_succeeds(tmp_path):
    events = []
    code = TREE_WORKER.split("while True:")[0] + "sys.exit(23)\n"
    with ProcessSupervisor() as supervisor:
        failed = run(supervisor, tmp_path, code, on_event=events.append)
        initial = next(event for event in events if "child_pid" in event)
        assert failed.returncode == 23
        assert not failed.cancelled and not failed.timed_out
        assert_stopped([initial["pid"], initial["child_pid"]])
        succeeded = run(supervisor, tmp_path, "print('fresh success', flush=True)")
        assert succeeded.returncode == 0
        assert "fresh success" in succeeded.log_tail


def test_stdout_flood_is_drained_and_logs_remain_bounded(tmp_path):
    with ProcessSupervisor() as supervisor:
        result = run(supervisor, tmp_path, "import sys\nfor i in range(2048): sys.stdout.write('x'*4096+'\\n')\nprint('final marker')\n")
    assert result.returncode == 0 and not result.timed_out
    assert len(result.log_tail.encode("utf-8")) <= 65536
    assert (tmp_path / "worker.log").stat().st_size <= 262144
    assert "final marker" in result.log_tail


def test_supervisor_close_ends_active_owned_tree(tmp_path):
    supervisor = ProcessSupervisor()
    started = threading.Event()
    seen = []
    results = []
    def event(event):
        if "child_pid" in event:
            seen.extend([event["pid"], event["child_pid"]])
            started.set()
    thread = threading.Thread(target=lambda: results.append(run(supervisor, tmp_path, TREE_WORKER, on_event=event)))
    thread.start()
    assert started.wait(timeout=5)
    supervisor.close()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert results[0].cancelled
    assert_stopped(seen)


def test_secret_environment_values_are_redacted_from_log_and_events(tmp_path):
    env = dict(os.environ)
    env["TEST_PROVIDER_API_KEY"] = "local-supervisor-test-secret-123"
    script = tmp_path / "secret.py"
    script.write_text("import json, os\nprint(os.environ['TEST_PROVIDER_API_KEY'])\nprint(json.dumps({'stage':'compiling','message':os.environ['TEST_PROVIDER_API_KEY']}))\n", encoding="utf-8")
    events = []
    with ProcessSupervisor() as supervisor:
        result = supervisor.run([sys.executable, "-u", str(script)], cwd=tmp_path,
                                env=env, log_path=tmp_path / "worker.log", on_event=events.append)
    assert result.returncode == 0
    assert env["TEST_PROVIDER_API_KEY"] not in result.log_tail
    assert env["TEST_PROVIDER_API_KEY"] not in (tmp_path / "worker.log").read_text(encoding="utf-8")
    assert env["TEST_PROVIDER_API_KEY"] not in json.dumps(events)


@pytest.mark.skipif(sys.platform != "win32", reason="Real native Windows suspended-process probe")
def test_windows_assignment_precedes_any_worker_code(tmp_path, monkeypatch):
    from woodwork.jobs.process import _WindowsJob
    marker = tmp_path / "executed.txt"
    original = _WindowsJob.assign_and_resume
    probed = []
    def delayed_assignment(self, process):
        time.sleep(0.2)
        assert not marker.exists(), "Worker ran before JobObject containment was established"
        probed.append(process.pid)
        return original(self, process)
    monkeypatch.setattr(_WindowsJob, "assign_and_resume", delayed_assignment)
    with ProcessSupervisor() as supervisor:
        result = run(supervisor, tmp_path, f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n")
    assert result.returncode == 0 and probed and marker.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Real Windows kill-on-job-close after abrupt coordinator exit")
def test_abrupt_coordinator_crash_closes_job_and_stops_owned_tree(tmp_path):
    worker = tmp_path / "tree.py"
    worker.write_text(TREE_WORKER, encoding="utf-8")
    record = tmp_path / "owned-pids.json"
    coordinator = tmp_path / "coordinator.py"
    coordinator.write_text(
        "import json, os, sys\nfrom pathlib import Path\nfrom woodwork.jobs.process import ProcessSupervisor\n"
        "def event(value):\n"
        "    if 'child_pid' in value:\n"
        f"        Path({str(record)!r}).write_text(json.dumps(value))\n"
        "        os._exit(37)\n"
        "with ProcessSupervisor() as supervisor:\n"
        f"    supervisor.run([sys.executable, '-u', {str(worker)!r}], cwd={str(tmp_path)!r}, env=dict(os.environ), log_path={str(tmp_path / 'coordinator.log')!r}, on_event=event)\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "services" / "api" / "src")
    process = subprocess.Popen([sys.executable, "-u", str(coordinator)], env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        output, _ = process.communicate(timeout=10)
        assert process.returncode == 37, output.decode("utf-8", errors="replace")
        observed = json.loads(record.read_text(encoding="utf-8"))
        assert_stopped([observed["pid"], observed["child_pid"]])
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_failed_spawn_does_not_poison_supervisor(tmp_path):
    with ProcessSupervisor() as supervisor:
        with pytest.raises(OSError):
            supervisor.run([str(tmp_path / "missing-interpreter.exe")], cwd=tmp_path,
                           env=dict(os.environ), log_path=tmp_path / "missing.log")
        assert run(supervisor, tmp_path, "print('recovered')").returncode == 0


@pytest.mark.skipif(sys.platform != "win32", reason="Real Windows startup/shutdown barrier")
def test_close_waits_for_inflight_contained_launch(tmp_path, monkeypatch):
    from woodwork.jobs.process import _WindowsJob
    supervisor = ProcessSupervisor()
    entered, release, closed = threading.Event(), threading.Event(), threading.Event()
    pids, results, errors = [], [], []
    original = _WindowsJob.assign_and_resume
    def held(self, process):
        pids.append(process.pid)
        entered.set()
        assert release.wait(5)
        return original(self, process)
    monkeypatch.setattr(_WindowsJob, "assign_and_resume", held)
    def launch():
        try:
            results.append(run(supervisor, tmp_path, "import time; time.sleep(30)"))
        except BaseException as error:
            errors.append(error)
    runner = threading.Thread(target=launch)
    closer = threading.Thread(target=lambda: (supervisor.close(), closed.set()))
    runner.start()
    try:
        assert entered.wait(5)
        closer.start()
        assert not closed.wait(0.1), "Close returned before its inflight launch was contained and stopped"
    finally:
        release.set()
        runner.join(timeout=5)
        if closer.ident is not None:
            closer.join(timeout=5)
        supervisor.close()
    assert not errors and results[0].cancelled
    assert closed.is_set() and not runner.is_alive() and not closer.is_alive()
    assert_stopped(pids)


@pytest.mark.skipif(sys.platform != "win32", reason="Real Windows atomic Job Object membership at creation")
def test_coordinator_crash_before_resume_does_not_leave_suspended_worker(tmp_path):
    worker = tmp_path / "never-started.py"
    worker.write_text("import time; time.sleep(30)", encoding="utf-8")
    record = tmp_path / "created-pid.json"
    coordinator = tmp_path / "birth-coordinator.py"
    coordinator.write_text(
        "import json, os, sys, psutil\nfrom pathlib import Path\n"
        "from woodwork.jobs.process import ProcessSupervisor, _WindowsJob\n"
        "def crash_before_resume(self, process):\n"
        f"    Path({str(record)!r}).write_text(json.dumps({{'pid':process.pid,'created':psutil.Process(process.pid).create_time()}}))\n"
        "    os._exit(37)\n"
        "_WindowsJob.assign_and_resume = crash_before_resume\n"
        "with ProcessSupervisor() as supervisor:\n"
        f"    supervisor.run([sys.executable, '-u', {str(worker)!r}], cwd={str(tmp_path)!r}, env=dict(os.environ), log_path={str(tmp_path / 'birth.log')!r})\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "services" / "api" / "src")
    process = subprocess.Popen([sys.executable, "-u", str(coordinator)], env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        output, _ = process.communicate(timeout=10)
        assert process.returncode == 37, output.decode("utf-8", errors="replace")
        observed = json.loads(record.read_text(encoding="utf-8"))
        assert_stopped([observed["pid"]])
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        # Failures must clean only the exact disposable process created by this test.
        if record.exists():
            observed = json.loads(record.read_text(encoding="utf-8"))
            try:
                owned = psutil.Process(observed["pid"])
                if owned.create_time() == observed["created"]:
                    owned.kill()
                    owned.wait(timeout=5)
            except psutil.NoSuchProcess:
                pass
