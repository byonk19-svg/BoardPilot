import copy
import json
from fractions import Fraction as F
from pathlib import Path

import pytest
from pypdf import PdfReader

from woodwork.application import compile_design
from woodwork.domain import hash_json
from woodwork.recipes import RECIPE_ID, RECIPE_VERSION, installed_catalog, resolve_recipe, manufacturing_plan, validate_recipe_graph

ID='beginner_screws_18_6_36in_bookcase'
VERSION='1.0.0'
LEGACY_FINGERPRINT='eefc2c56d77ebe54fd315049ebe6b867c737cfc8d8586672748be40d0c08bec1'
ROOT=Path(__file__).resolve().parents[1]


def sample(selected=True):
    spec=json.loads((ROOT/'tests/fixtures/bookcase-width-36in.json').read_text())
    if selected:spec['construction']['recipe']={'id':ID,'version':VERSION}
    return spec


def resolved_sample():
    spec=sample(); resolved=compile_design(spec)
    return spec,resolved,resolve_recipe(spec,resolved)


def test_exact_sample_has_a_separate_recipe_and_legacy_identity_is_stable():
    catalog=installed_catalog()
    assert (ID,VERSION) in catalog
    assert hash_json(catalog[(RECIPE_ID,RECIPE_VERSION)])==LEGACY_FINGERPRINT
    before=sample(False); spec,resolved,recipe=resolved_sample()
    assert recipe['status']=='complete'
    assert spec['dimensions']==before['dimensions'] and spec['materials']==before['materials']
    assert recipe['physical_review']=='not_reviewed' and recipe['review_record']['load_rating'] is None
    assert resolved['part_instance_count']==7


@pytest.mark.parametrize('path,value',[
    ('materials.main.actual_thickness_mm','19.05'),('materials.back.actual_thickness_mm','6.35'),
    ('dimensions.outside_depth_mm','355.6'),('dimensions.outside_width_mm','762'),
    ('dimensions.outside_height_mm','1066.8'),('dimensions.fixed_shelf_count',3),
])
def test_different_bookcases_are_not_silently_promoted(path,value):
    spec=sample(); group,key=path.rsplit('.',1); target=spec
    for part in group.split('.'):target=target[part]
    target[key]=value
    resolved=compile_design(spec); recipe=resolve_recipe(spec,resolved)
    assert recipe['status']=='incompatible' and not recipe['operations']
    assert spec['dimensions'][key]==value if group=='dimensions' else spec['materials'][group.split('.')[1]][key]==value


def test_fastener_counts_faces_rays_and_shelf_marks_are_literal_and_consistent():
    spec,resolved,recipe=resolved_sample()
    assert len(recipe['joints'])==14
    hardware={h['hardware_id']:h for h in recipe['hardware']}
    assert hardware['carcass_screw']['required_quantity']==24
    assert hardware['back_screw']['required_quantity']==36
    assert hardware['carcass_screw']['length_mm']=='50.8'
    assert hardware['back_screw']['length_mm']=='15.875'
    main=[j for j in recipe['joints'] if j['method']=='through_side_screw_and_glue']
    assert len(main)==8
    for joint in main:
        points=joint['stations']
        assert len(points)==3
        assert [p['from_front_edge_mm'] for p in points]==['30','149.4','268.8']
        left=joint['machined_instance_id']=='side_left'
        assert all(p['entry_face']==('local_T_positive' if left else 'local_T_negative') for p in points)
        assert all(p['drill_axis_world']==([1,0,0] if left else [-1,0,0]) for p in points)
        assert all(p['entry_world_mm']['x']==('0' if left else '914.4') for p in points)
    assert sorted({p['entry_world_mm']['z'] for j in main for p in j['stations']},key=F)==['9','307.8','606.6','905.4']
    plan=manufacturing_plan(spec,resolved,recipe)
    assert plan['side_left']==plan['side_right'] and plan['side_left']
    assert all('instance_id' not in json.dumps(d) and 'entry_world' not in json.dumps(d) for ds in plan.values() for d in ds)
    assert recipe['preparation_equivalence']['proper_rotation_determinant']==1
    assert recipe['preparation_equivalence']['side_patterns_match'] is True


@pytest.mark.parametrize('mutation', ['entry_face','entry_point','axis','pilot_depth','hardware_length','quantity','missing_joint','cycle','receiving_part','usage_id','hardware_identity','hardware_shorter','unknown_methods','missing_pilots','changed_instructions','front_offset'])
def test_invalid_fastening_cannot_become_complete(mutation):
    spec,resolved,recipe=resolved_sample(); graph={key:copy.deepcopy(recipe[key]) for key in ('joints','operations','hardware')}
    joint=next(j for j in graph['joints'] if j['method']=='through_side_screw_and_glue'); station=joint['stations'][0]
    if mutation=='entry_face':station['entry_face']='local_T_negative'
    elif mutation=='entry_point':station['entry_world_mm']['z']='10'
    elif mutation=='axis':station['drill_axis_world']=[0,1,0]
    elif mutation=='pilot_depth':station['pilot_into_receiver_mm']='999'
    elif mutation=='hardware_length':graph['hardware'][0]['length_mm']='12'
    elif mutation=='quantity':joint['hardware'][0]['quantity']=2
    elif mutation=='missing_joint':graph['joints'].pop()
    elif mutation=='cycle':graph['operations'][0]['depends_on']=[graph['operations'][-1]['operation_id']]
    elif mutation=='usage_id':joint['hardware'][0]['hardware_id']='back_screw'
    elif mutation=='hardware_identity':graph['hardware'][0]['type']='Drywall screw'
    elif mutation=='hardware_shorter':
        graph['hardware'][0]['length_mm']='40'
        for row in graph['joints']:
            if row['method']=='through_side_screw_and_glue':
                for point in row['stations']:point['screw_penetration_mm']='22'
    elif mutation=='unknown_methods':
        for row in graph['joints']:row['method']='unreviewed_joinery'
    elif mutation=='missing_pilots':
        graph['operations']=[o for o in graph['operations'] if o['operation_id']!='dry_fit_and_pilot']
        next(o for o in graph['operations'] if o['operation_id']=='attach_left')['depends_on']=['clearance_holes']
    elif mutation=='changed_instructions':graph['operations'][0]['actions']=['Skip offcut checks']
    elif mutation=='front_offset':station['from_front_edge_mm']='1'
    else:station['receiving_instance_id']='back'
    checked=validate_recipe_graph(graph,resolved)
    assert not checked['technical_completeness'] and checked['findings']


@pytest.mark.parametrize('paper',['letter','a4'])
def test_beginner_layout_has_plain_front_pages_and_one_illustration_per_checked_step(tmp_path,paper):
    from woodwork.exports.beginner_packet import BeginnerPacket
    spec=sample(); spec['documents']['paper_size']=paper; resolved=compile_design(spec); recipe=resolve_recipe(spec,resolved)
    measured={'instances':[{'instance_id':i['instance_id'],'world_aabb_mm':{key:[float(i['world_aabb_mm'][key][axis]) for axis in 'xyz'] for key in ('min','max')}} for i in resolved['part_instances']]}
    metadata={'revision_id':'beginner-layout-check','revision_number':1,'spec_sha256':resolved['spec_sha256'],'source_artifact_set_id':'layout-only-no-native-claim'}
    path=tmp_path/'guide.pdf'; packet=BeginnerPacket(path,spec,resolved,metadata,measured,recipe); count=packet.save()
    pages=PdfReader(path).pages; text=[p.extract_text() for p in pages]; front=' '.join(text[:3])
    assert len(pages)==count and count>=15
    assert 'Build your bookcase' in text[0] and 'Left side' in front and '878.4' in front
    assert 'local_T' not in front and 'manufacturing fingerprint' not in front and 'recipe_unselected' not in front
    assert len(packet.guide_page_map)==len(recipe['operations'])
    assert {p['operation_id'] for p in packet.guide_page_map}=={o['operation_id'] for o in recipe['operations']}
    for item in packet.guide_page_map:
        page_text=text[item['page']-1]
        assert item['title'] in page_text and item['figure_label'] in page_text
    whole=' '.join(' '.join(text).split())
    for expected in ['307.8','606.6','35 mm','12 mm','24','36','Do not over-countersink the back','not a full-size drilling template','physical build has not been performed','No shelf load rating']:
        assert expected.lower() in whole.lower()
    assert all('beginner-layout-check' in page for page in text)
    assert all(i['instance_id'] in whole for i in resolved['part_instances'])


@pytest.mark.parametrize('complete',[True,False])
def test_document_selection_and_step_coverage(tmp_path,monkeypatch,complete):
    # Renderer integration only; inert CAD and synthetic native captions cannot
    # establish CAD acceptance. The separate browser case uses native output.
    from test_export_units import renderer_source, synthetic_native_drawings
    from woodwork.exports import documents
    from woodwork.exports.core import write_json
    from woodwork.cad_adapter.verifier import CadValidationError
    spec=sample()
    if not complete:spec['dimensions']['outside_width_mm']='762'
    resolved=compile_design(spec)
    measured={'instances':[{'instance_id':i['instance_id'],'world_aabb_mm':{key:[float(i['world_aabb_mm'][key][axis]) for axis in 'xyz'] for key in ('min','max')}} for i in resolved['part_instances']]}
    metadata={'project_id':'renderer-only','revision_id':'beginner-doc-check','revision_number':1,'spec_sha256':resolved['spec_sha256'],'resolved_sha256':resolved['resolved_sha256'],'source_artifact_set_id':'renderer-only-source'}
    source,_=renderer_source(tmp_path,spec,resolved,metadata)
    monkeypatch.setattr(documents,'validate_artifact_set',lambda *a,**k:{'geometry':measured})
    monkeypatch.setattr(documents,'generate_native_drawings',synthetic_native_drawings)
    out=tmp_path/'documents';documents.add_documents(source,out,metadata,spec,resolved)
    evidence=documents.validate_documents(out,spec,resolved,metadata)
    if not complete:
        assert evidence['beginner_guide'] is None and not (out/'beginner-guide.json').exists()
        assert 'incompatible' in ''.join(p.extract_text() for p in PdfReader(out/'design-packet.pdf').pages)
        return
    assert evidence['beginner_guide']['illustrated_operations']==10
    guide=json.loads((out/'beginner-guide.json').read_text());guide['steps'].pop()
    write_json(out/'beginner-guide.json',guide)
    with pytest.raises(CadValidationError,match='coverage'):documents.validate_documents(out,spec,resolved,metadata)


def test_a_figure_label_without_vectors_is_not_an_illustrated_guide(tmp_path,monkeypatch):
    from test_export_units import renderer_source, synthetic_native_drawings
    from woodwork.exports import documents
    from woodwork.exports.beginner_packet import BeginnerPacket
    from woodwork.cad_adapter.verifier import CadValidationError
    spec,resolved,_=resolved_sample()
    measured={'instances':[{'instance_id':i['instance_id'],'world_aabb_mm':{key:[float(i['world_aabb_mm'][key][axis]) for axis in 'xyz'] for key in ('min','max')}} for i in resolved['part_instances']]}
    metadata={'project_id':'renderer-only','revision_id':'missing-figure','revision_number':1,'spec_sha256':resolved['spec_sha256'],'resolved_sha256':resolved['resolved_sha256'],'source_artifact_set_id':'renderer-only-source'}
    source,_=renderer_source(tmp_path,spec,resolved,metadata)
    monkeypatch.setattr(documents,'validate_artifact_set',lambda *a,**k:{'geometry':measured})
    monkeypatch.setattr(documents,'generate_native_drawings',synthetic_native_drawings)
    monkeypatch.setattr(BeginnerPacket,'draw_step',lambda *a:None)
    with pytest.raises(CadValidationError,match='vectors'):documents.add_documents(source,tmp_path/'documents',metadata,spec,resolved)
