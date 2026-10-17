"""Real PDF text checks; synthetic native sheets are renderer-only test fixtures."""
import json
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from woodwork.application import compile_design
from woodwork.cad_adapter import validate_artifact_set
from woodwork.cad_adapter.verifier import CadValidationError
from woodwork.exports import cumulative, documents, stock
from woodwork.exports.core import artifact_record, sha256_file, write_core_records, write_json
from woodwork.recipes import resolve_recipe
from woodwork.stock import plan_stock
from woodwork.templates import default_project_spec


def pdf_text(path):
    return ' '.join(' '.join(page.extract_text() for page in PdfReader(path).pages).split())


def renderer_inputs(units='dual', denominator=64, project_name=None):
    spec=default_project_spec()
    spec['documents']['schedule_units']=units
    spec['display']['fraction_denominator']=denominator
    if project_name is not None:spec['project_name']=project_name
    resolved=compile_design(spec)
    measured={'instances':[{'instance_id':item['instance_id'], 'world_aabb_mm':{
        key:[float(item['world_aabb_mm'][key][axis]) for axis in 'xyz']
        for key in ('min','max')}} for item in resolved['part_instances']]}
    metadata={'project_id':'renderer-only-project','revision_id':'renderer-only-revision',
              'revision_number':1,'spec_sha256':resolved['spec_sha256'],
              'resolved_sha256':resolved['resolved_sha256'],'source_artifact_set_id':'renderer-only-source'}
    return spec,resolved,measured,metadata


def test_metric_packet_schedules_use_only_metric_dimensions(tmp_path):
    spec,resolved,measured,metadata=renderer_inputs('mm')
    path=tmp_path/'metric.pdf'
    documents.Packet(path,spec,resolved,metadata,measured,resolve_recipe(spec,resolved)).save()
    text=pdf_text(path)
    assert '298.8 mm' in text and '726 mm' in text
    assert 'in (' not in text


@pytest.mark.parametrize('denominator,expected',[(16,'11 3/4'),(32,'11 3/4')])
def test_dual_packet_uses_selected_fraction_precision(tmp_path,denominator,expected):
    spec,resolved,measured,metadata=renderer_inputs('dual',denominator)
    path=tmp_path/'dual.pdf'
    documents.Packet(path,spec,resolved,metadata,measured,resolve_recipe(spec,resolved)).save()
    text=pdf_text(path)
    assert f'approx. {expected} in (298.8 mm)' in text
    assert '11 49/64 in (298.8 mm)' not in text
    assert '1 in (25.4 mm)' in text


@pytest.mark.parametrize('units,denominator,expected',[
    ('mm',64,'Original sheet: 2440 mm x 1220 mm'),
    ('dual',16,'Original sheet: approx. 96 1/16 in (2440 mm) x approx. 48 1/16 in (1220 mm)'),
])
def test_stock_pdf_sheet_labels_follow_options_and_cut_coordinates_stay_metric(tmp_path,units,denominator,expected):
    spec,resolved,_,metadata=renderer_inputs(units,denominator)
    path=tmp_path/'stock.pdf'
    stock.draw_stock_pdf(path,plan_stock(spec,resolved),spec,metadata)
    text=pdf_text(path)
    assert expected in text
    assert 'coordinates from the original sheet corner (mm)' in text
    assert 'kerf begins 308.8 mm' in text


def renderer_source(tmp_path,spec,resolved,metadata):
    """Core records only, with explicit inert CAD placeholders; no CAD acceptance."""
    source=tmp_path/'source';source.mkdir()
    write_core_records(source,spec,resolved,metadata)
    (source/'assembly.step').write_text('renderer-only inert STEP placeholder')
    (source/'parts').mkdir()
    for part in resolved['part_definitions']:
        (source/f"parts/{part['definition_id']}.step").write_text('renderer-only inert STEP placeholder')
    write_json(source/'build-inputs.json',{'spec_sha256':resolved['spec_sha256'],'resolved_sha256':resolved['resolved_sha256']})
    write_json(source/'step-instance-map.json',{'assembly_artifact_id':'renderer-only-assembly'})
    records=[artifact_record(source,path.relative_to(source).as_posix(),'step' if path.suffix=='.step' else 'json','application/octet-stream',metadata)
             for path in source.rglob('*') if path.is_file()]
    manifest={**metadata,'artifact_set_id':metadata['source_artifact_set_id'],'build_key_sha256':'renderer-only-build',
              'capabilities':['geometry'],'validation':{'documents':'not_requested'},
              'versions':{'recipe_fingerprint':None},'artifacts':records}
    write_json(source/'manifest.json',manifest)
    return source,manifest


def synthetic_native_drawings(out_dir,resolved,metadata):
    """Exercise document binding checks without invoking native CAD."""
    folder=out_dir/'drawings';folder.mkdir(exist_ok=True)
    for part in resolved['part_definitions']:
        path=folder/f"{part['definition_id']}-metric.pdf"
        pdf=canvas.Canvas(str(path),pagesize=(A4[1],A4[0]))
        dims=part['finished_mm']
        pdf.drawString(20,30,f"L {dims['length_mm']} W {dims['width_mm']} T {dims['thickness_mm']}")
        pdf.save()
        writer=PdfWriter();writer.append(PdfReader(path))
        writer.add_metadata({'/WoodworkRevision':metadata['revision_id'],'/WoodworkSpecSHA256':metadata['spec_sha256'],
            '/WoodworkDefinition':part['definition_id'],'/WoodworkUnits':'mm',
            '/WoodworkSourceStepSHA256':sha256_file(out_dir/f"parts/{part['definition_id']}.step")})
        with path.open('wb') as stream:writer.write(stream)


def test_new_document_provenance_binds_actual_selected_format_and_formatter(tmp_path,monkeypatch):
    spec,resolved,measured,metadata=renderer_inputs('mm',16)
    source,_=renderer_source(tmp_path,spec,resolved,metadata)
    monkeypatch.setattr(documents,'validate_artifact_set',lambda *a,**k:{'geometry':measured})
    monkeypatch.setattr(documents,'generate_native_drawings',synthetic_native_drawings)
    out=tmp_path/'documents'
    documents.add_documents(source,out,metadata,spec,resolved)
    inputs=json.loads((out/'build-inputs.json').read_text())
    assert inputs['documents_version']!='1.0.0'
    assert inputs['schedule_formatting']=={'units':'mm','fraction_denominator':16}
    assert inputs['renderer_sha256']['dimensions']==sha256_file(Path(documents.__file__).with_name('dimensions.py'))
    evidence=documents.validate_documents(out,spec,resolved,metadata)
    assert evidence['application_units']=='mm'
    assert evidence['application_fraction_denominator'] is None
    assert evidence['native_units']=='mm'
    assert 'in (' not in pdf_text(out/'design-packet.pdf')
    inputs['schedule_formatting']['units']='dual';write_json(out/'build-inputs.json',inputs)
    with pytest.raises(CadValidationError,match='formatting'):
        documents.validate_documents(out,spec,resolved,metadata)
    inputs['schedule_formatting']['units']='mm'
    # A valid packet cannot be relabeled as using an unknown renderer contract.
    inputs['documents_version']='999.0.0';write_json(out/'build-inputs.json',inputs)
    with pytest.raises(CadValidationError,match='version'):
        documents.validate_documents(out,spec,resolved,metadata)


def test_new_stock_provenance_binds_selected_format_and_formatter(tmp_path,monkeypatch):
    spec,resolved,_,metadata=renderer_inputs('mm',16)
    source,_=renderer_source(tmp_path,spec,resolved,metadata)
    monkeypatch.setattr(cumulative,'validate_artifact_set',lambda *a,**k:None)
    monkeypatch.setattr(stock,'validate_artifact_set',lambda *a,**k:None)
    out=tmp_path/'stock'
    stock.add_stock(source,out,metadata,spec,resolved)
    inputs=json.loads((out/'build-inputs.json').read_text())
    assert inputs['stock_export_version']!='1.0.1'
    assert inputs['schedule_formatting']=={'units':'mm','fraction_denominator':16}
    assert inputs['dimension_formatter_sha256']==sha256_file(Path(stock.__file__).with_name('dimensions.py'))
    assert 'Original sheet: 2440 mm x 1220 mm' in pdf_text(out/'stock-layout.pdf')
    evidence=stock.validate_stock_output(out,spec,resolved,metadata)
    assert evidence['application_units']=='mm' and evidence['application_fraction_denominator'] is None
    inputs['stock_export_version']='999.0.0';write_json(out/'build-inputs.json',inputs)
    with pytest.raises(CadValidationError,match='version'):
        stock.validate_stock_output(out,spec,resolved,metadata)


def test_metric_validation_keeps_valid_user_labels_containing_in_parenthesis(tmp_path,monkeypatch):
    spec,resolved,measured,metadata=renderer_inputs('mm',16,'Shelf in (garage)')
    source,_=renderer_source(tmp_path,spec,resolved,metadata)
    monkeypatch.setattr(documents,'validate_artifact_set',lambda *a,**k:{'geometry':measured})
    monkeypatch.setattr(documents,'generate_native_drawings',synthetic_native_drawings)
    out=tmp_path/'documents'
    documents.add_documents(source,out,metadata,spec,resolved)
    assert documents.validate_documents(out,spec,resolved,metadata)['application_units']=='mm'
    assert 'Shelf in (garage)' in pdf_text(out/'design-packet.pdf')


def test_metric_provenance_does_not_accept_a_dual_unit_packet(tmp_path,monkeypatch):
    spec,resolved,measured,metadata=renderer_inputs('mm',16)
    source,_=renderer_source(tmp_path,spec,resolved,metadata)
    monkeypatch.setattr(documents,'validate_artifact_set',lambda *a,**k:{'geometry':measured})
    monkeypatch.setattr(documents,'generate_native_drawings',synthetic_native_drawings)
    out=tmp_path/'documents'
    documents.add_documents(source,out,metadata,spec,resolved)
    dual_spec={**spec,'documents':{**spec['documents'],'schedule_units':'dual'}}
    documents.Packet(out/'design-packet.pdf',dual_spec,resolved,metadata,measured,resolve_recipe(spec,resolved)).save()
    with pytest.raises(CadValidationError,match='unit reference|dimension'):
        documents.validate_documents(out,spec,resolved,metadata)


@pytest.mark.parametrize('sample',['reference-bookcase','authored-bookcase'])
def test_legacy_verified_dual64_packet_keeps_its_original_checks(sample):
    root=Path(__file__).resolve().parents[1]/'samples'/sample
    assert validate_artifact_set(root,inspect_geometry=False)['status']=='passed'
    spec=json.loads((root/'project.json').read_text())
    resolved=json.loads((root/'resolved-project.json').read_text())
    manifest=json.loads((root/'manifest.json').read_text())
    document_inputs=json.loads((root/'build-inputs.json').read_text())['source_inputs']
    metadata={**manifest,'source_artifact_set_id':document_inputs['source_artifact_set_id']}
    evidence=documents.validate_documents(root,spec,resolved,metadata)
    assert evidence['application_units']=='dual'
    assert evidence['application_fraction_denominator']==64
    # Stock and document source chains retain the same historical renderer policy.
    assert stock.validate_stock_output(root,spec,resolved,manifest)['application_units']=='dual'
    if sample=='reference-bookcase':
        assert 'approx. 11 49/64 in (298.8 mm)' in pdf_text(root/'design-packet.pdf')
