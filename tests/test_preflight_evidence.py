"""Dispatcher evidence protocol tests; synthetic outputs are not CAD acceptance."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from woodwork.exports.core import write_json
from woodwork.jobs.dispatcher import Dispatcher
from woodwork.storage import Store
from woodwork.templates import default_project_spec


@pytest.fixture
def dispatch_case(tmp_path, monkeypatch):
    import woodwork.cad_adapter as adapter
    import woodwork.jobs.dispatcher as dispatch_module

    store = Store(tmp_path)
    (store.root / 'receipts').mkdir()
    initial = store.create_project('Preflight evidence test', default_project_spec())
    dispatcher = Dispatcher(store)
    dispatcher.supervisor.close()
    versions = {'versions': {'test_runtime': 'fixed'}, 'missing_components': [],
                'kernel_probe': 'explicit_preflight_required'}
    monkeypatch.setattr(dispatch_module, 'runtime_versions', lambda: versions)
    monkeypatch.setattr(dispatch_module, 'worker_environment', lambda root: {})
    # These tests isolate publication/diagnostic state. Genuine CAD validation
    # and process containment have their own integration suites.
    monkeypatch.setattr(adapter, 'validate_artifact_set', lambda *args, **kwargs: None)

    def complete(kind, *, timed_out=False, returncode=0):
        revision = initial['revision']
        if kind == 'preflight':
            store.queue_preflight()
        else:
            source = None
            if kind in {'stock', 'documents'}:
                seed = store.queue_job(revision['id'], 'generate', 'seed')
                store.claim_job('seed-session')
                source = 'set_seed'
                manifest = {'project_id': initial['project']['id'],
                            'revision_id': revision['id'], 'artifact_set_id': source,
                            'spec_sha256': revision['spec_sha256'],
                            'resolved_sha256': revision['resolved_sha256'],
                            'source_artifact_set_id': None, 'capabilities': ['geometry'],
                            'artifacts': []}
                store.publish_result(seed['id'], manifest, 'artifacts/set_seed', 'a' * 64)
            store.queue_job(revision['id'], kind, 'evidence-job', source_artifact_set_id=source)
        job = store.claim_job('test-session')

        class CompletedWorker:
            def run(self, args, **kwargs):
                if not timed_out and returncode == 0:
                    root = Path(args[-1])
                    (root / 'out').mkdir()
                    payload = json.loads((root / 'input.json').read_text())
                    manifest = {**payload['metadata'],
                                'spec_sha256': payload['resolved']['spec_sha256'],
                                'resolved_sha256': payload['resolved']['resolved_sha256'],
                                'capabilities': ['geometry'], 'artifacts': []}
                    if kind in {'stock', 'documents'}:
                        manifest['capabilities'].append('stock_layout' if kind == 'stock' else 'documents')
                    write_json(root / 'out/manifest.json', manifest)
                return SimpleNamespace(returncode=returncode, timed_out=timed_out,
                                       cancelled=False, elapsed_seconds=120 if timed_out else 1,
                                       peak_rss_bytes=1024, log_tail='')

            def close(self):
                pass

        dispatcher.supervisor = CompletedWorker()
        dispatcher.execute(job)
        return store.get_job(job['id'])

    yield store, complete
    dispatcher.close()


@pytest.mark.parametrize('kind', ['stock', 'documents'])
def test_derived_output_success_preserves_failed_cad_probe(dispatch_case, kind):
    store, complete = dispatch_case
    probe = store.root / 'runtime-preflight.json'
    write_json(probe, {'status': 'failed', 'checked_at': 'earlier-probe',
                       'diagnostic': {'code': 'NATIVE_KERNEL_LOAD_REFUSED'}})
    before = probe.read_bytes()

    assert complete(kind)['state'] == 'succeeded'
    assert probe.read_bytes() == before


def test_explicit_preflight_timeout_replaces_old_passing_probe(dispatch_case):
    store, complete = dispatch_case
    probe = store.root / 'runtime-preflight.json'
    write_json(probe, {'status': 'passed', 'checked_at': 'earlier-probe', 'kernel_probe': 'passed'})

    job = complete('preflight', timed_out=True, returncode=1)
    assert job['state'] == 'failed'
    assert job['diagnostic_code'] == 'WORKER_TIMEOUT'
    evidence = json.loads(probe.read_text())
    assert evidence['status'] == 'failed'
    assert evidence['checked_at'] != 'earlier-probe'
    assert evidence['diagnostic']['code'] == 'WORKER_TIMEOUT'
    assert evidence['metrics']['elapsed_seconds'] == 120


@pytest.mark.parametrize('kind', ['generate', 'preflight'])
def test_actual_cad_job_success_records_passing_probe(dispatch_case, kind):
    store, complete = dispatch_case
    write_json(store.root / 'runtime-preflight.json', {'status': 'failed'})

    assert complete(kind)['state'] == 'succeeded'
    evidence = json.loads((store.root / 'runtime-preflight.json').read_text())
    assert evidence['status'] == evidence['kernel_probe'] == 'passed'
    assert evidence['versions'] == {'test_runtime': 'fixed'}
    assert evidence['metrics']['elapsed_seconds'] == 1
