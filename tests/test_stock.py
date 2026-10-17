"""Supplied stock oracle plus independent cut-tree tamper regressions."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import pytest

from woodwork.domain import compile_project
from woodwork.templates import default_project_spec
from woodwork.stock import StockError, calculate_costs, hardware_purchase, pack_sheet, plan_stock, validate_plan, validate_sheet

FIXTURES=Path(__file__).parent/'fixtures'
EXPECTED=json.loads((FIXTURES/'bookcase-expected.json').read_text(encoding='utf-8'))
EXACT=json.loads((FIXTURES/'kerf-exact-fit.json').read_text(encoding='utf-8'))


def contains(actual,expected):
    if isinstance(expected,dict):
        for key,value in expected.items():contains(actual[key],value)
    elif isinstance(expected,list):
        assert len(actual)==len(expected)
        for a,e in zip(actual,expected,strict=True):contains(a,e)
    else:assert actual==expected


def compile_stock(spec=None):
    spec=spec or default_project_spec()
    resolved=compile_project(spec)
    return spec,resolved,plan_stock(spec,resolved)


def test_full_baseline_stock_oracle_and_independent_cut_replay():
    spec,resolved,plan=compile_stock()
    assert plan['status']=='complete'
    assert plan['optimality']=='not_claimed'
    assert plan['spec_sha256']==resolved['spec_sha256']
    assert plan['resolved_sha256']==resolved['resolved_sha256']
    contains(plan['sheets'],EXPECTED['baseline_stock_layout'])
    assert validate_plan(plan,spec,resolved)['status']=='passed'
    assert [len(sheet['internal_cuts']) for sheet in plan['sheets']]==[9,2]
    assert [row['sheet_count'] for row in plan['stock_counts']]==[1,1]
    assert plan_stock(spec,resolved)==plan


def test_exact_fit_has_two_kerfs_and_no_trailing_release():
    sheet=pack_sheet(EXACT['parts'],EXACT['sheet'],EXACT['kerf_mm'])
    assert sheet['unplaced_instance_ids']==[]
    assert [(leaf['instance_id'],leaf['x_mm'],leaf['y_mm']) for leaf in sheet['leaf_regions'] if leaf['kind']=='part']==[(r['id'],r['x_mm'],r['y_mm']) for r in EXACT['expected_placements']]
    assert len(sheet['internal_cuts'])==2
    assert [(c['axis'],c['kerf_start_mm'],c['kerf_mm']) for c in sheet['internal_cuts']]==[('x','100','3.2'),('x','203.2','3.2')]
    assert sheet['area_mm2']['parts']=='30000'
    assert sheet['area_mm2']['internal_kerf']=='640'
    assert sheet['area_mm2']['original_sheet']=='30640'
    assert validate_sheet(sheet,EXACT['parts'],EXACT['sheet'],'3.2','0')['status']=='passed'


@pytest.mark.parametrize('length',['306.3','300'])
def test_equal_area_and_missing_kerf_capacity_do_not_fit_three(length):
    stock={**EXACT['sheet'],'length_mm':length}
    sheet=pack_sheet(EXACT['parts'],stock,'3.2')
    assert len([r for r in sheet['leaf_regions'] if r['kind']=='part'])<3
    assert sheet['unplaced_instance_ids']
    validate_sheet(sheet,EXACT['parts'],stock,'3.2','0')


def test_trimmed_exact_fit_and_length_allowance():
    stock={'length_mm':'316.4','width_mm':'110','grain_axis':'length'}
    sheet=pack_sheet(EXACT['parts'],stock,'3.2','5')
    assert [(p['x_mm'],p['y_mm']) for p in sheet['leaf_regions'] if p['kind']=='part']==[('5','5'),('108.2','5'),('211.4','5')]
    assert sheet['unplaced_instance_ids']==[]
    validate_sheet(sheet,EXACT['parts'],stock,'3.2','5')
    parts=[{**p,'length_mm':'102'} for p in EXACT['parts']]
    assert pack_sheet(parts,EXACT['sheet'],'3.2')['unplaced_instance_ids']
    assert not pack_sheet(parts,{**EXACT['sheet'],'length_mm':'312.4'},'3.2')['unplaced_instance_ids']


def test_allowance_changes_only_stock_blanks_and_partition():
    spec=default_project_spec();spec['manufacturing']['rough_allowance_per_edge_mm']='1'
    spec,resolved,plan=compile_stock(spec)
    assert plan['status']=='complete'
    parts=[leaf for sheet in plan['sheets'] for leaf in sheet['leaf_regions'] if leaf['kind']=='part']
    side=next(p for p in parts if p['instance_id']=='side_left')
    assert (side['length_mm'],side['width_mm'])==('916.4','300.8')
    assert resolved['part_definitions'][0]['finished_mm']['length_mm']=='914.4'
    validate_plan(plan,spec,resolved)


def test_grain_locked_short_sheet_reports_named_unplaced_parts():
    spec=default_project_spec();spec['manufacturing']['stock_sheets'][0]['length_mm']='900'
    spec,resolved,plan=compile_stock(spec)
    assert plan['status']=='incomplete'
    assert {'side_left','side_right'}<=set(plan['unplaced_instance_ids'])
    assert all(p['rotation_deg'] in (0,180) for s in plan['sheets'] for p in s['leaf_regions'] if p['kind']=='part')
    assert plan['costs']['estimate_complete'] is False
    assert plan['costs']['sheet_purchase_subtotal_usd'] is None
    validate_plan(plan,spec,resolved)


def test_missing_and_incompatible_grain_stock_keep_geometry_valid():
    for mode in ('missing','grain'):
        spec=default_project_spec()
        if mode=='missing':spec['manufacturing']['stock_sheets']=spec['manufacturing']['stock_sheets'][1:]
        else:spec['manufacturing']['stock_sheets'][0]['grain_axis']='none'
        _,resolved,plan=compile_stock(spec)
        assert resolved['part_instance_count']==7
        assert plan['status']=='incomplete'
        assert len(plan['unplaced_instance_ids'])==6


def test_nondirectional_parts_can_rotate_without_violating_source_grain():
    spec=default_project_spec();spec['materials']['main']['face_grain']='none';spec['manufacturing']['stock_sheets'][0]['length_mm']='900';spec['manufacturing']['stock_sheets'][0]['grain_axis']='none'
    spec,resolved,plan=compile_stock(spec)
    assert plan['status']=='complete'
    sides=[p for s in plan['sheets'] for p in s['leaf_regions'] if p['instance_id'] in ('side_left','side_right')]
    assert all(p['rotation_deg'] in (90,270) for p in sides)
    validate_plan(plan,spec,resolved)


def test_known_sheet_prices_and_unknown_remaining_project_expenses():
    spec=default_project_spec();spec['manufacturing']['stock_sheets'][0]['unit_price']='70.00';spec['manufacturing']['stock_sheets'][1]['unit_price']='25.00'
    spec,resolved,plan=compile_stock(spec)
    costs=calculate_costs(plan,spec,resolved)
    assert costs['known_sheet_subtotal_usd']=='95.00'
    assert costs['sheet_purchase_subtotal_usd']=='95.00'
    assert costs['sheet_prices_complete'] is True
    assert costs['project_total_usd'] is None
    assert 'hardware' in costs['excluded_items']
    assert costs['consumed_allocation_method']=='finished_face_area / original_sheet_face_area'
    assert costs['currency']=='USD'


def test_missing_prices_are_unknown_and_partial_known_subtotal_is_explicit():
    spec=default_project_spec();spec['manufacturing']['stock_sheets'][0]['unit_price']='70.00'
    _,_,plan=compile_stock(spec)
    assert plan['costs']['known_sheet_subtotal_usd']=='70.00'
    assert plan['costs']['sheet_purchase_subtotal_usd'] is None
    assert plan['costs']['sheet_prices_complete'] is False
    assert plan['costs']['unknown_price_stock_ids']==['back_sheet']
    assert any(row['purchased_cost_usd'] is None for row in plan['costs']['rows'])


def test_explicit_hardware_pack_arithmetic():
    result=hardware_purchase(24,10,'5.25')
    assert result=={'required_count':24,'pack_size':10,'packs_purchased':3,'supplied_count':30,'pack_price_usd':'5.25','purchase_cost_usd':'15.75'}
    assert hardware_purchase(24,10,None)['purchase_cost_usd'] is None


@pytest.mark.parametrize('mutation',['missing_cut','duplicate_part','overlap','wrong_pool','fake_instance','wrong_kerf','grain_rotation','area','source','fingerprint'])
def test_independent_validator_rejects_tampered_plans(mutation):
    spec,resolved,plan=compile_stock();bad=deepcopy(plan);sheet=bad['sheets'][0]
    part=next(p for p in sheet['leaf_regions'] if p['kind']=='part')
    if mutation=='missing_cut':sheet['internal_cuts'].pop()
    elif mutation=='duplicate_part':sheet['leaf_regions'].append(deepcopy(part))
    elif mutation=='overlap':part['x_mm']='11'
    elif mutation=='wrong_pool':sheet['material_id']='plywood_back'
    elif mutation=='fake_instance':part['instance_id']='does_not_exist'
    elif mutation=='wrong_kerf':sheet['internal_cuts'][0]['kerf_mm']='0'
    elif mutation=='grain_rotation':part['rotation_deg']=90
    elif mutation=='area':sheet['area_mm2']['parts']='1'
    elif mutation=='source':sheet['internal_cuts'][0]['source_rectangle']['length_mm']='1'
    else:bad['spec_sha256']='0'*64
    with pytest.raises(StockError):validate_plan(bad,spec,resolved)


@pytest.mark.parametrize('trim',['1','3.199999'])
def test_positive_trim_smaller_than_kerf_is_reported_without_invalidating_geometry(trim):
    spec=default_project_spec();spec['manufacturing']['sheet_edge_trim_mm']=trim
    _,resolved,plan=compile_stock(spec)
    assert resolved['part_instance_count']==7
    assert plan['status']=='incomplete'
    assert 'TRIM_SMALLER_THAN_KERF' in {f['code'] for f in plan['findings']}


def test_small_leftover_requires_a_fully_contained_release_cut():
    part=[{'id':'piece','length_mm':'100','width_mm':'100','grain_axis':'length'}]
    assert pack_sheet(part,{'length_mm':'101','width_mm':'100'},'3.2')['unplaced_instance_ids']==['piece']
    assert not pack_sheet(part,{'length_mm':'103.2','width_mm':'100'},'3.2')['unplaced_instance_ids']


def test_different_width_rows_produce_extra_executable_release_cuts():
    parts=[{'id':'wide','length_mm':'120','width_mm':'100','grain_axis':'none'},{'id':'short','length_mm':'100','width_mm':'60','grain_axis':'none'}]
    stock={'length_mm':'240','width_mm':'140','grain_axis':'none'}
    sheet=pack_sheet(parts,stock,'3.2')
    assert sheet['unplaced_instance_ids']==[]
    assert any(c['axis']=='y' and c['source_rectangle']['width_mm']=='100' for c in sheet['internal_cuts'])
    validate_sheet(sheet,parts,stock,'3.2','0')


@pytest.mark.parametrize('fixture',EXPECTED['fixtures'],ids=lambda e:e['input_file'])
def test_all_supplied_projects_have_verified_layout_or_honest_unplaced_result(fixture):
    spec=json.loads((FIXTURES/fixture['input_file']).read_text(encoding='utf-8'))
    spec,resolved,plan=compile_stock(spec)
    assert plan['status']=='complete'
    assert sum(row['sheet_count'] for row in plan['stock_counts'])>=2
    validate_plan(plan,spec,resolved)
    for sheet in plan['sheets']:
        areas=sheet['area_mm2']
        assert Fraction(areas['parts'])+Fraction(areas['internal_kerf'])+Fraction(areas['offcuts'])==Fraction(areas['usable'])


def test_area_lower_bound_is_not_the_purchasing_quantity_on_failed_layout():
    spec=default_project_spec();spec['manufacturing']['stock_sheets'][0]['length_mm']='900'
    _,_,plan=compile_stock(spec)
    main=next(row for row in plan['area_lower_bounds'] if row['material_id']=='plywood_main')
    assert main['sufficiency']=='not_established'
    assert main['sheets_lower_bound']>=1
    assert plan['status']=='incomplete'


def test_declared_stock_order_and_multiple_sheet_types_remain_valid():
    spec=default_project_spec();spec['manufacturing']['stock_sheets'].reverse()
    spec,resolved,plan=compile_stock(spec)
    assert plan['status']=='complete'
    validate_plan(plan,spec,resolved)
    main=next(s for s in spec['manufacturing']['stock_sheets'] if s['material_id']=='plywood_main')
    alternate={**main,'stock_id':'main_alternate','length_mm':'3000'}
    spec['manufacturing']['stock_sheets'].append(alternate)
    spec,resolved,plan=compile_stock(spec)
    assert {s['stock_id'] for s in plan['sheets'] if s['material_id']=='plywood_main'}=={'main_sheet'}


@pytest.mark.parametrize('field',['bound','bound_claim','cost'])
def test_reporting_claims_are_independently_bound_to_stock_and_prices(field):
    spec=default_project_spec();spec['manufacturing']['stock_sheets'][0]['unit_price']='70.00';spec['manufacturing']['stock_sheets'][1]['unit_price']='25.00'
    spec,resolved,plan=compile_stock(spec)
    if field=='bound':plan['area_lower_bounds'][0]['sheets_lower_bound']=0
    elif field=='bound_claim':plan['area_lower_bounds'][0]['sufficiency']='sufficient'
    else:plan['costs']['sheet_purchase_subtotal_usd']='1.00'
    with pytest.raises(StockError):validate_plan(plan,spec,resolved)
