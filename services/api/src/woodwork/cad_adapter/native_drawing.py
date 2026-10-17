"""Public cadgen engineering drawing API, nominal metric A4 sheets from saved STEP."""
from pathlib import Path
from contextlib import redirect_stdout
import io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from woodwork.exports.core import sha256_file

NATIVE_DRAWING_VERSION = "1.0.0"


def generate_native_drawings(out_dir: Path, resolved: dict, metadata: dict):
    from cadgen import read_step
    from cadgen.eng_drawing import Sheet, eng_drawing

    folder = out_dir / "drawings"
    folder.mkdir(exist_ok=True)
    paths = []
    for definition in resolved["part_definitions"]:
        definition_id = definition["definition_id"]
        shape = read_step(out_dir / "parts" / f"{definition_id}.step")
        size = shape.bounding_box().size
        scale = min(.1, 120 / size.X, 55 / size.Y)
        output = folder / f"{definition_id}-metric.pdf"

        # Trusted code receives data through the closure; no Python source is
        # generated or interpolated. Public drawing decorators remain parameterless.
        @eng_drawing(out=output)
        def measured_part_sheet():
            sheet = Sheet("A4", scale=scale, title=f"{definition_id.upper()} - METRIC", part_number=definition_id,
                          revision=f"R{metadata['revision_number']}", units="mm", text_height=3.5,
                          notes=["A4 LANDSCAPE. DIMENSIONS IN MILLIMETERS. NOMINAL; NO FIT TOLERANCE SPECIFIED.",
                                 f"REVISION {metadata['revision_id']}", f"SPEC SHA256 {metadata['spec_sha256']}",
                                 "PART-LOCAL X=L, Y=W, Z=T. GRAIN FOLLOWS LOCAL L WHEN DECLARED."])
            # Explicit A4 view slots reserve space for projected dimension labels.
            # The pin's automatic iso label and wide-back top dimension can extend
            # beyond the frame even when its view geometry passes the layout guard.
            top = sheet.view(shape, "top", at=(88, 147), label="TOP")
            front = sheet.view(shape, "front", at=(88, 87), label="FRONT")
            right = sheet.view(shape, "right", at=(205, 87), label="RIGHT")
            iso_scale = min(scale * .5, .06)
            sheet.view(shape, "iso", at=(230, 150), scale=iso_scale, label=f"ISO 1:{1 / iso_scale:.4g}")
            top.overall()
            front.overall()
            right.overall()
            return sheet

        with redirect_stdout(io.StringIO()):
            measured_part_sheet()
        # The native renderer writes vector outlines, with no searchable text.
        # Add an application provenance caption without replacing its projections
        # or measured native dimensions, then bind PDF metadata to saved STEP bytes.
        reader = PdfReader(output)
        page = reader.pages[0]
        overlay = io.BytesIO()
        caption = canvas.Canvas(overlay, pagesize=(float(page.mediabox.width), float(page.mediabox.height)), invariant=1)
        caption.setFont("Helvetica", 7.5)
        measured = definition["finished_mm"]
        caption.drawString(17, float(page.mediabox.height) - 9,
                           f"SAVED STEP / mm: L {measured['length_mm']}  W {measured['width_mm']}  T {measured['thickness_mm']}  |  REV {metadata['revision_id']}")
        caption.save()
        overlay.seek(0)
        page.merge_page(PdfReader(overlay).pages[0])
        writer = PdfWriter()
        writer.add_page(page)
        writer.add_metadata({"/WoodworkRevision": metadata["revision_id"], "/WoodworkSpecSHA256": metadata["spec_sha256"],
                             "/WoodworkDefinition": definition_id, "/WoodworkUnits": "mm",
                             "/WoodworkSourceStepSHA256": sha256_file(out_dir / "parts" / f"{definition_id}.step")})
        with output.open("wb") as stream:
            writer.write(stream)
        paths.append(output)
    return paths
