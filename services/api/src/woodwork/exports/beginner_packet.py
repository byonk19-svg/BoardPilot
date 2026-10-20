"""Illustrated instructions from the checked 18/6 mm bookcase operation graph."""
from fractions import Fraction

from reportlab.lib import colors

from woodwork.cad_adapter.verifier import require
from woodwork.recipes.beginner import LABELS
from .documents import MARGIN, Packet

INK = colors.HexColor('#253f45')
WOOD = colors.HexColor('#e9ddc4')
ACCENT = colors.HexColor('#a33c24')


class BeginnerPacket(Packet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        require(self.recipe['status'] == 'complete', 'Beginner instructions require a checked recipe')
        self.guide_page_map = []
        self.parts = {p['instance_id']: p for p in self.resolved['part_instances']}
        self.definitions = {d['definition_id']: d for d in self.resolved['part_definitions']}
        self.hardware = {h['hardware_id']: h for h in self.recipe['hardware']}

    def label(self, text, x, y, size=10, color=INK, align='left'):
        c = self.canvas
        c.setFillColor(color)
        c.setFont('Helvetica-Bold', size)
        getattr(c, {'left': 'drawString', 'center': 'drawCentredString', 'right': 'drawRightString'}[align])(x, y, text)

    def panel(self, x, y, w, h, highlight=False):
        c = self.canvas
        c.setFillColor(WOOD)
        c.setStrokeColor(ACCENT if highlight else INK)
        c.setLineWidth(2 if highlight else .8)
        c.rect(x, y, w, h, fill=1, stroke=1)

    def dot(self, x, y):
        self.canvas.setFillColor(ACCENT)
        self.canvas.circle(x, y, 2.2, fill=1, stroke=0)

    def arrow(self, x1, y1, x2, y2):
        from math import atan2, cos, sin
        c = self.canvas
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1.4)
        c.line(x1, y1, x2, y2)
        a = atan2(y2-y1, x2-x1)
        for offset in (-.5, .5):
            c.line(x2, y2, x2-8*cos(a+offset), y2-8*sin(a+offset))

    def front(self, x, y, height, highlight=None, rear=False, marks=False, diagonals=False):
        w = float(self.spec['dimensions']['outside_width_mm'])
        h = float(self.spec['dimensions']['outside_height_mm'])
        s = height/h
        for item in sorted(self.measured['instances'], key=lambda p: p['instance_id'] != 'back'):
            name = item['instance_id']
            if name == 'back' and not rear:
                continue
            lo, hi = item['world_aabb_mm']['min'], item['world_aabb_mm']['max']
            px = w-hi[0] if rear else lo[0]
            self.panel(x+px*s, y+lo[2]*s, (hi[0]-lo[0])*s, (hi[2]-lo[2])*s, name == highlight)
        if rear and marks:
            for joint in self.recipe['joints']:
                if joint['machined_instance_id'] == 'back':
                    for point in joint['stations']:
                        p = point['entry_world_mm']
                        self.dot(x+(w-float(p['x']))*s, y+float(p['z'])*s)
        if not rear:
            for name, part in self.parts.items():
                if name == 'back':
                    continue
                px = float(part['center_mm']['x'])*s
                pz = float(part['center_mm']['z'])*s
                if name.startswith('side_'):
                    self.label(LABELS[name][0], x+px+(-14 if name == 'side_left' else 14), y+height*.48, align='center')
                else:
                    self.label(LABELS[name][0], x+px, y+pz+6, align='center')
        if diagonals:
            self.canvas.setDash(4, 3)
            self.canvas.setStrokeColor(ACCENT)
            self.canvas.line(x, y, x+w*s, y+h*s)
            self.canvas.line(x, y+h*s, x+w*s, y)
            self.canvas.setDash()
        return w*s

    def introduction(self):
        y = self.page('Build your bookcase', 'Illustrated guide | 18 mm panels + 6 mm back')
        y = self.text(self.spec['project_name'], MARGIN, y, size=14, bold=True)-12
        dims = self.spec['dimensions']
        y = self.text('Finished outside size: ' + ' x '.join(f"{dims[k]} mm" for k in ('outside_width_mm', 'outside_height_mm', 'outside_depth_mm')) + ' (width x height x depth). Depth includes the back; screw heads must be flush.', MARGIN, y, size=11)-12
        y = self.text('Build with screws through the sides into the ends of the horizontal panels, plus wood glue. The back is glued and fastened with shorter screws. Read the whole guide and practise both joints on matching offcuts first.', MARGIN, y, size=11)-12
        self.text('A physical build has not been performed. No shelf load rating is supplied. This guide is not a full-size drilling template. CAD files show nominal panel blanks; the drill marks are planned references.', MARGIN, y, size=10)
        self.front(MARGIN+50, 110, 220)
        sx = MARGIN+330
        self.panel(sx, 110, 72, 220)
        self.panel(sx+72-72*6/304.8, 110, 72*6/304.8, 220, True)
        self.label('RIGHT SIDE VIEW', sx+36, 90, 9, align='center')
        self.label('G - Back', sx+30, 350, 10)
        self.arrow(sx+45, 340, sx+71, 325)
        self.label('Front', sx-2, 345, 9)
        self.label('A / B = full-height sides', MARGIN+20, 77, 10)
        self.label('C / F = bottom / top     D / E = fixed shelves', MARGIN+20, 61, 10)

    def simple_cuts(self):
        y = self.page('Your seven parts - finished cut sizes', 'Use exact millimeters for cutting and marking')
        y = self.text('Keep these finished sizes and the actual plywood thicknesses. The 18 mm side panels fit outside the four shorter horizontal panels. The full-size 6 mm back sits on the rear edges.', MARGIN, y, size=11)-18
        for names in (('side_left',), ('side_right',), ('bottom', 'shelf_01', 'shelf_02', 'top'), ('back',)):
            d = self.definitions[self.parts[names[0]]['definition_id']]
            labels = '; '.join(f'{LABELS[n][0]} {LABELS[n][1]}' for n in names)
            y = self.text(labels, MARGIN, y, size=11, bold=True)-6
            f = d['finished_mm']
            y = self.text(f"Quantity {len(names)} | {f['length_mm']} x {f['width_mm']} x {f['thickness_mm']} mm (length x width x thickness)", MARGIN, y, size=11)-16
        self.rule(y)
        y -= 16
        for role in ('main', 'back'):
            m = self.spec['materials'][role]
            y = self.text(f"{m['name']}: actual {m['actual_thickness_mm']} mm. Nominal label: {m['nominal_label']} (a label only).", MARGIN, y, size=10)-12
        allowance = self.spec['manufacturing']['rough_allowance_per_edge_mm']
        y = self.text(f"Saw kerf: {self.spec['manufacturing']['saw_kerf_mm']} mm. Rough allowance per edge: {allowance} mm. Use the stock-layout PDF for sheet cutting; finish rough blanks to these sizes before assembly. Kerf is waste, not an addition to a finished part.", MARGIN, y, size=10)-12
        y = self.text('Three equal openings: 280.8 mm high. Shelf undersides: 298.8 and 597.6 mm above the outside bottom. Mark screw centres separately as shown in Step 2.', MARGIN, y, size=11)-12
        require(y > 65, 'Beginner cut list exceeds printable area')

    def tools_page(self):
        y = self.page('Tools, screws and drill settings', 'Check actual screws and matching offcuts first')
        y = self.text('Tools: panel saw with a supported cutting setup; drill/driver and matching driver bits; square; accurate metric measuring tools; clamps/corner clamps; helper or temporary support blocks; sacrificial backer; countersink matching each flat head; positive drill-depth stops; eye, hearing and dust protection.', MARGIN, y, size=10.5)-14
        for key, title in (('carcass_screw', 'MAIN JOINTS'), ('back_screw', 'BACK JOINTS')):
            h = self.hardware[key]
            y = self.text(f"{title}: {h['required_quantity']} required - {h['type']}", MARGIN, y, size=11, bold=True)-6
            y = self.text(f"Length {h['length_mm']} mm; specification {h['sku']}. Buy matching wood screws; pack counts and prices are unknown. Include spares for offcut trials.", MARGIN, y, size=10)-7
            total = Fraction(h['pilot_into_receiver_mm']) + Fraction('18' if key == 'carcass_screw' else '6')
            y = self.text(f"Clearance through outer panel: {'11/64' if key == 'carcass_screw' else '9/64'} in ({h['clearance_mm']} mm). Mating pilot: {'1/8' if key == 'carcass_screw' else '7/64'} in ({h['pilot_mm']} mm), {h['pilot_into_receiver_mm']} mm into the receiving edge; {float(total):g} mm total from the entry face.", MARGIN, y, size=10.5)-12
        y = self.text('Use wood glue suitable for plywood. Follow its label for clamp time, cure, temperature and cleanup. Do not lift/turn an uncured frame. The documented Titebond Original example stays unstressed at least 24 hours, or longer if its conditions require.', MARGIN, y, size=10.5)-12
        y = self.text('A pilot guides the threads in the receiving edge. A clearance hole lets the screw slide through the outer panel. A countersink seats its flat head flush. Published bit sizes are starting points: test the actual screw and plywood before drilling furniture.', MARGIN, y, size=10.5)-12
        y = self.text('The 6 mm back needs extra care: test the actual #6 flat head on a 6 mm offcut. Countersink at most 2 mm, leaving at least 4 mm of panel. This is an authored stop limit, not a supplier-certified safe depth. If a flush head crushes or pulls through, STOP and revise the fastening method; do not change the bookcase size or drive the head deeper.', MARGIN, y, size=10.5)-10
        require(y > 60, 'Beginner tools page exceeds printable area')

    def step_page(self, index, operation):
        title = f"Step {index}. {operation['title']}"
        y = self.page(title, 'Work in order | support and clamp before drilling')
        for number, action in enumerate(operation['actions'], 1):
            y = self.text(f'{number}. {action}', MARGIN, y, size=10.5)-10
        require(y > 355, f"Beginner step {index} text overlaps its illustration")
        figure = f"Figure {index} - {operation['title']}"
        self.text(figure, MARGIN, 340, size=10, bold=True)
        self.draw_step(operation['diagram'])
        self.text('Reference illustration; use written dimensions and a square. Never scale holes from this page.', MARGIN, 65, size=9)
        self.guide_page_map.append({'operation_id': operation['operation_id'], 'title': operation['title'], 'figure_label': figure, 'page': self.page_count, 'diagram': operation['diagram']})

    def draw_step(self, scene):
        c = self.canvas
        if scene == 'parts':
            x = MARGIN+28
            for i, name in enumerate(LABELS):
                px = x+(i % 4)*126
                py = 230-(i//4)*107
                self.panel(px, py, 82, 53, name == 'back')
                self.label(LABELS[name][0], px+41, py+23, 13, align='center')
                self.label(LABELS[name][1], px+41, py-16, 9, align='center')
            self.label('Label FRONT / BOTTOM; mark the outside face of each side.', MARGIN+10, 85, 9)
        elif scene == 'side_marks':
            main = [j for j in self.recipe['joints'] if j['method'] == 'through_side_screw_and_glue']
            for index, side in enumerate(('side_left', 'side_right')):
                x, y, width, height = MARGIN+90+index*235, 105, 72, 202
                self.panel(x, y, width, height)
                self.label(f'{LABELS[side][0]} OUTSIDE', x+width/2, 318, 10, align='center')
                for joint in main:
                    if joint['machined_instance_id'] != side:
                        continue
                    z = float(joint['stations'][0]['entry_world_mm']['z'])
                    py = y+z/914.4*height
                    c.setStrokeColor(INK)
                    c.line(x, py, x+width, py)
                    self.label(f'{z:g}', x-8, py-3, 8, align='right')
                    for station in joint['stations']:
                        self.dot(x+float(station['from_front_edge_mm'])/298.8*width, py)
                self.label('BOTTOM = 0', x+width/2, y-15, 9, align='center')
                self.label('FRONT', x-5, y+height*.5, 8, align='right')
            self.label('Depth marks from FRONT: 30 / 149.4 / 268.8 mm', MARGIN+20, 77, 10)
        elif scene in ('drill_section', 'back_fastening'):
            back = scene == 'back_fastening'
            through, pilot = (6, 12) if back else (18, 35)
            if not back:
                self.label('Offcut practice joint; drill furniture mating pilots in Step 4.', MARGIN+20, 310, 9)
            h = self.hardware['back_screw' if back else 'carcass_screw']
            scale = 7 if back else 4.8
            x, y = MARGIN+100, 172
            self.panel(x, y-38, through*scale, 76)
            self.panel(x+through*scale, y-32, (pilot+8)*scale, 64)
            c.setStrokeColor(ACCENT)
            c.setDash(3, 2)
            c.line(x, y, x+(through+pilot)*scale, y)
            c.setDash()
            c.setLineWidth(2)
            c.line(x, y-9, x, y+9)
            c.line(x, y-9, x+8, y)
            c.line(x, y+9, x+8, y)
            c.line(x+8, y, x+float(h['length_mm'])*scale, y)
            self.arrow(x-53, y, x-6, y)
            self.label('Entry / outside', x-5, y-68, 9, align='center')
            self.label(f'{through} mm outer panel', x+through*scale/2, y+55, 10, align='center')
            self.label('Receiving edge', x+(through+pilot/2)*scale, y+36, 10, align='center')
            self.dimension(x, y+96, x+(through+pilot)*scale, y+96, f'{through+pilot} mm TOTAL pilot depth')
            self.dimension(x+through*scale, y-62, x+(through+pilot)*scale, y-62, f'{pilot} mm INTO receiver')
            self.label(f"Screw length {h['length_mm']} mm; head flush", MARGIN+25, 89, 10)
            if back:
                self.label('Back countersink: max. 2 mm; at least 4 mm panel remains.', MARGIN+25, 74, 9)
        elif scene == 'back_layout':
            width = self.front(MARGIN+160, 90, 225, rear=True, marks=True)
            self.label('OUTSIDE REAR VIEW - G', MARGIN+160+width/2, 319, 10, align='center')
            self.label('BOTTOM = 0', MARGIN+160+width/2, 76, 9, align='center')
            self.text('36 dots = 36 short screws. Each dot must land in a receiving edge centre. See the back worksheet for exact marks.', MARGIN, 292, width=130, size=10)
        else:
            highlight = 'side_left' if scene == 'left_screws' else 'side_right' if scene == 'right_screws' else None
            x, y, height = MARGIN+145, 100, 205
            width = self.front(x, y, height, highlight=highlight, diagonals=scene == 'square')
            if highlight:
                for joint in self.recipe['joints']:
                    if joint['machined_instance_id'] == highlight:
                        z = float(joint['stations'][0]['entry_world_mm']['z'])/914.4*height
                        left = highlight == 'side_left'
                        px = x if left else x+width
                        self.arrow(px+(-40 if left else 40), y+z, px+(-4 if left else 4), y+z)
                self.label('3 screws per arrow / 12 on this side', MARGIN+40, 81, 10)
            elif scene == 'square':
                self.label('Equal diagonals + square corners', MARGIN+80, 81, 10)
            elif scene == 'final':
                self.text('Select the restraint and wall fasteners for your site. Attach to solid carcass per the kit instructions.', MARGIN, 300, width=125, size=10)
                self.arrow(x+width+65, y+height+8, x+width-12, y+height-5)
                self.label('Before loading', x+width+4, y+height+19, 9)
            else:
                self.text('Orientation: open FRONT faces UP. All back edges rest on the flat bench. Supports/clamps hold the free ends; drill from the outside of each side.', MARGIN, 300, width=125, size=10)
                self.label('Flat bench under BACK edges', x+width/2, 79, 9, align='center')
                c.setStrokeColor(INK)
                c.line(x-20, y-5, x+width+20, y-5)
                self.arrow(x+width+45, y+90, x+width+3, y+90)
                self.label('Clamp / support', x+width+12, y+108, 8)

    def back_worksheet(self):
        y = self.page('Back worksheet - exact fixing marks', 'All distances in millimeters | outside rear view')
        y = self.text('Mark from BOTTOM and from the LEFT edge as you look at the OUTSIDE REAR of G. These patterns are symmetric. Horizontal rows start at the receiving panel ends, 18 mm inside each side of G. Do not measure their 25 mm end offsets from the outside of G.', MARGIN, y, size=11)-16
        w = Fraction(self.spec['dimensions']['outside_width_mm'])
        for joint in self.recipe['joints']:
            if joint['machined_instance_id'] != 'back':
                continue
            receiver = next(n for n in joint['instance_ids'] if n != 'back')
            points = joint['stations']
            if receiver.startswith('side_'):
                from_left = w-Fraction(points[0]['entry_world_mm']['x'])
                detail = f"Vertical line {float(from_left):g} from rear-left edge; heights " + ', '.join(p['entry_world_mm']['z'] for p in points)
            else:
                xs = sorted(w-Fraction(p['entry_world_mm']['x']) for p in points)
                detail = f"Horizontal line {points[0]['entry_world_mm']['z']} above bottom; rear-left marks " + ', '.join(f'{float(v):g}' for v in xs)
            y = self.text(f"{LABELS[receiver][0]} {LABELS[receiver][1]}: {detail} mm.", MARGIN, y, size=10.5)-12
        y = self.text('Six marks on each of six receiving edges = 36 screws. Keep the back dry-clamped for mating pilots. Use the clearance and pilot sequence in Step 8; never drill freehand through an unsupported panel.', MARGIN, y, size=11)-10
        require(y > 65, 'Back worksheet exceeds printable area')

    def sources(self):
        records = self.recipe['source_records']
        for start in range(0, len(records), 3):
            y = self.page('Sources and construction limits', 'Published guidance + authored adaptation')
            for source in records[start:start+3]:
                y = self.text(source['title'], MARGIN, y, size=11, bold=True)-5
                y = self.text(source['url'], MARGIN, y, size=9)-7
                y = self.text(source['rule'], MARGIN, y, size=10)-18
            require(y > 65, 'Beginner sources exceed printable area')
        y = self.page('What was checked - and your checks', 'Technical appendix begins on the next page')
        for item in [
            'The app checks the exact saved panel dimensions, connection coverage, fastener counts, entry faces, drill directions, receiving panels and screw/pilot depths. Each assembly illustration is tied to an operation in that same checked recipe.',
            'Exact screw stations, depth stops and the shallow back countersink are authored adaptations. Published guidance is not certification of this exact furniture. Check actual stock, offcut performance, workholding, square, cure and fastening before use.',
            'If an offcut splits, strips, crushes, breaks through or cannot hold a flush screw head within the stated limits, stop. Do not substitute longer screws, change material thickness or enlarge a countersink to force the design to work.',
            'A physical build has not been performed. No shelf load rating or tested service behavior is supplied. Site restraint selection remains necessary before loading.',
            'CAD exports remain unmachined nominal panel blanks. Native metric drawings and the following measured schedules are technical references, not full-size drilling templates.',
        ]:
            y = self.text(item, MARGIN, y, size=11)-17
        require(y > 65, 'Beginner limits exceed printable area')

    def save(self):
        self.introduction()
        self.simple_cuts()
        self.tools_page()
        for index, operation in enumerate(self.recipe['operations'], 1):
            self.step_page(index, operation)
        self.back_worksheet()
        self.sources()
        self.overview()
        self.schedule()
        self.cuts_and_materials()
        for definition in self.resolved['part_definitions']:
            self.part_page(definition)
        self.construction_page()
        self.canvas.save()
        return self.page_count
