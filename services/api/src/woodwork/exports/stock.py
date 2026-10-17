"""Cumulative exact stock data, independently replayed cut trees and print views."""
import json
from pathlib import Path
from reportlab.lib.pagesizes import A4,letter
from reportlab.pdfgen.canvas import Canvas
from woodwork.cad_adapter import validate_artifact_set
from woodwork.cad_adapter.verifier import require
from woodwork.domain import hash_json
from woodwork.exports.core import artifact_record,write_json,sha256_file
from woodwork.exports.cumulative import copy_verified_set
from woodwork.exports.dimensions import format_schedule,schedule_formatting,saved_schedule_formatting

STOCK_EXPORT_VERSION='1.1.0'


def draw_stock_pdf(path,plan,spec,metadata):
    policy=schedule_formatting(spec)
    size=A4 if spec['documents']['paper_size']=='a4' else letter
    width,height=size
    canvas=Canvas(str(path),pagesize=size,pageCompression=1)
    page=0
    def begin(title):
        canvas.setFont('Helvetica-Bold',16);canvas.drawString(36,height-42,title)
        canvas.setFont('Helvetica',9)
        canvas.drawString(36,height-61,'Revision '+metadata['revision_id'])
        canvas.drawString(36,height-75,'Spec SHA256 '+metadata['spec_sha256'])
    def end():
        nonlocal page
        page+=1;canvas.setFont('Helvetica',9)
        canvas.drawString(36,25,f'Woodworking Planner | nominal rough blanks | page {page}')
        canvas.showPage()
    def line(text,y,bold=False):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        font='Helvetica-Bold' if bold else 'Helvetica'
        canvas.setFont(font,9)
        text=str(text)
        while text:
            count=len(text)
            while count>1 and stringWidth(text[:count],font,9)>width-72:count-=1
            canvas.drawString(36,y,text[:count]);text=text[count:]
            if text:y-=13
        return y
    begin('Stock and purchase estimate')
    y=height-104
    for text in (f"Layout: {plan['status']}. Deterministic first-fit rows; optimality is not claimed.",
                 f"Saw kerf: {spec['manufacturing']['saw_kerf_mm']} mm. Edge trim: {spec['manufacturing']['sheet_edge_trim_mm']} mm.",
                 f"Per-edge rough allowance: {spec['manufacturing']['rough_allowance_per_edge_mm']} mm; finish to nominal size separately.",
                 'Grain-locked boards follow the declared compatible stock grain direction.',
                 'Area lower bounds do not establish sufficient purchasing quantities.'):
        y=line(text,y)-17
    y-=10
    costs=plan['costs']
    line('Sheet purchase costs (user-entered USD prices)',y,True);y-=20
    for row in costs['rows']:
        if y<100:end();begin('Purchase estimate continued');y=height-105
        price=row['unit_price_usd'] if row['unit_price_usd'] is not None else 'unknown'
        total=row['purchased_cost_usd'] if row['purchased_cost_usd'] is not None else 'unknown'
        y=line(f"{row['stock_id']}: {row['sheets_purchased']} sheet(s), unit USD {price}, purchased USD {total}",y)-18
    line('Known sheet subtotal: USD '+costs['known_sheet_subtotal_usd'],y,True);y-=18
    line('Sheet subtotal: '+(str(costs['sheet_purchase_subtotal_usd']) if costs['sheet_purchase_subtotal_usd'] is not None else 'incomplete; missing price or layout'),y);y-=18
    line('Complete project total: unknown. Excludes '+', '.join(costs['excluded_items'])+'.',y);y-=18
    line('Consumed allocation: finished face area / original sheet face area. Currency: HALF_EVEN to cents.',y);y-=26
    for identifier in plan['unplaced_instance_ids']:
        if y<80:end();begin('Unplaced parts continued');y=height-105
        line('UNPLACED: '+identifier,y);y-=16
    for finding in plan['findings'][:8]:
        message=finding['message'] if isinstance(finding,dict) else str(finding)
        if y<100:end();begin('Layout findings continued');y=height-105
        y=line(message,y)-14
    end()
    for sheet in plan['sheets']:
        begin(f"{sheet['stock_id']} / sheet {sheet['sheet_index']}")
        actual=sheet['actual_stock_mm']
        line('Original sheet: '+format_schedule(actual['length_mm'],policy)+' x '+format_schedule(actual['width_mm'],policy),height-102)
        stock=next(s for s in spec['manufacturing']['stock_sheets'] if s['stock_id']==sheet['stock_id'])
        line('Material '+sheet['material_id']+'; actual thickness '+sheet['actual_thickness_mm']+' mm; grain '+stock['grain_axis'],height-117)
        length,stock_width=float(actual['length_mm']),float(actual['width_mm'])
        scale=min((width-72)/length,250/stock_width)
        origin_x,origin_y=36,height-145-stock_width*scale
        canvas.setFillColorRGB(.9,.9,.9);canvas.setStrokeColorRGB(0,0,0)
        canvas.rect(origin_x,origin_y,length*scale,stock_width*scale,fill=1)
        canvas.setFont('Helvetica',9);canvas.setFillColorRGB(0,0,0)
        if stock['grain_axis']=='length':
            canvas.line(origin_x+10,origin_y-10,origin_x+90,origin_y-10)
            canvas.line(origin_x+90,origin_y-10,origin_x+83,origin_y-13)
            canvas.drawString(origin_x+100,origin_y-13,'stock grain along length (+x)')
        usable=sheet['usable_rectangle']
        canvas.setFillColorRGB(1,1,1)
        canvas.rect(origin_x+float(usable['x_mm'])*scale,origin_y+float(usable['y_mm'])*scale,float(usable['length_mm'])*scale,float(usable['width_mm'])*scale,fill=1)
        parts=[r for r in sheet['leaf_regions'] if r['kind']=='part']
        for index,part in enumerate(parts,1):
            x,y=origin_x+float(part['x_mm'])*scale,origin_y+float(part['y_mm'])*scale
            w,h=float(part['length_mm'])*scale,float(part['width_mm'])*scale
            canvas.setFillColorRGB(.95,.95,.95);canvas.setStrokeColorRGB(0,0,0)
            canvas.rect(x,y,w,h,fill=1)
            if min(w,h)>=16:
                canvas.setFillColorRGB(0,0,0);canvas.setFont('Helvetica-Bold',9);canvas.drawString(x+4,y+5,str(index))
        canvas.setFillColorRGB(0,0,0)
        y=origin_y-34
        line('Part IDs and rough rectangles; coordinates from the original sheet corner (mm)',y,True);y-=20
        for index,part in enumerate(parts,1):
            y=line(f"{index}. {part['instance_id']}: x={part['x_mm']}, y={part['y_mm']}, {part['length_mm']} x {part['width_mm']}, rotation {part['rotation_deg']} deg",y)-18
        areas=sheet['area_mm2']
        y-=7
        line(f"Areas mm2: parts {areas['parts']}; internal kerf {areas['internal_kerf']}; offcuts {areas['offcuts']}",y);y-=16
        line(f"Usable {areas['usable']}; reserved edge bands {areas['reserved_edge_bands']}; original {areas['original_sheet']}",y)
        end()
        begin(f"Cut sequence: {sheet['stock_id']} / {sheet['sheet_index']}")
        y=height-103
        line('Apply reserved edge trim first, then replay each numbered internal cut on its named region.',y);y-=20
        line('Internal kerf removes material. No trailing kerf is invented at a finished stock boundary.',y);y-=26
        for cut in sheet['trim_cuts']:
            if y<140:end();begin('Edge trim sequence continued');y=height-104
            rect=cut['source_rectangle']
            y=line(f"{cut['cut_id']}: trim region {cut['source_region']} along {cut['axis']}; kerf begins {cut['kerf_start_mm']} mm, width {cut['kerf_mm']} mm.",y,True)-16
            y=line(f"Source x={rect['x_mm']}, y={rect['y_mm']}, {rect['length_mm']} x {rect['width_mm']} mm. Result: {cut['low_child']} / {cut['high_child']}.",y)-22
        for cut in sheet['internal_cuts']:
            if y<140:end();begin('Cut sequence continued');y=height-104
            rect=cut['source_rectangle']
            from fractions import Fraction
            from woodwork.domain import exact_decimal
            offset=exact_decimal(Fraction(cut['kerf_start_mm'])-Fraction(rect['x_mm' if cut['axis']=='x' else 'y_mm']))
            y=line(f"{cut['cut_id']}: region {cut['source_region']}, axis {cut['axis']}, kerf begins {cut['kerf_start_mm']} mm, width {cut['kerf_mm']} mm",y,True)-16
            y=line('Kerf begins '+offset+' mm from this active region origin along the named axis.',y)-16
            y=line(f"Source x={rect['x_mm']}, y={rect['y_mm']}, {rect['length_mm']} x {rect['width_mm']} mm; children {cut['low_child']} / {cut['high_child']}",y)-24
        line('These diagrams describe sheet cutting; they are not a drill-access or structural approval.',y-6)
        end()
    canvas.save()
    return page


def validate_stock_output(directory,spec,resolved,metadata):
    from woodwork.stock import validate_plan,plan_stock
    directory=Path(directory)
    value=json.loads((directory/'stock-layout.json').read_text())
    require(all(value[k]==metadata[k] for k in ('revision_id','spec_sha256','resolved_sha256')),'Stock record revision differs.')
    plan=value['plan']
    validate_plan(plan,spec,resolved)
    require(plan==plan_stock(spec,resolved),'Stock plan differs from authoritative deterministic planning.')
    require(json.loads((directory/'cost-estimate.json').read_text())=={'revision_id':metadata['revision_id'],'spec_sha256':metadata['spec_sha256'],'resolved_sha256':metadata['resolved_sha256'],**plan['costs']},'Cost estimate differs from stock calculation.')
    from pypdf import PdfReader
    reader=PdfReader(directory/'stock-layout.pdf')
    require(0<len(reader.pages)<=30,'Stock PDF has invalid page count.')
    text=' '.join('\n'.join(page.extract_text() for page in reader.pages).split())
    require(metadata['revision_id'] in text and metadata['spec_sha256'] in text,'Stock PDF revision missing.')
    require(all(i['instance_id'] in text for i in resolved['part_instances']),'Stock PDF omits a placed or unplaced physical ID.')
    policy=saved_schedule_formatting(json.loads((directory/'build-inputs.json').read_text(encoding='utf-8')),spec,'stock')
    for sheet in plan['sheets']:
        actual=sheet['actual_stock_mm']
        require('Original sheet: '+format_schedule(actual['length_mm'],policy)+' x '+format_schedule(actual['width_mm'],policy) in text,'Stock PDF sheet dimensions disagree with selected units or precision.')
    return {'status':'passed','revision_id':metadata['revision_id'],'spec_sha256':metadata['spec_sha256'],'resolved_sha256':metadata['resolved_sha256'],'cut_tree_replay':'passed','layout_status':plan['status'],'pdf_pages':len(reader.pages),'visual_review':'required_separately','application_units':policy['units'],'application_fraction_denominator':policy['fraction_denominator'] if policy['units']=='dual' else None}


def add_stock(source_dir,out_dir,metadata,spec,resolved):
    from woodwork.stock import plan_stock,validate_plan
    out_dir=Path(out_dir)
    manifest,records=copy_verified_set(source_dir,out_dir,metadata)
    plan=plan_stock(spec,resolved);validate_plan(plan,spec,resolved)
    write_json(out_dir/'stock-layout.json',{'revision_id':metadata['revision_id'],'spec_sha256':metadata['spec_sha256'],'resolved_sha256':metadata['resolved_sha256'],'plan':plan})
    write_json(out_dir/'cost-estimate.json',{'revision_id':metadata['revision_id'],'spec_sha256':metadata['spec_sha256'],'resolved_sha256':metadata['resolved_sha256'],**plan['costs']})
    draw_stock_pdf(out_dir/'stock-layout.pdf',plan,spec,metadata)
    source_inputs=json.loads((out_dir/'build-inputs.json').read_text())
    inherited_inputs=source_inputs['source_inputs'] if 'stock_export_version' in source_inputs else source_inputs
    inputs={'spec_sha256':metadata['spec_sha256'],'resolved_sha256':metadata['resolved_sha256'],'source_artifact_set_id':metadata['source_artifact_set_id'],'source_build_key_sha256':manifest['build_key_sha256'],'source_inputs':inherited_inputs,'stock_export_version':STOCK_EXPORT_VERSION,'stock_sources_sha256':{name:sha256_file(Path(__file__).parents[1]/'stock'/name) for name in ('planner.py','validator.py','costs.py','common.py')},'exporter_sha256':sha256_file(Path(__file__)),'stock_options':spec['manufacturing'],'schedule_formatting':schedule_formatting(spec),'dimension_formatter_sha256':sha256_file(Path(__file__).with_name('dimensions.py'))}
    write_json(out_dir/'build-inputs.json',inputs)
    evidence=validate_stock_output(out_dir,spec,resolved,metadata)
    write_json(out_dir/'stock-validation.json',evidence)
    for relative,kind,mime in [('stock-layout.json','json','application/json'),('cost-estimate.json','json','application/json'),('stock-validation.json','json','application/json'),('build-inputs.json','json','application/json'),('stock-layout.pdf','pdf','application/pdf')]:
        records[relative]=artifact_record(out_dir,relative,kind,mime,metadata)
    manifest.update(artifacts=list(records.values()),build_key_sha256=hash_json(inputs))
    manifest['capabilities']=list(dict.fromkeys([*manifest['capabilities'],'stock_layout','cost_estimate']))
    manifest['validation']['stock_layout']='passed' if plan['status']=='complete' else 'incomplete'
    write_json(out_dir/'manifest.json',manifest)
    validate_artifact_set(out_dir,inspect_geometry=False)
    return manifest
