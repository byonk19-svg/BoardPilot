"""Independent active-region simulation; never trusts a packing success flag."""
from collections import Counter
from fractions import Fraction

from woodwork.domain import exact_decimal

from .common import Rectangle, StockError, expanded_parts, mm, part_input, require


def _simulate(initial,cuts,leaves,*,kerf):
    active=dict(initial);seen=set(initial);cut_ids=set();removed=Fraction(0)
    require(len(cuts)<=4*max(len(leaves),1)+8,'Cut sequence exceeds its bounded rectangle contract.')
    for cut in cuts:
        require(isinstance(cut['cut_id'],str) and cut['cut_id'] not in cut_ids,'Invalid or duplicate cut identity.');cut_ids.add(cut['cut_id'])
        source=cut['source_region'];require(source in active,'Cut references an unavailable or already consumed region.')
        rect=active.pop(source)
        require(Rectangle.read(cut['source_rectangle'])==rect,'Cut source rectangle does not match the active remnant.')
        require(mm(cut['kerf_mm'])==kerf,'Cut kerf differs from the measured setting.')
        start=mm(cut['kerf_start_mm']);axis=cut['axis']
        # Independently calculate the partition, rather than reusing planner helpers.
        if axis=='x':
            require(rect.x<=start and start+kerf<=rect.x+rect.length,'Full X kerf band exceeds its source.')
            low=Rectangle(rect.x,rect.y,start-rect.x,rect.width)
            band=Rectangle(start,rect.y,kerf,rect.width)
            high=Rectangle(start+kerf,rect.y,rect.x+rect.length-start-kerf,rect.width)
        elif axis=='y':
            require(rect.y<=start and start+kerf<=rect.y+rect.width,'Full Y kerf band exceeds its source.')
            low=Rectangle(rect.x,rect.y,rect.length,start-rect.y)
            band=Rectangle(rect.x,start,rect.length,kerf)
            high=Rectangle(rect.x,start+kerf,rect.length,rect.y+rect.width-start-kerf)
        else:require(False,'Unknown guillotine cut direction.')
        require(Rectangle.read(cut['kerf_rectangle'])==band,'Kerf rectangle does not span the declared source.')
        require(low.area+band.area+high.area==rect.area,'Cut does not partition the source exactly.')
        for key,child in (('low_child',low),('high_child',high)):
            identifier=cut[key]
            if child.area==0:require(identifier is None,'Empty regions must be omitted explicitly.')
            else:
                require(isinstance(identifier,str) and identifier not in seen,'Cut child identity is absent or already used.')
                seen.add(identifier);active[identifier]=child
        removed+=band.area
    leaf_ids=[leaf['region_id'] for leaf in leaves]
    require(len(set(leaf_ids))==len(leaf_ids) and set(leaf_ids)==set(active),'Leaf regions do not exactly classify the active cutting remnants.')
    for leaf in leaves:require(Rectangle.read(leaf)==active[leaf['region_id']],'Leaf bounds disagree with executable cuts.')
    return removed


def validate_sheet(sheet,parts,stock,kerf_mm,trim_mm='0'):
    try:return _validate_sheet(sheet,parts,stock,kerf_mm,trim_mm)
    except StockError:raise
    except (KeyError,TypeError,ValueError,IndexError):raise StockError([{'code':'STOCK_PLAN_INVALID','message':'Malformed stock layout or cut sequence.','field':'stock_plan','details':{}}]) from None


def _validate_sheet(sheet,parts,stock,kerf_mm,trim_mm):
    length,width,kerf,trim=mm(stock['length_mm']),mm(stock['width_mm']),mm(kerf_mm),mm(trim_mm)
    original=Rectangle(Fraction(0),Fraction(0),length,width);usable=Rectangle(trim,trim,length-2*trim,width-2*trim)
    require(usable.length>0 and usable.width>0,'Nonpositive usable stock.')
    require(not 0<trim<kerf,'Unsupported partial-edge trimming band.')
    require(sheet['actual_stock_mm']=={'length_mm':exact_decimal(length),'width_mm':exact_decimal(width)},'Original stock dimensions mismatch.')
    require(Rectangle.read(sheet['usable_rectangle'])==usable,'Usable stock does not match the declared trims.')
    require(sheet['stock_id']==stock.get('stock_id','sheet') and sheet['material_id']==stock.get('material_id','test'),'Wrong stock/material pool.')
    require(sheet['grain_axis']==stock.get('grain_axis','length'),'Stock grain metadata mismatch.')
    if trim:
        trim_removed=_simulate({'original':original},sheet['trim_cuts'],sheet['trim_leaf_regions'],kerf=kerf)
        leaves={leaf['region_id']:Rectangle.read(leaf) for leaf in sheet['trim_leaf_regions']}
        require(leaves.get('usable')==usable,'Trim cuts do not preserve the exact usable rectangle.')
        require(sum((r.area for r in leaves.values()),trim_removed)==original.area,'Original trim area partition mismatch.')
    else:require(not sheet['trim_cuts'],'Zero trim must not add an edge cut.')
    removed=_simulate({'usable':usable},sheet['internal_cuts'],sheet['leaf_regions'],kerf=kerf)
    requested={p['id']:p for p in map(part_input,parts)}
    require(len(requested)==len(parts),'Requested part identities are not unique.')
    placed=[];rectangles=[];part_area=offcut_area=Fraction(0)
    for leaf in sheet['leaf_regions']:
        rect=Rectangle.read(leaf)
        require(rect.length>0 and rect.width>0 and rect.x>=usable.x and rect.y>=usable.y and rect.x+rect.length<=usable.x+usable.length and rect.y+rect.width<=usable.y+usable.width,'Part/offcut exceeds usable stock.')
        if leaf['kind']=='offcut':
            require(leaf['instance_id'] is None,'Offcut cannot claim a physical instance.');offcut_area+=rect.area;continue
        require(leaf['kind']=='part','Unknown leaf classification.')
        identifier=leaf['instance_id'];require(identifier in requested,'Stock leaf references an unknown physical instance.')
        part=requested[identifier];rotation=leaf['rotation_deg']
        require(type(rotation) is int and rotation in (0,90,180,270),'Unsupported part orientation.')
        require(part['material_id']==sheet['material_id'],'Part assigned to another material pool.')
        if part['grain']!='none':require(rotation in (0,180) and sheet['grain_axis']=='length','Grain-locked part rotated or assigned incompatible stock.')
        expected=(part['length'],part['width']) if rotation in (0,180) else (part['width'],part['length'])
        require((rect.length,rect.width)==expected,'Placed part differs from its rough blank dimensions.')
        placed.append(identifier);rectangles.append(rect);part_area+=rect.area
    require(len(set(placed))==len(placed),'Physical part duplicated in one sheet.')
    unplaced=sheet['unplaced_instance_ids']
    require(len(set(unplaced))==len(unplaced) and not set(unplaced)&set(placed) and set(unplaced)|set(placed)==set(requested),'Sheet coverage does not exactly match requested/unplaced instances.')
    for i,first in enumerate(rectangles):
        for second in rectangles[i+1:]:require(first.x+first.length<=second.x or second.x+second.length<=first.x or first.y+first.width<=second.y or second.y+second.width<=first.y,'Placed rectangles overlap.')
    expected={'parts':part_area,'internal_kerf':removed,'offcuts':offcut_area,'usable':usable.area,'reserved_edge_bands':original.area-usable.area,'original_sheet':original.area}
    require(part_area+removed+offcut_area==usable.area,'Usable sheet area does not reconcile.')
    require(sheet['area_mm2']=={key:exact_decimal(value) for key,value in expected.items()},'Published area totals do not match independently replayed cuts.')
    return {'status':'passed','part_count':len(placed),'cut_count':len(sheet['internal_cuts']),'trim_cut_count':len(sheet['trim_cuts'])}


def validate_plan(plan,spec,resolved):
    from .planner import trusted_source
    try:
        spec=trusted_source(spec,resolved)
        require(plan['spec_sha256']==resolved['spec_sha256'] and plan['resolved_sha256']==resolved['resolved_sha256'],'Stock plan source fingerprint mismatch.')
        require(plan['schema_version']=='1.0.0' and plan['optimality']=='not_claimed','Unsupported stock contract or optimality claim.')
        parts=expanded_parts(resolved);requested={p['id']:p for p in parts};stocks={s['stock_id']:s for s in spec['manufacturing']['stock_sheets']};materials={m['material_id']:m for m in spec['materials'].values()}
        require(len(plan['sheets'])<=len(parts),'Candidate opens more sheets than physical parts.')
        all_placed=[];counts=Counter();identities=set();reports=[]
        for sheet in plan['sheets']:
            stock=stocks[sheet['stock_id']]
            require(type(sheet['sheet_index']) is int and sheet['sheet_index']>0 and type(sheet['sheet_count']) is int and sheet['sheet_count']==1,'Invalid physical sheet count/index.')
            identity=(sheet['stock_id'],sheet['sheet_index']);require(identity not in identities,'Physical sheet duplicated.');identities.add(identity)
            material=materials[stock['material_id']]
            require(sheet['actual_thickness_mm']==material['actual_thickness_mm'],'Stock thickness does not inherit its declared material.')
            placed=[leaf['instance_id'] for leaf in sheet['leaf_regions'] if leaf['kind']=='part']
            require(placed and set(placed)<=set(requested),'Empty sheet or unknown physical instance.')
            assigned=[requested[key] for key in placed]
            require(all(p['thickness_mm']==material['actual_thickness_mm'] for p in assigned),'Part assigned to the wrong thickness pool.')
            reports.append(validate_sheet(sheet,assigned,stock,spec['manufacturing']['saw_kerf_mm'],spec['manufacturing']['sheet_edge_trim_mm']))
            all_placed.extend(placed);counts[sheet['stock_id']]+=1
        missing=plan['unplaced_instance_ids']
        require(len(set(all_placed))==len(all_placed) and len(set(missing))==len(missing),'Global physical part coverage duplicated.')
        require(not set(missing)&set(all_placed) and set(missing)|set(all_placed)==set(requested),'Global requested/unplaced coverage is incomplete.')
        expected_counts={stock['stock_id']:{'stock_id':stock['stock_id'],'material_id':stock['material_id'],'sheet_count':counts[stock['stock_id']]} for stock in spec['manufacturing']['stock_sheets'] if counts[stock['stock_id']]}
        rows=plan['stock_counts']
        require(all(type(row['sheet_count']) is int and row['sheet_count']>0 for row in rows),'Purchased sheet counts must be positive integers.')
        require(len({row['stock_id'] for row in rows})==len(rows),'Purchased stock count duplicated.')
        require({row['stock_id']:row for row in rows}==expected_counts,'Purchased stock count does not match physical sheets.')
        for material in materials.values():require(len({sheet['stock_id'] for sheet in plan['sheets'] if sheet['material_id']==material['material_id']})<=1,'This planner supports one selected stock type per material.')
        require(plan['status']==('incomplete' if missing else 'complete'),'Layout completeness claim does not match physical coverage.')
        lower_bounds=[]
        for material in materials.values():
            compatible=[stock for stock in spec['manufacturing']['stock_sheets'] if stock['material_id']==material['material_id'] and (material['face_grain']=='none' or stock['grain_axis']=='length')]
            if not compatible:continue
            stock=compatible[0]
            area=sum((mm(part['length_mm'])*mm(part['width_mm']) for part in parts if part['material_id']==material['material_id']),Fraction(0))
            trim=mm(spec['manufacturing']['sheet_edge_trim_mm'])
            usable=(mm(stock['length_mm'])-2*trim)*(mm(stock['width_mm'])-2*trim)
            ratio=area/usable
            lower_bounds.append({'material_id':material['material_id'],'stock_id':stock['stock_id'],'sheets_lower_bound':(ratio.numerator+ratio.denominator-1)//ratio.denominator,'sufficiency':'not_established'})
        require(plan['area_lower_bounds']==lower_bounds,'Area lower bounds do not match declared stock, or imply unverified sufficiency.')
        from .costs import calculate_costs
        require(plan['costs']==calculate_costs(plan,spec,resolved),'Cost estimate differs from declared prices and verified physical sheets.')
        return {'status':'passed','coverage':'incomplete' if missing else 'complete','sheets':reports,'placed_part_count':len(all_placed),'unplaced_part_count':len(missing)}
    except StockError:raise
    except (KeyError,TypeError,ValueError,IndexError):raise StockError([{'code':'STOCK_PLAN_INVALID','message':'Malformed stock layout or source records.','field':'stock_plan','details':{}}]) from None
