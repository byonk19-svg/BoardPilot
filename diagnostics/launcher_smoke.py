"""Real browser restart/reconnect proof in a fresh, explicitly isolated local store."""
import argparse
import json
from pathlib import Path
import time

from playwright.sync_api import sync_playwright, expect
import psutil

from diagnostics.recovery import seed
from woodwork.launcher import launch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.store.resolve()
    if root.exists():
        raise SystemExit('Choose a new isolated store. This diagnostic never resets existing projects.')
    root.mkdir(parents=True)
    _, manifest = seed(root, args.source.resolve())
    args.output.mkdir(parents=True, exist_ok=True)
    config = root / 'desktop-launcher.json'
    config.write_text(json.dumps({'repository': str(Path(__file__).resolve().parents[1]),
                                 'data_root': str(root), 'port': 8777}), encoding='utf-8')
    result = None
    events, external = [], []

    def stop():
        nonlocal result
        if result and result['started_pid']:
            process = psutil.Process(result['started_pid'])
            process.terminate()
            process.wait(timeout=10)
            result = None

    try:
        started = time.monotonic()
        result = launch(config, open_browser=lambda url: True)
        cold_seconds = time.monotonic() - started
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(base_url=result['url'], viewport={'width': 1365, 'height': 900}, service_workers='block')
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            def local_only(route):
                url = route.request.url
                if not url.startswith(('http://127.0.0.1:8777/', 'blob:', 'data:')):
                    external.append(url)
                    route.abort()
                else:
                    route.continue_()
            context.route('**/*', local_only)
            page = context.new_page()
            page.on('response', lambda response: events.append({'url': response.url, 'status': response.status})
                    if '/api/v1/' in response.url else None)
            page.goto(result['url'])
            page.get_by_label('Saved projects').select_option(manifest['project_id'])
            expect(page.get_by_test_id('asset-loaded')).to_have_text('7 part instances loaded')
            expect(page.get_by_role('button', name='Update design', exact=True)).to_be_enabled()
            before = page.request.get('/api/v1/revisions/' + manifest['revision_id']).json()['revision']
            cut_before = page.get_by_test_id('cut-list').inner_text()
            width = page.get_by_label('Outside width', exact=True)
            width.fill('40 in')
            expect(page.get_by_text('Draft saved locally.', exact=True)).to_be_visible(timeout=15000)
            page.screenshot(path=str(args.output / 'before-restart.png'))
            # Keep this browser tab and its old CSRF session alive across a real server restart.
            stop()
            width.fill('41 in')
            expect(page.get_by_role('alert').first).to_contain_text('local service is unavailable', timeout=10000)
            expect(width).to_have_value('41 in')
            page.screenshot(path=str(args.output / 'service-stopped.png'))
            result = launch(config, open_browser=lambda url: True)
            width.fill('42 in')
            expect(page.get_by_text('Draft saved locally.', exact=True)).to_be_visible(timeout=15000)
            expect(page.get_by_role('button', name='Update design', exact=True)).to_be_enabled()
            assert any(event['status'] == 403 for event in events), 'The old session must be renewed after restart.'
            assert page.request.get('/api/v1/revisions/' + manifest['revision_id']).json()['revision'] == before
            page.reload()
            expect(width).to_have_value('42 in')
            expect(page.get_by_test_id('asset-loaded')).to_have_text('7 part instances loaded')
            cut_after = page.get_by_test_id('cut-list').inner_text()
            assert cut_after == cut_before
            page.screenshot(path=str(args.output / 'reconnected.png'))
            started = time.monotonic()
            reused = launch(config, open_browser=lambda url: True)
            assert reused['reused'] and reused['started_pid'] is None
            assert not external, external
            report = {'status': 'passed', 'cold_start_seconds': round(cold_seconds, 3),
                      'reuse_seconds': round(time.monotonic() - started, 3),
                      'existing_tab_reconnected': True, 'csrf_session_renewed': True,
                      'draft_saved_and_restored': True, 'accepted_revision_unchanged': True,
                      'cut_list_unchanged': True, 'loaded_panels': 7, 'external_requests': external,
                      'project_id': manifest['project_id'], 'revision_id': manifest['revision_id'],
                      'api_events': events, 'store': str(root)}
            (args.output / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            context.tracing.stop(path=str(args.output / 'browser-trace.zip'))
            browser.close()
            print(json.dumps({key: value for key, value in report.items() if key != 'api_events'}))
    finally:
        stop()


if __name__ == '__main__':
    main()
