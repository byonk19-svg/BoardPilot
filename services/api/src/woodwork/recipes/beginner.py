"""Checked through-side entry geometry and an explicit beginner operation graph."""
from copy import deepcopy
from fractions import Fraction as F

from woodwork.domain import DomainError, finding, hash_json, resolve_mm
from .beginner_catalog import BEGINNER_ID, ENTRY
from .graph import validate_recipe_graph as validate_common

LABELS={'side_left':('A','Left side'),'side_right':('B','Right side'),'bottom':('C','Bottom'),'shelf_01':('D','Lower shelf'),'shelf_02':('E','Upper shelf'),'top':('F','Top'),'back':('G','Back')}


def world_point(instance,point):
    return {axis:resolve_mm(sum(F(instance['rotation_cad_rows'][i][j])*F(point[key]) for j,key in enumerate('xyz'))+F(instance['center_mm'][axis])) for i,axis in enumerate('xyz')}


def back_positions(length,offsets):
    return sorted({value for offset in offsets for value in (F(offset),length-F(offset))})


def build_recipe_graph(entry,spec,resolved):
    parts={i['instance_id']:i for i in resolved['part_instances']}; definitions={d['definition_id']:d for d in resolved['part_definitions']}
    hardware={h['hardware_id']:h for h in entry['hardware']}
    h,w,d=(F(spec['dimensions'][key]) for key in ('outside_height_mm','outside_width_mm','outside_depth_mm'))
    t,b=(F(spec['materials'][role]['actual_thickness_mm']) for role in ('main','back'))
    depth=d-b; offsets=entry['rules']['back_end_offsets_mm']; joints=[]
    for required in resolved['construction_requirements']:
        members=required['instance_ids']; back='back' in members
        if not back:
            side=next(p for p in members if p.startswith('side_')); receiver=next(p for p in members if p!=side)
            machine=parts[side]; face_x=F(0) if F(machine['center_mm']['x'])<w/2 else w
            sign=(face_x-F(machine['center_mm']['x']))/(F(machine['rotation_cad_rows'][0][2])*t/2)
            z=F(parts[receiver]['center_mm']['z']); stations=[]
            for front in (F(entry['rules']['main_front_offset_mm']),depth/2,depth-F(entry['rules']['main_front_offset_mm'])):
                datum={'x':resolve_mm(z-h/2),'y':resolve_mm(front-depth/2),'z':resolve_mm(t/2)}
                actual={**datum,'z':resolve_mm(sign*t/2)}
                axis=[int(-sign*machine['rotation_cad_rows'][i][2]) for i in range(3)]
                stations.append({'reference_face':'local_T_positive','local_alignment_mm':datum,'world_alignment_mm':world_point(machine,datum),'geometry':'layout_datum_not_drill_entry','entry_face':'local_T_positive' if sign>0 else 'local_T_negative','entry_local_mm':actual,'entry_world_mm':world_point(machine,actual),'drill_axis_world':axis,'from_front_edge_mm':resolve_mm(front),'receiving_instance_id':receiver})
            method='through_side_screw_and_glue'; hardware_id='carcass_screw'; machined=side; through=t
        else:
            receiver=next(p for p in members if p!='back'); target=parts[receiver]; machine=parts['back']; stations=[]
            if receiver.startswith('side_'):
                points=[(F(target['center_mm']['x']),z) for z in back_positions(h,offsets)]
            else:
                length=F(definitions[target['definition_id']]['finished_mm']['length_mm']); start=F(target['center_mm']['x'])-length/2
                points=[(start+x,F(target['center_mm']['z'])) for x in back_positions(length,offsets)]
            for x,z in points:
                local={'x':resolve_mm(z-h/2),'y':resolve_mm(x-w/2),'z':resolve_mm(b/2)}
                stations.append({'reference_face':'back_local_T_positive','local_alignment_mm':local,'world_alignment_mm':world_point(machine,local),'geometry':'layout_datum_not_drill_entry','entry_face':'local_T_positive','entry_local_mm':deepcopy(local),'entry_world_mm':world_point(machine,local),'drill_axis_world':[0,-1,0],'receiving_instance_id':receiver})
            method='back_screw_and_glue'; hardware_id='back_screw'; machined='back'; through=b
        fastener=hardware[hardware_id]
        for station in stations:
            station.update(hardware_id=hardware_id,through_thickness_mm=resolve_mm(through),clearance_diameter_mm=fastener['clearance_mm'],pilot_diameter_mm=fastener['pilot_mm'],pilot_into_receiver_mm=fastener['pilot_into_receiver_mm'],head_policy=fastener['head_policy'],screw_penetration_mm=resolve_mm(F(fastener['length_mm'])-through))
        joints.append({**deepcopy(required),'method':method,'machined_instance_id':machined,'stations':stations,'hardware':[{'hardware_id':hardware_id,'quantity':len(stations)}],'source_ids':['pw_back','mcfeely_chart'] if back else ['pw_bookcase','mcfeely_chart','minwax_bookcase'],'decision_basis':'authored_geometry_pending_physical_review'})
    operations=operation_graph(joints,list(parts))
    return {'recipe_id':BEGINNER_ID,'joints':joints,'operations':operations,'hardware':deepcopy(entry['hardware'])}


def operation_graph(joints,all_parts):
    main=[p for p in all_parts if p!='back']; sides=['side_left','side_right']
    descriptions=[
        ('cut_and_label','Cut, check and label the parts','finish_to_size',all_parts,['panel_saw','measuring_tools'],'parts',[
            'Measure the actual plywood: 18 mm for A-F and 6 mm for G. A nominal 3/4-inch label is not a thickness measurement. Stop if your actual stock differs.',
            'Use the cut list and the separate stock-layout PDF. Keep saw kerf on the waste side. If rough blanks include allowance, finish them to the exact finished sizes before marking holes.',
            'Mark A-G, FRONT and BOTTOM in pencil. Pick the outside faces of A and B. Lightly remove splinters without rounding joint edges; keep glue-contact edges bare. Follow the saw manual and use eye, hearing and dust protection.']),
        ('mark_sides','Mark both sides from the bottom and front','mark',sides,['square','measuring_tools'],'side_marks',[
            'Lay A and B together with bottoms aligned. Transfer the four panel centre lines from the same BOTTOM edge: 9, 307.8, 606.6 and 905.4 mm. These are screw centre lines, not shelf undersides.',
            'Shelf undersides are 298.8 and 597.6 mm above the bottom. Mark an 18 mm band for each panel and its centre line. Each clear opening will be 280.8 mm.',
            'On the marked OUTSIDE face, place three screw marks on every centre line, 30, 149.4 and 268.8 mm from the FRONT edge. Both sides get twelve marks. The drawing is not a full-size drilling template.']),
        ('clearance_holes','Test and drill the side clearance holes','drill',sides,['drill_driver','matching_flathead_countersink','1_8in_pilot_bit','11_64in_clearance_bit','drill_depth_stops','clamps','sacrificial_backer'],'drill_section',[
            'First practise the complete joint on matching 18 mm offcuts using your actual #8 x 2 in flat-head WOOD screws. The published pilot sizes are starting points: stop if the core splits, the screw strips or the joint will not close.',
            'Clamp each loose side on a sacrificial backer, OUTSIDE up. Make a shallow countersink for the actual screw head before drilling the 11/64 in clearance hole through the side only. Set the head flush, never deeply below the veneer.',
            'A clearance hole lets the screw pass through the side without gripping it. The narrower 1/8 in pilot goes into the mating horizontal panel later. Do not substitute drywall screws or hold a panel in your hand while drilling.']),
        ('dry_fit_and_pilot','Dry fit and drill the mating pilot holes','drill',main,['drill_driver','1_8in_pilot_bit','drill_depth_stops','clamps','square'],'dry_fit',[
            'On a flat bench, stand the six main panels on their BACK edges with the open FRONT facing up. Put C-F between A and B, with top/bottom flush at the ends. Use corner/bar clamps and a helper or temporary support blocks; keep all free ends supported.',
            'Align D and E with their marked bands and check the three 280.8 mm clear openings. Clamp the panels square, with all back edges in one plane. Do not use screws to pull a badly fitting joint into place.',
            'Use each side clearance hole as a guide for a perpendicular 1/8 in pilot into the CENTRE of the horizontal panel edge. Pilot depth is 35 mm into that edge: 53 mm total from the outside of the 18 mm side. Use a positive depth stop and a square/guide block; keep hands clear behind the drill.']),
        ('attach_left','Glue and fasten the left side','attach',main,['drill_driver','clamps','square'],'left_screws',[
            'Keep the dry assembly supported on its back edges. Release A only enough to spread a thin, even film of plywood-compatible wood glue on the four left end edges of C-F. Follow the glue label and restore the matched pencil marks.',
            'Reclamp A at right angles, with the opposite ends still supported by B and the clamps/supports. Drive three #8 x 2 in flat-head wood screws into each matched pilot: twelve screws on A.',
            'Use a low drill clutch and finish gently so heads sit flush. Keep the panels tight and flush without crushing veneer. If a screw spins or a panel splits, stop and repair the joint before continuing.']),
        ('attach_right','Glue and fasten the right side','attach',main,['drill_driver','clamps','square'],'right_screws',[
            'With A secured and all panels still supported, apply glue to the four right end edges of C-F and restore B to its matched marks. Clamp the right-hand joints closed.',
            'Drive the other twelve #8 x 2 in flat-head wood screws through B into the prepared pilots. Confirm top/bottom alignment and the same three clear openings. Remove temporary spacers/supports that are not part of the bookcase.',
            'There are 24 main screws in total. Keep clamps in place as required by the adhesive label; do not stand or load the case while the glue is uncured.']),
        ('square_and_cure','Check square and let the carcass glue cure','inspect',main,['square','measuring_tools','clamps'],'square',[
            'Before the glue sets, measure both outside corner-to-corner diagonals of the open front. Adjust the clamps gently until they match and the corners check square. Check width/height 914.4 mm and carcass depth 298.8 mm.',
            'Let the adhesive fully cure under its stated conditions before lifting or turning the case. Handling time is not full cure. For the documented Titebond Original example, keep it unstressed for at least 24 hours and follow any longer label requirement.',
            'With a helper, place the cured case FRONT down on a padded, flat bench so the BACK edges face up. Recheck square. If the cured frame is out of square, stop rather than forcing the thin back to correct it.']),
        ('mark_and_pilot_back','Mark and drill the back fixing lines','drill',all_parts,['drill_driver','7_64in_pilot_bit','9_64in_clearance_bit','drill_depth_stops','clamps','measuring_tools','sacrificial_backer'],'back_layout',[
            'Dry-clamp G flush with all four outside edges. Mark the rear edge CENTRES underneath it: sides 9 mm in from each outer side; bottom/shelves/top at 9, 307.8, 606.6 and 905.4 mm above BOTTOM. The back diagram is viewed from outside the rear.',
            'Each contacted edge gets six screws: mark 25, 200 and 375 mm from BOTH ends of that receiving edge. For horizontal edges, the ends are the INSIDE faces of the sides, 18 mm in from the back-panel edges. The back worksheet gives the resulting positions.',
            'Remove G onto a sacrificial backer. On a matching 6 mm offcut, test a shallow countersink for the actual #6 head, no deeper than 2 mm; at least 4 mm of panel must remain. The head must sit flush without crushing or pulling through. Stop if it will not. Then countersink G before drilling 9/64 in clearance holes through G only. Do not over-countersink the back. Reclamp it flush, then use those holes to guide 7/64 in pilots 12 mm into the carcass edges: 18 mm total from the rear face of G. Test the #6 screw/pilot combination on matching offcuts first.']),
        ('attach_back','Glue and screw the applied back','attach',all_parts,['drill_driver','clamps','square'],'back_fastening',[
            'Lift the dry-fitted back, spread a thin film of wood glue on the contacted carcass rear edges, then restore G to the same marks and pilots. Keep its edges flush and the case square.',
            'Use only #6 x 5/8 in flat-head wood screws in the 36 prepared positions. Seat the heads flush in the tested shallow countersinks without crushing or pulling through the 6 mm back. No fastener head should project beyond the finished outside dimensions. Do not use the long carcass screws here.',
            'The short screws pass through 6 mm of back and enter the carcass about 9.875 mm. Check for unintended breakout, loose joints and missed receiving edges before allowing the back glue to cure.']),
        ('final_check','Finish checking and restrain before loading','inspect',all_parts,['square','measuring_tools'],'final',[
            'Let all glue fully cure per its label. Check the finished outside size: 914.4 mm wide, 914.4 mm high and 304.8 mm deep, including G. Confirm three 280.8 mm clear openings and that every screw is seated, with no split core or sharp point exposed.',
            'Remove splinters and clean the piece. Apply any optional finish only after curing and per its product instructions; do not conceal a faulty joint. With a helper, place it on a level surface.',
            'Before loading, install a furniture tip-over restraint selected for the actual wall and solid carcass using the kit instructions. Do not rely only on the thin back. If you cannot identify a suitable attachment, get qualified help. A physical build has not been performed; no shelf load rating is supplied.']),
    ]
    operations=[]
    for index,(key,title,kind,parts,tools,diagram,actions) in enumerate(descriptions):
        attached=[j['joint_id'] for j in joints if (key=='attach_back' and j['method']=='back_screw_and_glue') or (key in ('attach_left','attach_right') and j['method']=='through_side_screw_and_glue' and j['machined_instance_id']==('side_left' if key=='attach_left' else 'side_right'))]
        operations.append({'operation_id':key,'title':title,'type':kind,'parts':parts,'depends_on':[] if not operations else [operations[-1]['operation_id']],'joints':attached,'tools':tools,'instruction':' '.join(actions),'actions':actions,'diagram':diagram})
    return operations


def validate_recipe_graph(graph,resolved,*,required_tools=(),available_tools=None,rough_allowance_mm='0'):
    checked=validate_common(graph,resolved,required_tools=required_tools,available_tools=available_tools,rough_allowance_mm=rough_allowance_mm)
    findings=checked['findings']; parts={p['instance_id']:p for p in resolved['part_instances']}; definitions={d['definition_id']:d for d in resolved['part_definitions']}; hardware={h['hardware_id']:h for h in graph.get('hardware',[])}
    if graph.get('operations') != operation_graph(graph.get('joints', []), list(parts)):
        findings.append({'code':'OPERATION_CONTRACT_MISMATCH','message':'Required preparation, pilot drilling, assembly order or instructions differ from this versioned method.'})
    spec=resolved['spec']; outside=[F(spec['dimensions'][key]) for key in ('outside_width_mm','outside_depth_mm','outside_height_mm')]
    normalized={key:set() for key in ('side_left','side_right')}
    for expected in ENTRY['hardware']:
        actual=hardware.get(expected['hardware_id'],{})
        if any(actual.get(key)!=value for key,value in expected.items()):
            findings.append({'code':'HARDWARE_SPEC_MISMATCH','message':f"Hardware {expected['hardware_id']} differs from this versioned method's screw specification."})
    for joint in graph.get('joints',[]):
        try:
            main=joint['method']=='through_side_screw_and_glue'; expected_hardware='carcass_screw' if main else 'back_screw'
            if joint['method'] not in ('through_side_screw_and_glue','back_screw_and_glue'):raise ValueError()
            machine=parts[joint['machined_instance_id']]; dims=definitions[machine['definition_id']]['finished_mm']; half=[F(dims[k])/2 for k in ('length_mm','width_mm','thickness_mm')]
            if main and not machine['instance_id'].startswith('side_') or not main and machine['instance_id']!='back':raise ValueError()
            fastener=hardware[expected_hardware]
            if len(joint['stations'])!=(3 if main else 6):raise ValueError()
            if joint['hardware']!=[{'hardware_id':expected_hardware,'quantity':len(joint['stations'])}]:raise ValueError()
            receiver_id=next(p for p in joint['instance_ids'] if p!=machine['instance_id']); receiver=parts[receiver_id]
            if main:
                target_axis=[1,0,0] if F(machine['center_mm']['x'])<outside[0]/2 else [-1,0,0]
                face_coord=F(0) if target_axis[0]>0 else outside[0]
                expected_points={(F(front),F(receiver['center_mm']['z'])) for front in ('30','149.4','268.8')}
            else:
                target_axis=[0,-1,0]; face_coord=outside[1]
                if receiver_id.startswith('side_'):expected_points={(F(receiver['center_mm']['x']),p) for p in back_positions(outside[2],('25','200','375'))}
                else:
                    L=F(definitions[receiver['definition_id']]['finished_mm']['length_mm']); start=F(receiver['center_mm']['x'])-L/2
                    expected_points={(start+p,F(receiver['center_mm']['z'])) for p in back_positions(L,('25','200','375'))}
            actual_points=set()
            for station in joint['stations']:
                local=[F(station['entry_local_mm'][a]) for a in 'xyz']; point=[F(station['entry_world_mm'][a]) for a in 'xyz']; through=F(station['through_thickness_mm']); pilot=F(station['pilot_into_receiver_mm']); length=F(fastener['length_mm'])
                if not all(abs(local[i])<=half[i] for i in range(3)) or abs(local[2])!=half[2]:raise ValueError()
                if station['entry_face']!=('local_T_positive' if local[2]>0 else 'local_T_negative'):raise ValueError()
                if world_point(machine,station['entry_local_mm'])!=station['entry_world_mm'] or station['drill_axis_world']!=target_axis:raise ValueError()
                if point[0 if main else 1]!=face_coord or station['receiving_instance_id']!=receiver_id or station['hardware_id']!=expected_hardware:raise ValueError()
                if through!=2*half[2] or pilot!=F('35' if main else '12') or F(station['screw_penetration_mm'])!=length-through:raise ValueError()
                if station['clearance_diameter_mm']!=fastener['clearance_mm'] or station['pilot_diameter_mm']!=fastener['pilot_mm'] or station['head_policy']!=fastener['head_policy']:raise ValueError()
                if not 0<F(fastener['pilot_mm'])<F(fastener['major_diameter_mm'])<F(fastener['clearance_mm']):raise ValueError()
                if not through<length<through+pilot:raise ValueError()
                for distance in (length,through+pilot):
                    tip=[point[i]+F(target_axis[i])*distance for i in range(3)]
                    if not all(F(receiver['world_aabb_mm']['min'][a])<tip[i]<F(receiver['world_aabb_mm']['max'][a]) for i,a in enumerate('xyz')):raise ValueError()
                if main:
                    if point[2]!=F(receiver['center_mm']['z']):raise ValueError()
                    if F(station['from_front_edge_mm'])!=point[1]:raise ValueError()
                    if any(F(station['local_alignment_mm'][a])!=F(station['entry_local_mm'][a]) for a in 'xy'):raise ValueError()
                    actual_points.add((point[1],point[2]))
                    # Proper rotation about length normalizes the exterior face.
                    normalized[machine['instance_id']].add((local[0],local[1] if local[2]>0 else -local[1],abs(local[2]),station['head_policy'],station['clearance_diameter_mm']))
                else:actual_points.add((point[0],point[2]))
            if actual_points!=expected_points:raise ValueError()
        except (KeyError,ValueError,TypeError,ZeroDivisionError,StopIteration):
            findings.append({'code':'DRILL_ENTRY_INVALID','message':f"Connection {joint.get('joint_id','unknown')} has inconsistent drilling entry, axis, receiver, depth or hardware."})
    equivalent=bool(normalized['side_left']) and normalized['side_left']==normalized['side_right']
    if not equivalent:findings.append({'code':'PREPARATION_NOT_EQUIVALENT','message':'Side preparation patterns do not match under the proper exterior-face rotation.'})
    checked.update(technical_completeness=not findings,preparation_equivalence={'proper_rotation_determinant':1,'side_patterns_match':equivalent})
    return checked


def resolve_recipe(spec,resolved,*,catalog=None,available_tools=None):
    from .catalog import installed_catalog
    selection=spec['construction']['recipe']; entry=(installed_catalog() if catalog is None else catalog).get((selection['id'],selection['version']))
    if entry is None:raise DomainError([finding('RECIPE_UNKNOWN','The selected recipe version is not installed.','construction.recipe')])
    incompatible=[]
    for path,bounds in entry['modeling_bounds'].items():
        value=spec
        for key in path.split('.'):value=value[key]
        if not F(bounds[0])<=F(value)<=F(bounds[1]):incompatible.append(f'{path}: this method requires actual {bounds[0]} mm; received {value} mm.')
    if spec['dimensions']['fixed_shelf_count']!=2:incompatible.append('This method requires exactly two fixed shelves.')
    if spec['template']['id']!=entry['applicability']['template_id'] or any(spec['materials'][role]['kind']!='plywood' for role in ('main','back')):incompatible.append('This method requires the plywood bookcase template and plywood panels.')
    graph=build_recipe_graph(entry,spec,resolved) if not incompatible else {'joints':[],'operations':[],'hardware':[]}
    checked=validate_recipe_graph(graph,resolved,required_tools=entry['required_tools'],available_tools=available_tools,rough_allowance_mm=spec['manufacturing']['rough_allowance_per_edge_mm']) if not incompatible else {'technical_completeness':False,'findings':[],'ordered_operation_ids':[],'hardware':[],'preparation_equivalence':None}
    operations={o['operation_id']:o for o in graph['operations']}
    return {'status':'incompatible' if incompatible else 'complete' if checked['technical_completeness'] else 'incomplete','recipe_id':selection['id'],'recipe_version':selection['version'],'fingerprint':hash_json(entry),'physical_review':'not_reviewed','technical_completeness':checked['technical_completeness'],'findings':incompatible+[f['message'] for f in checked['findings']],'validation_findings':checked['findings'],'joints':graph['joints'],'operations':[operations[key] for key in checked['ordered_operation_ids']],'hardware':checked['hardware'],'preparation_equivalence':checked['preparation_equivalence'],**{key:deepcopy(entry[key]) for key in ('required_tools','source_records','author_decisions','installation','review_record','consumables')}}


def manufacturing_plan(spec,resolved,recipe):
    plan={i['instance_id']:[] for i in resolved['part_instances']}
    if recipe['status']!='complete':return plan
    for side in ('side_left','side_right'):
        stations=[s for j in recipe['joints'] if j['machined_instance_id']==side for s in j['stations']]
        plan[side]=sorted([{'operation_type':'planned_through_side_wood_screw','geometry_status':'reference_only_nominal_cad_blank','coordinate_frame':'marked_outside_face_from_bottom_and_front','height_from_bottom_mm':s['entry_world_mm']['z'],'from_front_edge_mm':s['from_front_edge_mm'],'clearance_mm':s['clearance_diameter_mm'],'pilot_mm':s['pilot_diameter_mm'],'pilot_into_receiver_mm':s['pilot_into_receiver_mm'],'head_policy':s['head_policy'],'hardware_id':s['hardware_id']} for s in stations],key=lambda s:(F(s['height_from_bottom_mm']),F(s['from_front_edge_mm'])))
    plan['back']=[{'operation_type':'planned_back_wood_screw','geometry_status':'reference_only_nominal_cad_blank','reference_face':'back_local_T_positive','local_alignment_mm':deepcopy(s['entry_local_mm']),'clearance_mm':s['clearance_diameter_mm'],'pilot_mm':s['pilot_diameter_mm'],'pilot_into_receiver_mm':s['pilot_into_receiver_mm'],'head_policy':s['head_policy'],'hardware_id':s['hardware_id']} for j in recipe['joints'] if j['machined_instance_id']=='back' for s in j['stations']]
    return plan
