"""A narrowly authored butt-joint method for the existing measured sample."""
from copy import deepcopy
import hashlib
from pathlib import Path

BEGINNER_ID='beginner_screws_18_6_36in_bookcase'
BEGINNER_VERSION='1.0.0'

ENTRY={
    'recipe_id':BEGINNER_ID,'version':BEGINNER_VERSION,
    'title':'Beginner screw-and-glue bookcase - actual 18/6 mm, 36 x 36 x 12 in',
    'method':'Through-side wood screws and glue; separately screwed applied back',
    'test_only':False,'technical_completeness':True,'physical_review':'not_recorded',
    'generator_version':'1.0.0','illustration_contract':'beginner_checked_steps_1.0.0',
    'modeling_bounds':{
        'dimensions.outside_width_mm':['914.4','914.4'],'dimensions.outside_height_mm':['914.4','914.4'],
        'dimensions.outside_depth_mm':['304.8','304.8'],'materials.main.actual_thickness_mm':['18','18'],
        'materials.back.actual_thickness_mm':['6','6'],
    },
    'applicability':{'template_id':'plywood_bookcase_v1','main_material_kind':'plywood','back_material_kind':'plywood','environment':'indoor','shelf_count':[2,2]},
    'required_tools':['panel_saw','drill_driver','square','measuring_tools','clamps','matching_flathead_countersink','1_8in_pilot_bit','11_64in_clearance_bit','7_64in_pilot_bit','9_64in_clearance_bit','drill_depth_stops','sacrificial_backer','eye_hearing_dust_protection'],
    'hardware':[
        {'hardware_id':'carcass_screw','type':'#8 x 2 in flat-head wood screw (not drywall screw)','sku':'spec:WOOD-8x2-FLAT','length_mm':'50.8','length_in':'2','major_diameter_mm':'4.1656','thread':'wood','unit':'each','unit_price':None,'pack_quantity':None,'clearance_mm':'4.365625','pilot_mm':'3.175','pilot_into_receiver_mm':'35','head_policy':'countersink_flush_only'},
        {'hardware_id':'back_screw','type':'#6 x 5/8 in flat-head wood screw; shallow flush seating','sku':'0605-FPB','length_mm':'15.875','length_in':'0.625','major_diameter_mm':'3.5052','thread':'wood','unit':'each','unit_price':None,'pack_quantity':None,'clearance_mm':'3.571875','pilot_mm':'2.778125','pilot_into_receiver_mm':'12','head_policy':'shallow_countersink_flush_max_2mm'},
    ],
    'consumables':[{'consumable_id':'wood_glue','description':'Interior wood glue suitable for plywood, used per its label; Titebond Original is the documented example. Keep joint surfaces bare.','quantity':None,'unit_price':None}],
    'rules':{'main_front_offset_mm':'30','back_end_offsets_mm':['25','200','375'],'finish_to_size':True},
    'source_records':[
        {'source_id':'pw_bookcase','title':'Popular Woodworking, Bookcase Plans, PDF p18','url':'https://media.popularwoodworking.com/app/uploads/2019/11/r3067_bookcaseplans.pdf','rule':'Published plywood bookcase alternative: #8 x 2 in screws through sides into fixed shelves. This sample layout is an authored adaptation.'},
        {'source_id':'mcfeely_chart','title':'McFeelys Wood Screw Drilling Chart','url':'https://www.mcfeelys.com/drilling_chart','rule':'Starting straight hardwood pilots: #8 1/8 in, #6 7/64 in. Shank clearances: #8 11/64 in, #6 9/64 in. Match actual screws and verify on matching offcuts; wood/core properties vary.'},
        {'source_id':'minwax_bookcase','title':'Minwax Traditional Bookcase, PDF p3','url':'https://www.minwax.com/content/dam/cbg-minwax/woodworking-project-inspiration/pdfs/minwax-intermediate-project-traditional-bookcase.pdf','rule':'Countersink before clearance to reduce veneer tearing; dry-clamp and use clearance holes to guide mating pilots. Its unrelated dimensions and drywall screw choice are not adopted.'},
        {'source_id':'pw_back','title':'Popular Woodworking, Stacking Bookshelves, PDF p2','url':'https://media.popularwoodworking.com/app/uploads/2011/04/StackingBookshelves.pdf','rule':'#6 x 5/8 in screws are a published plywood-back option. The surface-applied 6 mm back and shallow flush-head choice here are authored adaptations; no rabbet is added.'},
        {'source_id':'back_screw_product','title':'McFeelys 0605-FPB #6 x 5/8 in flat-head wood screw','url':'https://www.mcfeelys.com/6-x-5-8-in-flat-head-black-phillips.html','rule':'Published flat-head wood-screw size and Phillips #2 drive. Head diameter 17/64 in (6.746875 mm). No universal safe countersink depth in 6 mm plywood is claimed; the 2 mm maximum here is an authored stop limit and requires a matching offcut test.'},
        {'source_id':'glue','title':'Titebond wood-glue use and curing guidance','url':'https://titebond.com/resources/use/glues','rule':'Use the actual adhesive label for clamp/cure times and conditions. Handling time is not full cure; do not stress uncured joints.'},
        {'source_id':'restraint','title':'US CPSC Anchor It: install a restraint kit','url':'https://www.anchorit.gov/how-to-anchor/how-to-install-a-kit/','rule':'Select a kit and fasteners for the furniture and actual wall. Follow its installation instructions before loading furniture.'},
    ],
    'author_decisions':[
        'Three main screws per joint at 30 mm, mid-depth and 30 mm from the rear. Four horizontal panels, two ends each: 24 screws.',
        'Back fasteners are 25, 200 and 375 mm from both ends of each contacted edge: six per line, six lines, 36 screws. This is geometric placement, not a tested load specification.',
        'Main pilot depth is 35 mm into the horizontal edge; back pilot depth is 12 mm into the carcass edge. Stop distances from the entry faces include the measured 18 mm or 6 mm outer panel.',
        'Choose actual wood screws matching the stated size/head specifications; supplier pack size and prices are unknown. Drill/drive matching offcuts before touching the cabinet.',
        'Side preparation is referenced from a marked outside face, bottom and front. Symmetric depth rows make the two side blanks equivalent after a proper 180-degree rotation; actual CAD entry faces remain separately recorded.',
        'CAD stays as measured unmachined blanks. Drilling illustrations are planned reference geometry, not native machined holes. No physical build or load test was performed.',
    ],
    'installation':{'status':'site_selection_required','instruction':'Before loading, select and install a tip-over restraint suited to the actual wall and solid carcass, following the kit instructions. Do not rely only on the thin back as the furniture attachment. If the wall or attachment is uncertain, get qualified installation help.','source_id':'restraint'},
    'review_record':{'technical_scope':'Geometry, source consistency, complete connection coverage, drilling references, preparation equivalence and ordered instructions','physical_record':None,'load_rating':None},
}


def beginner_entry():
    entry=deepcopy(ENTRY)
    sources={name:Path(__file__).with_name(name).read_bytes() for name in ('beginner.py','graph.py')}
    entry['generator_sources']={name:hashlib.sha256(source).hexdigest() for name,source in sources.items()}
    entry['generator_sha256']=hashlib.sha256(b''.join(name.encode()+b'\0'+source for name,source in sources.items())).hexdigest()
    return entry
