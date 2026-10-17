"""Deterministic first-fit rows and executable guillotine cuts, without optimality claims."""
from copy import deepcopy
from fractions import Fraction

from woodwork.application import compile_design
from woodwork.domain import DomainError, canonical_json, exact_decimal, finding

from .common import Rectangle, StockError, expanded_parts, mm, part_input, require, split_rectangle


def _releasable(used,available,kerf):
    remaining=available-used
    return remaining==0 or remaining>=kerf


def _rows_fit(rows,length,width,kerf):
    total=sum((row['height'] for row in rows),Fraction(0))+max(0,len(rows)-1)*kerf
    if total>width or not _releasable(total,width,kerf):return False
    for row in rows:
        used=sum((p['placed_length'] for p in row['parts']),Fraction(0))+(len(row['parts'])-1)*kerf
        if used>length or not _releasable(used,length,kerf):return False
        if any(not _releasable(p['placed_width'],row['height'],kerf) for p in row['parts']):return False
    return True


def _cut(cuts,regions,source,axis,start,kerf,low_id,high_id,prefix='cut'):
    rect=regions.pop(source)
    low,band,high=split_rectangle(rect,axis,start,kerf)
    require(low.length>=0 and low.width>=0 and high.length>=0 and high.width>=0,'Generated cut cannot fit its full kerf.')
    low_id=low_id if low.area>0 else None
    high_id=high_id if high.area>0 else None
    cuts.append({'cut_id':f'{prefix}_{len(cuts)+1:02d}','source_region':source,'source_rectangle':rect.record(),'axis':axis,
                 'kerf_start_mm':exact_decimal(start),'kerf_mm':exact_decimal(kerf),'low_child':low_id,'high_child':high_id,'kerf_rectangle':band.record()})
    if low_id is not None:regions[low_id]=low
    if high_id is not None:regions[high_id]=high


def _trim(length,width,trim,kerf):
    original=Rectangle(Fraction(0),Fraction(0),length,width)
    if not trim:return [],[{'region_id':'usable',**original.record()}]
    regions={'original':original};cuts=[]
    _cut(cuts,regions,'original','x',trim-kerf,kerf,'discard_left','after_left','trim')
    _cut(cuts,regions,'after_left','x',length-trim,kerf,'trimmed_x','discard_right','trim')
    _cut(cuts,regions,'trimmed_x','y',trim-kerf,kerf,'discard_front','after_front','trim')
    _cut(cuts,regions,'after_front','y',width-trim,kerf,'usable','discard_back','trim')
    return cuts,[{'region_id':key,**rect.record()} for key,rect in regions.items()]


def pack_sheet(parts,sheet,kerf_mm,trim_mm='0'):
    """Pack one physical sheet; unplaced IDs are a heuristic result for this sheet."""
    require(isinstance(parts,list) and len(parts)<=256,'A sheet request supports at most 256 physical blanks.')
    parsed=[part_input(part) for part in parts]
    require(len({p['id'] for p in parsed})==len(parsed),'Duplicate requested physical part.')
    length,width,kerf,trim=mm(sheet['length_mm']),mm(sheet['width_mm']),mm(kerf_mm),mm(trim_mm)
    grain=sheet.get('grain_axis','length')
    require(grain in ('length','none'),'Unknown stock grain policy.')
    require(length>2*trim and width>2*trim,'Trim-adjusted stock must be positive.')
    require(not 0<trim<kerf,'Positive trim smaller than kerf is unsupported.','TRIM_SMALLER_THAN_KERF','manufacturing.sheet_edge_trim_mm')
    usable_length,usable_width=length-2*trim,width-2*trim
    rows=[];unplaced=[]
    for part in sorted(parsed,key=lambda p:(-p['length'],-p['width'],p['id'])):
        if part['grain']!='none' and grain!='length':unplaced.append(part['id']);continue
        options=[(0,part['length'],part['width'])]
        if part['grain']=='none':options.append((90,part['width'],part['length']))
        placed=False
        # Existing rows first; orientation preference remains stable within each row.
        for index in range(len(rows)+1):
            for rotation,l,w in options:
                candidate=deepcopy(rows)
                placement={**part,'placed_length':l,'placed_width':w,'rotation':rotation}
                if index==len(rows):candidate.append({'height':w,'parts':[placement]})
                else:candidate[index]['parts'].append(placement);candidate[index]['height']=max(candidate[index]['height'],w)
                if _rows_fit(candidate,usable_length,usable_width,kerf):rows=candidate;placed=True;break
            if placed:break
        if not placed:unplaced.append(part['id'])
    usable=Rectangle(trim,trim,usable_length,usable_width)
    regions={'usable':usable};cuts=[];leaves=[];strips=[];source='usable'
    special_back=len(rows)==1 and len(rows[0]['parts'])==1 and rows[0]['parts'][0]['id']=='back'
    for index,row in enumerate(rows,1):
        region=regions[source];end=region.y+row['height']
        row_id='back_row' if special_back else f'row_{index}'
        if end<region.y+region.width:
            high=f'remainder_{index}' if index<len(rows) else 'offcut_top'
            _cut(cuts,regions,source,'y',end,kerf,row_id,high)
            strips.append((row_id,row,index))
            if index<len(rows):source=high
        else:strips.append((source,row,index))
    # Offcut above the last row precedes the row leaves in the declared cut order.
    if 'offcut_top' in regions:leaves.append({'region_id':'offcut_top','kind':'offcut','instance_id':None,**regions.pop('offcut_top').record(),'rotation_deg':0})
    for source,row,index in strips:
        for position,part in enumerate(row['parts']):
            region=regions[source];end=region.x+part['placed_length'];last=position==len(row['parts'])-1
            low=part['id'] if part['placed_width']==row['height'] else f'column_{index}_{position+1}'
            if end<region.x+region.length:
                if last:high='offcut_right' if special_back else f'offcut_row_{index}'
                else:high=f'row_{index}_remaining'+('' if len(row['parts'])==2 else '_'+chr(ord('a')+position))
                _cut(cuts,regions,source,'x',end,kerf,low,high)
                part_region=low
                next_source=high
            else:part_region=source;next_source=None
            if part['placed_width']<row['height']:
                column=regions[part_region]
                offcut=f'offcut_column_{index}_{position+1}'
                _cut(cuts,regions,part_region,'y',column.y+part['placed_width'],kerf,part['id'],offcut)
                part_region=part['id']
                if offcut in regions:leaves.append({'region_id':offcut,'kind':'offcut','instance_id':None,**regions.pop(offcut).record(),'rotation_deg':0})
            leaves.append({'region_id':part_region,'kind':'part','instance_id':part['id'],**regions.pop(part_region).record(),'rotation_deg':part['rotation']})
            source=next_source
        if source is not None and source in regions:leaves.append({'region_id':source,'kind':'offcut','instance_id':None,**regions.pop(source).record(),'rotation_deg':0})
    # A sheet on which nothing fits retains its entire usable region as an offcut.
    for key,rect in regions.items():leaves.append({'region_id':key,'kind':'offcut','instance_id':None,**rect.record(),'rotation_deg':0})
    part_area=sum((Rectangle.read(leaf).area for leaf in leaves if leaf['kind']=='part'),Fraction(0))
    offcut_area=sum((Rectangle.read(leaf).area for leaf in leaves if leaf['kind']=='offcut'),Fraction(0))
    kerf_area=sum((Rectangle.read(cut['kerf_rectangle']).area for cut in cuts),Fraction(0))
    trim_cuts,trim_leaves=_trim(length,width,trim,kerf)
    return {'stock_id':sheet.get('stock_id','sheet'),'material_id':sheet.get('material_id','test'),'sheet_count':1,
            'grain_axis':grain,'actual_stock_mm':{'length_mm':exact_decimal(length),'width_mm':exact_decimal(width)},
            'usable_rectangle':usable.record(),'trim_cuts':trim_cuts,'trim_leaf_regions':trim_leaves,
            'internal_cuts':cuts,'leaf_regions':leaves,'unplaced_instance_ids':unplaced,
            'area_mm2':{key:exact_decimal(value) for key,value in {'parts':part_area,'internal_kerf':kerf_area,'offcuts':offcut_area,'usable':usable.area,'reserved_edge_bands':length*width-usable.area,'original_sheet':length*width}.items()}}


def trusted_source(spec,resolved):
    try:trusted=compile_design(spec)
    except DomainError as error:raise StockError(error.findings) from None
    require(canonical_json(trusted)==canonical_json(resolved),'Stock source differs from authoritative project compilation.','STOCK_SOURCE_MISMATCH')
    return trusted['spec']


def plan_stock(spec,resolved):
    from .costs import calculate_costs
    from .validator import validate_plan
    spec=trusted_source(spec,resolved)
    parts=expanded_parts(resolved);stocks=spec['manufacturing']['stock_sheets'];kerf=spec['manufacturing']['saw_kerf_mm'];trim=spec['manufacturing']['sheet_edge_trim_mm']
    sheets=[];unplaced=[];findings=[];counts=[];bounds=[]
    for material in spec['materials'].values():
        pool=[p for p in parts if p['material_id']==material['material_id']]
        compatible=[s for s in stocks if s['material_id']==material['material_id'] and (material['face_grain']=='none' or s['grain_axis']=='length')]
        if not compatible:
            unplaced.extend(p['id'] for p in pool)
            findings.append(finding('COMPATIBLE_STOCK_MISSING','Declare compatible stock for these panels.','manufacturing.stock_sheets',material_id=material['material_id'],instance_ids=[p['id'] for p in pool]));continue
        stock=compatible[0]  # One declared stock type per material, without supplier optimization.
        area=sum((mm(p['length_mm'])*mm(p['width_mm']) for p in pool),Fraction(0))
        usable=(mm(stock['length_mm'])-2*mm(trim))*(mm(stock['width_mm'])-2*mm(trim))
        ratio=area/usable
        bounds.append({'material_id':material['material_id'],'stock_id':stock['stock_id'],'sheets_lower_bound':(ratio.numerator+ratio.denominator-1)//ratio.denominator,'sufficiency':'not_established'})
        pending=pool;sheet_count=0
        while pending:
            try:candidate=pack_sheet(pending,stock,kerf,trim)
            except StockError as error:
                if error.code!='TRIM_SMALLER_THAN_KERF':raise
                findings.extend(error.findings);unplaced.extend(p['id'] for p in pending);break
            placed={leaf['instance_id'] for leaf in candidate['leaf_regions'] if leaf['kind']=='part'}
            if not placed:
                unplaced.extend(p['id'] for p in pending)
                findings.append(finding('STOCK_CANDIDATE_UNPLACED','This stock and conservative cutting policy did not produce a complete candidate. Try another sheet size or grain setting.','manufacturing.stock_sheets',stock_id=stock['stock_id'],instance_ids=[p['id'] for p in pending]));break
            sheet_count+=1
            candidate.update(sheet_index=sheet_count,actual_thickness_mm=material['actual_thickness_mm'],unplaced_instance_ids=[])
            sheets.append(candidate)
            pending=[p for p in pending if p['id'] not in placed]
        if sheet_count:counts.append({'stock_id':stock['stock_id'],'material_id':material['material_id'],'sheet_count':sheet_count})
    plan={'schema_version':'1.0.0','spec_sha256':resolved['spec_sha256'],'resolved_sha256':resolved['resolved_sha256'],
          'status':'incomplete' if unplaced else 'complete','optimality':'not_claimed','sheets':sheets,'stock_counts':counts,
          'unplaced_instance_ids':sorted(unplaced),'findings':findings,'area_lower_bounds':bounds}
    plan['costs']=calculate_costs(plan,spec,resolved)
    plan['validation']=validate_plan(plan,spec,resolved)
    return plan
