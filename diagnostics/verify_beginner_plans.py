"""Independently inspect an actual downloaded beginner ZIP. No native generation."""
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

from pypdf import PdfReader


def inspect(path, expected):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest == expected
        assert len(names) == len(set(names))
        assert set(names) == {'manifest.json', *[a['relative_path'] for a in manifest['artifacts']]}
        for a in manifest['artifacts']:
            data = archive.read(a['relative_path'])
            assert len(data) == a['size_bytes'] and hashlib.sha256(data).hexdigest() == a['sha256']
            assert a['revision_id'] == manifest['revision_id'] and a['spec_sha256'] == manifest['spec_sha256']
        spec = json.loads(archive.read('project.json'))
        resolved = json.loads(archive.read('resolved-project.json'))
        assert [spec['dimensions'][f'outside_{axis}_mm'] for axis in ('width', 'height', 'depth')] == ['914.4', '914.4', '304.8']
        assert [spec['materials'][role]['actual_thickness_mm'] for role in ('main', 'back')] == ['18', '6']
        assert resolved['part_instance_count'] == 7
        cuts = {(g['finished_mm']['length_mm'], g['finished_mm']['width_mm'], g['finished_mm']['thickness_mm']): g['quantity'] for g in resolved['cut_groups']}
        assert cuts == {('914.4', '298.8', '18'): 2, ('878.4', '298.8', '18'): 4, ('914.4', '914.4', '6'): 1}
        recipe = json.loads(archive.read('construction-recipe.json'))
        assert recipe['status'] == 'complete' and recipe['physical_review'] == 'not_reviewed'
        assert {h['hardware_id']: h['required_quantity'] for h in recipe['hardware']} == {'carcass_screw': 24, 'back_screw': 36}
        guide = json.loads(archive.read('beginner-guide.json'))
        pages = PdfReader(io.BytesIO(archive.read('design-packet.pdf'))).pages
        assert len(guide['steps']) == len(recipe['operations']) == 10
        for step, operation in zip(guide['steps'], recipe['operations']):
            page = pages[step['page']-1]
            text = ' '.join(page.extract_text().split())
            assert step['operation_id'] == operation['operation_id']
            assert step['figure_label'] in text
            assert all(' '.join(a.split()) in text for a in operation['actions'])
            # A label alone is not an illustration: each illustrated page must draw vectors.
            assert page.get_contents().get_data().count(b' re') >= 2
        assert all(manifest['revision_id'] in p.extract_text() for p in pages)
        stock = json.loads(archive.read('stock-layout.json'))
        assert stock['revision_id'] == manifest['revision_id'] and stock['plan']['status'] == 'complete' and not stock['plan']['unplaced_instance_ids']
        assert manifest['validation']['geometry'] == 'passed'
        return {'status': 'passed', 'revision_id': manifest['revision_id'], 'spec_sha256': manifest['spec_sha256'], 'resolved_sha256': manifest['resolved_sha256'], 'guide_pages': len(pages), 'illustrated_steps': 10, 'every_payload_hash_and_revision_checked': True, 'cut_groups': {str(k): v for k, v in cuts.items()}, 'zip_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(), 'physical_build': 'not_performed'}


if __name__ == '__main__':
    print(json.dumps(inspect(Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))))
