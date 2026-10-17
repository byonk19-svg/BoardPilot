from copy import deepcopy
from woodwork.application import compile_design,apply_manufacturing_plan
from woodwork.domain import compile_project,resolved_hash
from woodwork.templates import default_project_spec
from woodwork.recipes import RECIPE_ID,RECIPE_VERSION
from woodwork.cad_adapter.verifier import validate_ledger


def test_null_recipe_preserves_exact_domain_ledger():
    spec=default_project_spec()
    assert compile_design(spec)==compile_project(spec)


def test_supported_recipe_binds_operations_fingerprints_and_trusted_ledger():
    spec=default_project_spec()
    spec['dimensions']['outside_depth_mm']='355.6'
    spec['materials']['main']['actual_thickness_mm']='19.05'
    spec['materials']['back']['actual_thickness_mm']='6.35'
    spec['construction']['recipe']={'id':RECIPE_ID,'version':RECIPE_VERSION}
    ledger=compile_design(spec)
    assert ledger['construction_status']=='recipe_complete'
    assert ledger['construction']['physical_review']=='not_recorded'
    horizontals=next(d for d in ledger['part_definitions'] if d['definition_id']=='panel_horizontal')
    assert len(horizontals['planned_recipe_operations'])==6
    assert horizontals['machining']==[]
    assert ledger['resolved_sha256']==resolved_hash(ledger)
    validate_ledger(spec,ledger)
    from woodwork.cad_adapter.runtime import construction_manifest
    from jsonschema import Draft202012Validator
    import json
    from woodwork.cad_adapter.runtime import SCHEMA
    schema=json.loads(SCHEMA.read_text())['properties']['construction']
    Draft202012Validator(schema).validate(construction_manifest(spec,ledger))


def test_equal_size_boards_different_local_face_patterns_split_manufacturing_groups():
    spec=default_project_spec();spec['dimensions']['outside_width_mm']='950.4'
    ledger=compile_design(spec)
    assert len(ledger['cut_groups'])==2
    old_ids=[i['instance_id'] for i in ledger['part_instances']]
    plan={i:[] for i in old_ids}
    for i in ('top','bottom','shelf_01','shelf_02'):
        plan[i]=[{'operation_type':'test_reference','reference_face':'local_T_positive','local_alignment_mm':{'x':'10','y':'0'}}]
    changed=apply_manufacturing_plan(deepcopy(ledger),plan,'test-fingerprint')
    assert len(changed['cut_groups'])==3
    assert [i['instance_id'] for i in changed['part_instances']]==old_ids
    assert changed['geometry_sha256']==ledger['geometry_sha256']
