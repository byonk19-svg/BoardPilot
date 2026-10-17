"""Cumulative, revision-bound design PDFs and technically checked recipe packets."""
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import uuid
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

from woodwork.cad_adapter import validate_artifact_set
from woodwork.cad_adapter.native_drawing import NATIVE_DRAWING_VERSION, generate_native_drawings
from woodwork.cad_adapter.verifier import require
from woodwork.domain import hash_json
from woodwork.exports.core import artifact_record, canonical_bytes, sha256_file, write_json
from woodwork.exports.dimensions import format_schedule, schedule_formatting, saved_schedule_formatting
from woodwork.recipes import public_catalog, resolve_recipe

DOCUMENTS_VERSION = "1.1.0"
MARGIN = 42


class Packet:
    def __init__(self, path, spec, resolved, metadata, measured, recipe):
        self.spec, self.resolved, self.metadata, self.measured, self.recipe = spec, resolved, metadata, measured, recipe
        self.paper = A4 if spec["documents"]["paper_size"] == "a4" else letter
        self.width, self.height = self.paper
        self.content = self.width - 2 * MARGIN
        self.canvas = canvas.Canvas(str(path), pagesize=self.paper, invariant=1, pageCompression=1)
        self.canvas.setTitle(f"Woodworking Planner - revision {metadata['revision_id']}")
        self.page_count = 0

    def measurement(self, value):
        return format_schedule(value, schedule_formatting(self.spec))

    def text(self, text, x, y, width=None, size=10, bold=False, color=colors.black):
        style = ParagraphStyle("packet", fontName="Helvetica-Bold" if bold else "Helvetica", fontSize=size, leading=size * 1.35, textColor=color)
        paragraph = Paragraph(escape(str(text)), style)
        w, h = paragraph.wrap(width or self.content, self.height)
        paragraph.drawOn(self.canvas, x, y - h)
        return y - h

    def page(self, title, subtitle="Measured design packet"):
        if self.page_count:
            self.canvas.showPage()
        self.page_count += 1
        c = self.canvas
        c.setStrokeColor(colors.HexColor("#263238"))
        c.setLineWidth(.6)
        c.line(MARGIN, self.height - 49, self.width - MARGIN, self.height - 49)
        self.text("WOODWORKING PLANNER", MARGIN, self.height - 25, size=11, bold=True)
        self.text(subtitle, self.width - MARGIN - 235, self.height - 25, width=235, size=9)
        self.text(title, MARGIN, self.height - 66, size=18, bold=True)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#37474f"))
        c.drawString(MARGIN, 28, f"Revision {self.metadata['revision_id']}  |  {self.spec['documents']['paper_size'].upper()}  |  Page {self.page_count}")
        c.drawString(MARGIN, 16, f"Spec SHA-256 {self.metadata['spec_sha256']}")
        c.setFillColor(colors.black)
        return self.height - 103

    def rule(self, y):
        self.canvas.setStrokeColor(colors.HexColor("#c7ced1"))
        self.canvas.line(MARGIN, y, self.width - MARGIN, y)

    def row(self, label, value, y, label_width=130):
        self.text(label, MARGIN, y, width=label_width - 10, size=10, bold=True)
        return self.text(value, MARGIN + label_width, y, width=self.content - label_width, size=10) - 8

    def dimension(self, x1, y1, x2, y2, label, *, vertical=False):
        c = self.canvas
        c.setStrokeColor(colors.black)
        c.setFillColor(colors.black)
        c.setLineWidth(.55)
        c.line(x1, y1, x2, y2)
        if vertical:
            c.line(x1-3, y1, x1+3, y1)
            c.line(x2-3, y2, x2+3, y2)
            c.saveState()
            c.translate(x1 - 7, (y1+y2)/2)
            c.rotate(90)
            c.setFont("Helvetica", 9)
            c.drawCentredString(0, 0, label)
            c.restoreState()
        else:
            c.line(x1, y1-3, x1, y1+3)
            c.line(x2, y2-3, x2, y2+3)
            c.setFont("Helvetica", 9)
            c.drawCentredString((x1+x2)/2, y1+7, label)

    def assembly_views(self):
        c = self.canvas
        dimensions = self.spec["dimensions"]
        w, h, d = (float(dimensions[key]) for key in ("outside_width_mm", "outside_height_mm", "outside_depth_mm"))
        scale = min(270/h, (self.content-175)/(w+d))
        origin_x, origin_y = MARGIN+32, 110
        side_x = origin_x + w*scale + 93
        instances = sorted(self.measured["instances"], key=lambda i: i["instance_id"] != "back")
        c.setLineWidth(.65)
        for item in instances:
            lo, hi = item["world_aabb_mm"]["min"], item["world_aabb_mm"]["max"]
            c.setFillColor(colors.HexColor("#f1f3f4") if item["instance_id"] == "back" else colors.HexColor("#cfd8dc"))
            c.setStrokeColor(colors.HexColor("#455a64"))
            c.rect(origin_x+lo[0]*scale, origin_y+lo[2]*scale, (hi[0]-lo[0])*scale, (hi[2]-lo[2])*scale, fill=1, stroke=1)
            if item["instance_id"] in {"bottom", "top"} or item["instance_id"].startswith("shelf_"):
                center_y = origin_y+(lo[2]+hi[2])*scale/2
                c.line(origin_x+w*scale, center_y, origin_x+w*scale+9, center_y)
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 9)
                c.drawString(origin_x+w*scale+13, center_y-3, item["instance_id"])
        c.setFillColor(colors.HexColor("#f1f3f4"))
        c.rect(side_x, origin_y, d*scale, h*scale, fill=1, stroke=1)
        back = next(i for i in instances if i["instance_id"] == "back")
        y0 = back["world_aabb_mm"]["min"][1]
        c.setFillColor(colors.HexColor("#b0bec5"))
        c.rect(side_x+y0*scale, origin_y, (d-y0)*scale, h*scale, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        opening = self.resolved["openings"][-1]
        side_label_y = origin_y + (float(opening["z_min_mm"]) + float(opening["z_max_mm"])) * scale / 2
        c.line(origin_x+3, side_label_y, origin_x+17, side_label_y)
        c.drawString(origin_x+20, side_label_y-3, "side_left")
        c.line(origin_x+w*scale-3, side_label_y, origin_x+w*scale-17, side_label_y)
        c.drawRightString(origin_x+w*scale-20, side_label_y-3, "side_right")
        c.drawCentredString(origin_x+w*scale/2, origin_y-17, "FRONT - full-height sides and between-side panels")
        c.drawCentredString(side_x+d*scale/2, origin_y-34, "RIGHT - back included in outside depth")
        c.drawString(side_x+4, origin_y+h*scale+9, "back")
        self.dimension(origin_x, origin_y+h*scale+22, origin_x+w*scale, origin_y+h*scale+22, self.measurement(dimensions["outside_width_mm"]))
        self.dimension(origin_x-18, origin_y, origin_x-18, origin_y+h*scale, self.measurement(dimensions["outside_height_mm"]), vertical=True)
        self.dimension(side_x, origin_y-16, side_x+d*scale, origin_y-16, self.measurement(dimensions["outside_depth_mm"]))

    def overview(self):
        y = self.page("Design overview")
        y = self.text(self.spec["project_name"], MARGIN, y, size=16, bold=True) - 12
        state = "DESIGN PACKET - CONSTRUCTION RECIPE UNSELECTED" if self.recipe["status"] == "recipe_unselected" else f"DESIGN PACKET - CONSTRUCTION {self.recipe['status'].upper()}"
        if self.recipe["status"] == "complete":
            state = "TECHNICAL FABRICATION METHOD COMPLETE - PHYSICAL REVIEW PENDING"
        y = self.text(state, MARGIN, y, size=11, bold=True) - 10
        y = self.text("Saved CAD, cut dimensions, drawings and this packet describe the same immutable revision. Outside depth includes the applied back. Dimensions are nominal; no fabrication fit tolerance or shelf load rating is supplied.", MARGIN, y, size=10) - 12
        y = self.row("Verified geometry", f"{len(self.resolved['part_instances'])} physical panels; {len(self.resolved['part_definitions'])} semantic definitions; {len(self.resolved['cut_groups'])} manufacturing cut groups", y)
        y = self.row("Unit reference", self.measurement("25.4") + "; approximate fractions are explicitly labeled.", y)
        self.assembly_views()

    def schedule(self):
        y = self.page("Instances and clear openings")
        y = self.text("Board identity and installed centers (millimeters)", MARGIN, y, size=11, bold=True) - 10
        for instance in self.resolved["part_instances"]:
            center = instance["center_mm"]
            y = self.row(instance["instance_id"], f"{instance['definition_id']} | center X {center['x']}, Y {center['y']}, Z {center['z']} mm", y)
        y -= 5
        self.rule(y)
        y -= 15
        y = self.text("Clear openings - measured between saved opposing faces", MARGIN, y, size=11, bold=True) - 10
        for opening in self.resolved["openings"]:
            label = f"Opening {opening['opening_index'] + 1}"
            values = f"Width {self.measurement(opening['clear_width_mm'])}; depth {self.measurement(opening['clear_depth_mm'])}; clear height {self.measurement(opening['resolved_clear_height_mm'])}. Z faces {opening['z_min_mm']} to {opening['z_max_mm']} mm."
            y = self.row(label, values, y)
        require(y > 55, "Instance/opening schedule exceeds printable page")

    def cuts_and_materials(self):
        y = self.page("Grouped cuts and materials")
        y = self.text("Finished sizes, rough blanks and kerf remain separate. Grain is local L where declared. Groups combine panels only when their complete manufacturing fingerprint matches.", MARGIN, y) - 12
        for group in self.resolved["cut_groups"]:
            y = self.text(f"Quantity {group['quantity']} - {', '.join(group['definition_ids'])}", MARGIN, y, bold=True, size=11) - 4
            y = self.text("Members: " + ", ".join(group["member_instance_ids"]), MARGIN, y, size=9) - 5
            f, r = group["finished_mm"], group["rough_mm"]
            y = self.row("Finished L / W / T", " | ".join(self.measurement(f[key]) for key in ("length_mm", "width_mm", "thickness_mm")), y)
            y = self.row("Rough L / W / T", " | ".join(self.measurement(r[key]) for key in ("length_mm", "width_mm", "thickness_mm")), y)
            y -= 4
        self.rule(y)
        y -= 14
        for material in self.spec["materials"].values():
            y = self.row(material["material_id"], f"{material['name']}. Actual {self.measurement(material['actual_thickness_mm'])}. Nominal label: {material['nominal_label']} (display only).", y)
        y = self.row("Cut process", f"Saw kerf {self.spec['manufacturing']['saw_kerf_mm']} mm; rough allowance per edge {self.spec['manufacturing']['rough_allowance_per_edge_mm']} mm. No sufficient sheet count is asserted without a verified stock layout.", y)
        require(y > 55, "Cut/material schedule exceeds printable page")

    def part_page(self, definition):
        y = self.page("Measured part - " + definition["definition_id"])
        y = self.row("Physical members", ", ".join(definition["member_instance_ids"]), y)
        for label, key in (("Local length L", "length_mm"), ("Local width W", "width_mm"), ("Actual thickness T", "thickness_mm")):
            y = self.row(label, self.measurement(definition["finished_mm"][key]), y)
        y = self.row("Local convention", "Centered origin. +X=L, +Y=W, +Z=T. Grain follows L where declared. This face diagram is nominal and uncompensated.", y)
        length, width, thickness = [float(definition["finished_mm"][k]) for k in ("length_mm", "width_mm", "thickness_mm")]
        scale = min((self.content-70)/length, 225/width)
        x, baseline = MARGIN+35, 215
        c = self.canvas
        c.setFillColor(colors.HexColor("#eceff1"))
        c.setStrokeColor(colors.black)
        c.rect(x, baseline, length*scale, width*scale, fill=1)
        self.dimension(x, baseline+width*scale+18, x+length*scale, baseline+width*scale+18, self.measurement(definition["finished_mm"]["length_mm"]))
        self.dimension(x-15, baseline, x-15, baseline+width*scale, self.measurement(definition["finished_mm"]["width_mm"]), vertical=True)
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawCentredString(x+length*scale/2, baseline+width*scale/2, definition["definition_id"] + " / local +T face")
        c.line(x+length*scale*.3, baseline+width*scale*.35, x+length*scale*.7, baseline+width*scale*.35)
        c.drawCentredString(x+length*scale/2, baseline+width*scale*.35-15, "L / grain direction" if definition["grain_axis"] == "L" else "L / no grain constraint")
        self.text("Thickness profile", x, 174, size=10, bold=True)
        c.rect(x, 133, length*scale, max(thickness*scale, 2), fill=0)
        self.text("T = " + self.measurement(definition["finished_mm"]["thickness_mm"]), x, 117, size=10)
        self.text(f"Companion drawing: drawings/{definition['definition_id']}-metric.pdf. Genuine cadgen A4 orthographic/isometric projections and native dimensions remain millimeters.", MARGIN, 78, size=9)

    def construction_page(self):
        y = self.page("Construction state and revision details")
        y = self.row("Construction status", self.recipe["status"], y)
        y = self.row("Physical review", "NOT REVIEWED - no actual build, service behavior or load capacity is certified.", y)
        for finding in self.recipe.get("findings", []):
            y = self.text(finding, MARGIN, y, size=10) - 8
        if self.recipe["status"] == "recipe_unselected":
            y = self.text("Missing attachment method: no pocket settings, fastener quantity or assembly instructions have been inferred from the panel geometry. Compatible recipes must be selected and checked against measured stock and the tool set.", MARGIN, y) - 12
            for entry in public_catalog():
                y = self.text("Installed method: " + entry["title"], MARGIN, y, size=10, bold=True) - 8
                bounds = entry["modeling_bounds"]
                outside = " x ".join(bounds[f"dimensions.outside_{axis}_mm"][0] for axis in ("width", "height", "depth"))
                main, back = (bounds[f"materials.{role}.actual_thickness_mm"][0] for role in ("main", "back"))
                y = self.text(f"This method's exact applicability is {outside} mm, actual {main} mm main panels and {back} mm back. This revision's measured stock is not silently changed to fit it.", MARGIN, y, size=10) - 12
        y = self.row("Template", self.spec["template"]["id"] + " / " + self.spec["template"]["version"], y)
        y = self.row("Resolved SHA-256", self.resolved["resolved_sha256"], y)
        y = self.row("Publication source", self.metadata["source_artifact_set_id"], y)
        self.text("The current STEP occurrence map is bound to the exact assembly hash. Rebuilds receive current selectors; old face/occurrence references are not manufacturing identity.", MARGIN, y-8, size=10)

    def recipe_pages(self):
        if self.recipe["status"] != "complete":
            return
        y = self.page("Recipe hardware and source review", "Technical fabrication instructions; physical review pending")
        y = self.row("Recipe", self.recipe["recipe_id"] + " / " + self.recipe["recipe_version"], y)
        y = self.row("Required tools", ", ".join(self.recipe["required_tools"]), y)
        for hardware in self.recipe["hardware"]:
            purchased = f"{hardware['purchased_quantity']} purchased in {hardware['packs_purchased']} pack(s)" if hardware['purchased_quantity'] is not None else "purchase quantity unknown"
            y = self.row(hardware["hardware_id"], f"{hardware['required_quantity']} required; {hardware['type']}; {hardware['sku']}; length {self.measurement(hardware['length_mm'])}; {purchased}. Price unknown.", y)
        for decision in self.recipe["author_decisions"]:
            y = self.text(decision, MARGIN, y, size=9) - 9
        y = self.text(self.recipe["installation"]["instruction"], MARGIN, y, size=10, bold=True) - 12
        require(y > 55, "Recipe hardware page exceeds printable page")
        y = self.page("Recipe primary sources and limits", "Source-backed method; no physical build performed")
        for source in self.recipe["source_records"]:
            y = self.text(source["title"], MARGIN, y, size=10, bold=True) - 5
            y = self.text(source["url"], MARGIN, y, size=9) - 5
            y = self.text(source["rule"], MARGIN, y, size=9) - 14
        require(y > 55, "Recipe source page exceeds printable page")
        self.operation_diagram()
        y = self.page("Back fastening reference coordinates", "Authored station layout; physical review pending")
        y = self.text("Coordinates below are cabinet-world millimeters: X is measured from the cabinet's left edge when viewed from the front; Z is measured from its bottom. When viewing the outside of back, cabinet +X runs left across the diagram. Align marked part IDs before fastening.", MARGIN, y, size=10) - 12
        for joint in self.recipe["joints"]:
            if joint["method"] != "back_glue_and_brad":
                continue
            other = next(i for i in joint["instance_ids"] if i != "back")
            points = [station["world_alignment_mm"] for station in joint["stations"]]
            if other.startswith("side_"):
                detail = f"X centerline {points[0]['x']} mm; Z stations " + ", ".join(p["z"] for p in points) + " mm."
            else:
                detail = f"Z centerline {points[0]['z']} mm; X stations " + ", ".join(p["x"] for p in points) + " mm."
            y = self.row(other + " / back", detail, y)
        y = self.text("Brads are the separately sourced 1-1/4 in 18-gauge type, driven through the back's outer local +T face. Keep the thin back square, supported and flush; check all points for breakout. Station spacing is an authored geometric choice, not an approved load capacity.", MARGIN, y-12, size=10)
        require(y > 55, "Back station coordinate page exceeds printable page")
        y = 0
        for index, operation in enumerate(self.recipe["operations"], 1):
            if y < 180:
                y = self.page("Assembly sequence", "Technical fabrication instructions; physical review pending")
            y = self.text(f"{index}. {operation['operation_id']}", MARGIN, y, bold=True, size=11) - 4
            y = self.text("Parts: " + ", ".join(operation["parts"]), MARGIN, y, size=9) - 5
            y = self.text(operation["instruction"], MARGIN, y, size=10) - 6
            if operation["joints"]:
                y = self.text("Connections: " + ", ".join(operation["joints"]), MARGIN, y, size=9) - 6
            y -= 10

    def operation_diagram(self):
        y = self.page("Operation reference diagrams", "Authored recipe illustration - not a native section/detail view")
        y = self.text("Horizontal panel: align the jig at the end-edge stations on marked local +T. Circles identify guide alignment references, not pocket-hole outlines. The manufacturer jig controls drilling depth and angle.", MARGIN, y, size=10) - 10
        definition = next(d for d in self.resolved["part_definitions"] if d["definition_id"] == "panel_horizontal")
        length, width = [float(definition["finished_mm"][k]) for k in ("length_mm", "width_mm")]
        scale = min((self.content-35)/length, 135/width)
        x, baseline = MARGIN+15, y-145
        c = self.canvas
        c.setStrokeColor(colors.black)
        c.rect(x, baseline, length*scale, width*scale)
        joints = [j for j in self.recipe["joints"] if j.get("machined_instance_id") == "bottom" and j["method"] == "pocket_hole_and_glue"]
        for joint in joints:
            for station in joint["stations"]:
                point = station["local_alignment_mm"]
                c.circle(x+(float(point["x"])+length/2)*scale, baseline+(float(point["y"])+width/2)*scale, 2.5, stroke=1, fill=0)
        c.setFont("Helvetica", 9)
        c.drawCentredString(x+length*scale/2, baseline+width*scale/2, "panel_horizontal / marked local +T face")
        c.drawCentredString(x+length*scale/2, baseline-11, "front edge / local -W")
        labels = ", ".join(self.measurement(s["from_front_edge_mm"]) for s in joints[0]["stations"])
        y = self.text("Front-edge station distances: " + labels, MARGIN, baseline-25, size=9) - 15
        y = self.text("Applied back: drive the selected brads through its outer local +T face on the marked carcass-edge centerlines. This authored layout has no inferred shelf-load rating.", MARGIN, y, size=10) - 9
        w, h = [float(self.spec["dimensions"][k]) for k in ("outside_width_mm", "outside_height_mm")]
        scale = min((self.content-35)/w, 225/h)
        x, baseline = MARGIN+15, y-235
        c.rect(x, baseline, w*scale, h*scale)
        for joint in self.recipe["joints"]:
            if joint["method"] == "back_glue_and_brad":
                for station in joint["stations"]:
                    point = station["world_alignment_mm"]
                    c.circle(x+(w-float(point["x"]))*scale, baseline+float(point["z"])*scale, 1.7, fill=1, stroke=0)
        self.text("back / outside face: cabinet +X runs left; +Z runs up. Exact stations follow on the next page.", MARGIN, baseline-12, size=9)

    def save(self):
        self.overview()
        self.schedule()
        self.cuts_and_materials()
        for definition in self.resolved["part_definitions"]:
            self.part_page(definition)
        self.construction_page()
        self.recipe_pages()
        self.canvas.save()
        return self.page_count


def validate_documents(out_dir, spec, resolved, metadata):
    out_dir = Path(out_dir)
    reader = PdfReader(out_dir / "design-packet.pdf")
    expected_size = A4 if spec["documents"]["paper_size"] == "a4" else letter
    text = " ".join("\n".join(page.extract_text() for page in reader.pages).split())
    require(bool(reader.pages) and all(abs(float(page.mediabox.width)-expected_size[0]) < .01 and abs(float(page.mediabox.height)-expected_size[1]) < .01 for page in reader.pages), "Application PDF paper size mismatch")
    require(metadata["revision_id"] in text and metadata["spec_sha256"] in text and resolved["resolved_sha256"] in text, "Application PDF revision binding missing")
    source_id = metadata.get("source_artifact_set_id")
    if source_id is None and (out_dir / "manifest.json").is_file():
        source_id = json.loads((out_dir / "manifest.json").read_text())["source_artifact_set_id"]
    require(source_id is not None and source_id in text, "Application PDF source artifact set binding missing")
    policy = saved_schedule_formatting(json.loads((out_dir / 'build-inputs.json').read_text(encoding='utf-8')), spec, 'documents')
    require('Unit reference ' + format_schedule("25.4", policy) in text, "Schedule unit reference missing")
    require(all(instance["instance_id"] in text for instance in resolved["part_instances"]), "Application PDF omits physical part identity")
    for definition in resolved["part_definitions"]:
        for label, key in (("Local length L", "length_mm"), ("Local width W", "width_mm"), ("Actual thickness T", "thickness_mm")):
            require(label + ' ' + format_schedule(definition["finished_mm"][key], policy) in text, "Application PDF dimension mismatch")
    pdfs = [{"path": "design-packet.pdf", "pages": len(reader.pages), "paper": spec["documents"]["paper_size"], "sha256": sha256_file(out_dir / "design-packet.pdf")}]
    for definition in resolved["part_definitions"]:
        relative = f"drawings/{definition['definition_id']}-metric.pdf"
        native = PdfReader(out_dir / relative)
        require(len(native.pages) == 1 and abs(float(native.pages[0].mediabox.width)-A4[1]) < .01 and abs(float(native.pages[0].mediabox.height)-A4[0]) < .01, "Native PDF must be metric landscape A4")
        require(native.metadata.get("/WoodworkRevision") == metadata["revision_id"] and native.metadata.get("/WoodworkSpecSHA256") == metadata["spec_sha256"] and native.metadata.get("/WoodworkDefinition") == definition["definition_id"], "Native PDF provenance mismatch")
        require(native.metadata.get("/WoodworkSourceStepSHA256") == sha256_file(out_dir / f"parts/{definition['definition_id']}.step") and native.metadata.get("/WoodworkUnits") == "mm", "Native PDF saved STEP binding mismatch")
        native_text = " ".join(native.pages[0].extract_text().split())
        dims = definition["finished_mm"]
        require(f"L {dims['length_mm']} W {dims['width_mm']} T {dims['thickness_mm']}" in native_text, "Native PDF measured provenance caption mismatch")
        pdfs.append({"path": relative, "pages": 1, "paper": "a4_landscape", "units": "mm", "sha256": sha256_file(out_dir / relative), "native_dimension_text": "vector_outlines_not_text_extractable", "native_dimension_visual_review": "required_separately", "searchable_provenance": "application_caption"})
    return {"status": "passed", "revision_id": metadata["revision_id"], "spec_sha256": metadata["spec_sha256"], "resolved_sha256": resolved["resolved_sha256"], "source_artifact_set_id": source_id, "assembly_sha256": sha256_file(out_dir / "assembly.step"), "pdfs": pdfs,
            "visual_review": "required_separately", "native_units": "mm", "application_units": policy['units'],
            "application_fraction_denominator": policy['fraction_denominator'] if policy['units'] == 'dual' else None}


def add_documents(source_dir, out_dir, metadata, spec, resolved, *, progress=None):
    source_dir, out_dir = Path(source_dir).resolve(), Path(out_dir).resolve()
    verified = validate_artifact_set(source_dir)
    source = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))
    require(not out_dir.exists() or not any(out_dir.iterdir()), "Document staging directory must be new and empty")
    require(metadata["project_id"] == source["project_id"] and metadata["revision_id"] == source["revision_id"] and metadata["revision_number"] == source["revision_number"], "Document source revision mismatch")
    require(resolved["spec_sha256"] == source["spec_sha256"] and resolved["resolved_sha256"] == source["resolved_sha256"] and hash_json(spec) == source["spec_sha256"], "Document source hashes mismatch")
    require(metadata.get("source_artifact_set_id", source["artifact_set_id"]) == source["artifact_set_id"], "Document source artifact identity mismatch")
    metadata = {**metadata, "spec_sha256": source["spec_sha256"], "resolved_sha256": source["resolved_sha256"], "source_artifact_set_id": source["artifact_set_id"]}
    out_dir.mkdir(parents=True, exist_ok=True)
    for record in source["artifacts"]:
        target = out_dir / record["relative_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_dir / record["relative_path"], target)
    recipe = resolve_recipe(spec, resolved)
    if progress:
        progress("generating_documents")
    page_count = Packet(out_dir / "design-packet.pdf", spec, resolved, metadata, verified["geometry"], recipe).save()
    generate_native_drawings(out_dir, resolved, metadata)
    recipe_record = {"revision_id": metadata["revision_id"], "spec_sha256": metadata["spec_sha256"], "resolved_sha256": resolved["resolved_sha256"], **recipe}
    write_json(out_dir / "construction-recipe.json", recipe_record)
    material = json.loads((out_dir / "materials.json").read_text(encoding="utf-8"))
    material.update({"hardware": recipe["hardware"], "hardware_status": recipe["status"], "consumables": recipe.get("consumables", [])})
    write_json(out_dir / "materials.json", material)
    if progress:
        progress("verifying_documents")
    inputs = {"spec_sha256": metadata["spec_sha256"], "resolved_sha256": metadata["resolved_sha256"], "source_artifact_set_id": source["artifact_set_id"], "geometry_build_key_sha256": source["build_key_sha256"], "geometry_inputs": json.loads((source_dir / "build-inputs.json").read_text()), "documents_version": DOCUMENTS_VERSION, "native_drawing_version": NATIVE_DRAWING_VERSION, "document_options": spec["documents"], "recipe_fingerprint": recipe["fingerprint"], "schedule_formatting": schedule_formatting(spec), "renderer_sha256": {"documents": sha256_file(Path(__file__)), "native_drawing": sha256_file(Path(__file__).parents[1] / "cad_adapter/native_drawing.py"), "dimensions": sha256_file(Path(__file__).with_name('dimensions.py'))}}
    write_json(out_dir / "build-inputs.json", inputs)
    evidence = validate_documents(out_dir, spec, resolved, metadata)
    write_json(out_dir / "document-validation.json", evidence)
    records = {r["relative_path"]: artifact_record(out_dir, r["relative_path"], r["kind"], r["mime_type"], metadata, r["definition_id"]) for r in source["artifacts"]}
    sidecar = json.loads((out_dir / "step-instance-map.json").read_text())
    sidecar["assembly_artifact_id"] = records["assembly.step"]["artifact_id"]
    write_json(out_dir / "step-instance-map.json", sidecar)
    for relative in ("step-instance-map.json", "materials.json", "build-inputs.json", "construction-recipe.json", "document-validation.json"):
        records[relative] = artifact_record(out_dir, relative, "json", "application/json", metadata)
    records["design-packet.pdf"] = artifact_record(out_dir, "design-packet.pdf", "pdf", "application/pdf", metadata)
    for definition in resolved["part_definitions"]:
        relative = f"drawings/{definition['definition_id']}-metric.pdf"
        records[relative] = artifact_record(out_dir, relative, "pdf", "application/pdf", metadata, definition["definition_id"])
    manifest = deepcopy(source)
    manifest.update({"artifact_set_id": metadata.get("artifact_set_id", str(uuid.uuid4())), "source_artifact_set_id": source["artifact_set_id"], "artifacts": list(records.values()), "build_key_sha256": hash_json(inputs),
                     "construction": {key: recipe[key] for key in ("status", "recipe_id", "recipe_version", "physical_review", "findings")}})
    manifest["versions"]["recipe_fingerprint"] = recipe["fingerprint"]
    manifest["validation"]["documents"] = "passed"
    manifest["capabilities"] = list(dict.fromkeys([*source["capabilities"], "documents", *(["construction_instructions"] if recipe["status"] == "complete" else [])]))
    write_json(out_dir / "manifest.json", manifest)
    validate_artifact_set(out_dir)
    return manifest
