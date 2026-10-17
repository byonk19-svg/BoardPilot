import json
import os
from pathlib import Path
import pytest
from woodwork.exports.stock import add_stock,validate_stock_output
from woodwork.cad_adapter import validate_artifact_set
from woodwork.exports.core import sha256_file

ROOT=Path(__file__).resolve().parents[1]
EXPECTED=json.loads((ROOT/'tests/fixtures/bookcase-expected.json').read_text())['fixtures']


@pytest.mark.skipif(not os.environ.get('WOODWORK_DOCUMENT_SOURCE_ROOT'),reason='Requires all nine actual cumulative document sets.')
@pytest.mark.parametrize('example',EXPECTED,ids=lambda e:e['input_file'])
def test_actual_cumulative_geometry_documents_stock_and_pdf(example,tmp_path):
    source=Path(os.environ['WOODWORK_DOCUMENT_SOURCE_ROOT'])/example['input_file'].removesuffix('.json')
    manifest=json.loads((source/'manifest.json').read_text())
    original_manifest_hash=sha256_file(source/'manifest.json')
    spec=json.loads((source/'project.json').read_text());resolved=json.loads((source/'resolved-project.json').read_text())
    metadata={k:manifest[k] for k in ('project_id','revision_id','revision_number','spec_sha256','resolved_sha256')}
    metadata.update(artifact_set_id='stock_'+example['input_file'].replace('-','_').replace('.json',''),source_artifact_set_id=manifest['artifact_set_id'])
    out=tmp_path/'out'
    result=add_stock(source,out,metadata,spec,resolved)
    assert {'geometry','documents','stock_layout','cost_estimate'}<=set(result['capabilities'])
    assert validate_artifact_set(out,inspect_geometry=False)['status']=='passed'
    evidence=validate_stock_output(out,spec,resolved,metadata)
    assert evidence['cut_tree_replay']=='passed' and evidence['layout_status']=='complete'
    assert (out/'assembly.step').read_bytes()==(source/'assembly.step').read_bytes()
    assert sha256_file(source/'manifest.json')==original_manifest_hash
    old_map=json.loads((source/'step-instance-map.json').read_text());new_map=json.loads((out/'step-instance-map.json').read_text())
    assert old_map['instances']==new_map['instances'] and old_map['assembly_artifact_id']!=new_map['assembly_artifact_id']
    assert old_map['assembly_sha256']==new_map['assembly_sha256']
