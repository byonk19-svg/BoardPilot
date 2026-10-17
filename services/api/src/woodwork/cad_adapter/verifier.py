"""Independent checks on saved CAD bytes, never renderer flags or triangle counts."""
import itertools
import json
import math
import re
import struct
from decimal import Decimal
from pathlib import Path

from woodwork.exports.core import canonical_bytes, sha256_file

POSITION_TOLERANCE_MM = 0.000002
GLB_TOLERANCE_M = 0.00000015
ID = re.compile(r"[a-z][a-z0-9_]{0,99}\Z")
MM = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]{0,5}[1-9])?\Z")


class CadValidationError(ValueError):
    """Artifact sets with this failure may not be published."""


def require(condition, message):
    if not condition:
        raise CadValidationError(message)


def near(actual, expected, tolerance=POSITION_TOLERANCE_MM):
    require(len(actual) == len(expected) and all(math.isfinite(a) and abs(a - float(e)) <= tolerance for a, e in zip(actual, expected)), f"Measured geometry disagrees: {actual} versus {expected}")


def validate_ledger(spec, resolved):
    """Revalidate hash, references, bounds, identities, and rigid transformations."""
    from woodwork.domain import ProjectSpec, compile_project, hash_json, resolved_hash

    ProjectSpec.model_validate(spec)
    require(resolved_hash(resolved) == resolved["resolved_sha256"], "Resolved ledger checksum mismatch")
    require(hash_json(spec) == resolved["spec_sha256"], "Spec does not match resolved source")
    require(canonical_bytes(spec) == canonical_bytes(resolved["spec"]), "Resolved source snapshot mismatch")
    definitions = resolved["part_definitions"]
    instances = resolved["part_instances"]
    require(len(definitions) == 3 and 5 <= len(instances) <= 9, "Unsupported template cardinality")
    definition_ids = [d["definition_id"] for d in definitions]
    instance_ids = [i["instance_id"] for i in instances]
    require(len(set(definition_ids)) == len(definition_ids) and len(set(instance_ids)) == len(instance_ids), "Duplicate manufacturing identity")
    require(all(ID.fullmatch(value) for value in definition_ids + instance_ids), "Unsafe manufacturing identity")
    for definition in definitions:
        require(definition["quantity"] == len(definition["member_instance_ids"]), "Definition quantity/member mismatch")
        members = [i["instance_id"] for i in instances if i["definition_id"] == definition["definition_id"]]
        require(set(members) == set(definition["member_instance_ids"]) and len(members) == definition["quantity"], "Definition does not match instance ledger")
        for key, value in definition["finished_mm"].items():
            require(isinstance(value, str) and MM.fullmatch(value) is not None, "Invalid canonical panel dimension")
            maximum = Decimal("40") if key == "thickness_mm" else Decimal("2400")
            require(0 < Decimal(value) <= maximum, "Panel dimension outside supported bounds")
            rough = definition["rough_mm"][key]
            require(isinstance(rough, str) and MM.fullmatch(rough) is not None and Decimal(rough) >= Decimal(value), "Invalid resolved rough blank dimension")
            if key == "thickness_mm":
                require(rough == value, "Rough allowance cannot change thickness")
        require(definition["material_id"] in {m["material_id"] for m in spec["materials"].values()}, "Unknown definition material")
        require(type(definition["quantity"]) is int and definition["quantity"] > 0, "Invalid definition quantity")
        require(not definition.get("machining"), "Unsupported machining requires a newer adapter")
    for instance in instances:
        require(instance["definition_id"] in definition_ids, "Unknown definition reference")
        rotation = instance["rotation_cad_rows"]
        require(len(rotation) == 3 and all(len(row) == 3 and all(type(v) is int and v in (-1, 0, 1) for v in row) for row in rotation), "Invalid rotation")
        for i in range(3):
            for j in range(3):
                require(sum(rotation[k][i] * rotation[k][j] for k in range(3)) == int(i == j), "Non-rigid rotation")
        a, b, c = rotation
        determinant = a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])
        require(determinant == 1, "Reflected instance transform")
        require(set(instance["center_mm"]) == set("xyz"), "Invalid center contract")
        for value in instance["center_mm"].values():
            require(isinstance(value, str) and MM.fullmatch(value) is not None and abs(Decimal(value)) <= 2400, "Invalid resolved center")
    allowed = resolved["expected_contact_pairs"]
    require(len({tuple(sorted(pair)) for pair in allowed}) == len(allowed), "Duplicate contact declarations")
    require(all(len(pair) == 2 and pair[0] != pair[1] and set(pair) <= set(instance_ids) for pair in allowed), "Unknown contact identity")
    # Checksums alone do not prove derivation: an archive could rehash an invented
    # cut size, grain policy, or machining fingerprint. Recompile through the
    # authoritative domain engine and compare the entire canonical ledger.
    from woodwork.application import compile_design
    trusted = compile_design(spec)
    require(canonical_bytes(trusted) == canonical_bytes(resolved), "Resolved ledger differs from authoritative spec compilation")


def _identity():
    return [[int(i == j) for j in range(4)] for i in range(4)]


def _multiply(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _node_matrix(node):
    if "matrix" in node:
        require(len(node["matrix"]) == 16, "Invalid GLB matrix")
        return [[node["matrix"][j * 4 + i] for j in range(4)] for i in range(4)]
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    scale = node.get("scale", [1, 1, 1])
    translation = node.get("translation", [0, 0, 0])
    rows = [[1 - 2 * (y*y + z*z), 2 * (x*y - z*w), 2 * (x*z + y*w)], [2 * (x*y + z*w), 1 - 2 * (x*x + z*z), 2 * (y*z - x*w)], [2 * (x*z - y*w), 2 * (y*z + x*w), 1 - 2 * (x*x + y*y)]]
    matrix = _identity()
    for i in range(3):
        for j in range(3):
            matrix[i][j] = rows[i][j] * scale[j]
        matrix[i][3] = translation[i]
    return matrix


def glb_positions(path: Path):
    raw = path.read_bytes()
    require(len(raw) >= 28 and struct.unpack_from("<III", raw) == (0x46546C67, 2, len(raw)), "Invalid GLB header")
    json_size = struct.unpack_from("<I", raw, 12)[0]
    require(raw[16:20] == b"JSON" and raw[24 + json_size:28 + json_size] == b"BIN\0", "Unsupported GLB container")
    document = json.loads(raw[20:20 + json_size])
    binary = raw[28 + json_size:]
    require(len(binary) >= struct.unpack_from("<I", raw, 20 + json_size)[0], "Truncated GLB binary")
    meshes = []
    for mesh in document["meshes"]:
        positions = []
        for primitive in mesh["primitives"]:
            accessor = document["accessors"][primitive["attributes"]["POSITION"]]
            require(accessor["componentType"] == 5126 and accessor["type"] == "VEC3" and "sparse" not in accessor, "Unsupported GLB position encoding")
            view = document["bufferViews"][accessor["bufferView"]]
            require(view.get("buffer", 0) == 0, "External GLB buffer forbidden")
            start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
            stride = view.get("byteStride", 12)
            positions.extend(struct.unpack_from("<fff", binary, start + i * stride) for i in range(accessor["count"]))
        meshes.append(positions)
    points = []
    visited = set()

    def visit(index, parent):
        require(index not in visited, "Cyclic or shared GLB node")
        visited.add(index)
        node = document["nodes"][index]
        transform = _multiply(parent, _node_matrix(node))
        if "mesh" in node:
            for position in meshes[node["mesh"]]:
                p = (*position, 1)
                points.append(tuple(sum(transform[i][j] * p[j] for j in range(4)) for i in range(3)))
        for child in node.get("children", []):
            visit(child, transform)

    for node in document["scenes"][document.get("scene", 0)]["nodes"]:
        visit(node, _identity())
    require(bool(points) and all(math.isfinite(v) for p in points for v in p), "Empty/nonfinite GLB")
    return points


def bounds(points):
    return {"min": [min(p[i] for p in points) for i in range(3)], "max": [max(p[i] for p in points) for i in range(3)]}


def glb_orientation(path: Path, expected_volume_mm3):
    """Check actual indexed triangles and normals, including exporter handedness."""
    raw = path.read_bytes()
    size = struct.unpack_from("<I", raw, 12)[0]
    document = json.loads(raw[20:20 + size])
    binary = raw[28 + size:]

    def accessor_values(index, vector):
        accessor = document["accessors"][index]
        formats = {5121: ("B", 1), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
        require(accessor["componentType"] in formats and "sparse" not in accessor, "Unsupported indexed GLB encoding")
        code, component_size = formats[accessor["componentType"]]
        require(accessor["type"] == ("VEC3" if vector else "SCALAR"), "Invalid indexed GLB accessor")
        if vector:
            require(accessor["componentType"] == 5126, "Nonfloat GLB normal/position")
        count = 3 if vector else 1
        view = document["bufferViews"][accessor["bufferView"]]
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        stride = view.get("byteStride", component_size * count)
        return [struct.unpack_from("<" + code * count, binary, offset + i * stride) for i in range(accessor["count"])]

    def cross(a, b):
        return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])

    def dot(a, b):
        return sum(a[i] * b[i] for i in range(3))

    signed_volume = 0.0
    triangles = 0
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            require(primitive.get("mode", 4) == 4 and "indices" in primitive and "NORMAL" in primitive["attributes"], "GLB triangles/normals missing")
            points = accessor_values(primitive["attributes"]["POSITION"], True)
            normals = accessor_values(primitive["attributes"]["NORMAL"], True)
            indices = [value[0] for value in accessor_values(primitive["indices"], False)]
            require(len(indices) % 3 == 0 and len(normals) == len(points), "GLB triangle/normal cardinality mismatch")
            for offset in range(0, len(indices), 3):
                ia, ib, ic = indices[offset:offset + 3]
                a, b, c = points[ia], points[ib], points[ic]
                normal = cross(tuple(b[i] - a[i] for i in range(3)), tuple(c[i] - a[i] for i in range(3)))
                magnitude = math.sqrt(dot(normal, normal))
                if magnitude <= 1e-18:
                    continue
                require(all(math.isfinite(v) for index in (ia, ib, ic) for v in normals[index]), "Nonfinite GLB normal")
                require(all(dot(normal, normals[index]) >= -magnitude * 1e-6 for index in (ia, ib, ic)), "GLB triangle winding contradicts normals")
                signed_volume += dot(a, cross(b, c)) / 6
                triangles += 1
    expected_m3 = expected_volume_mm3 * 1e-9
    require(triangles > 0 and signed_volume > 0 and abs(signed_volume - expected_m3) <= expected_m3 * 1e-5, "GLB signed mesh volume/handedness mismatch")
    return {"triangle_count": triangles, "signed_volume_m3": signed_volume, "normals": "passed", "winding": "passed"}


def _aabb(shape):
    box = shape.bounding_box()
    return {"min": list(box.min), "max": list(box.max)}


def _expected_aabb(aabb):
    return {key: [float(aabb[key][axis]) for axis in "xyz"] if isinstance(aabb[key], dict) else [float(v) for v in aabb[key]] for key in ("min", "max")}


def measure_geometry(out_dir: Path, resolved: dict):
    from cadgen import read_scene, read_step

    cad_paths=['assembly.step',*[f"parts/{d['definition_id']}.{suffix}" for d in resolved['part_definitions'] for suffix in ('step','glb')]]
    inspected_bytes={relative:sha256_file(out_dir/relative) for relative in cad_paths}
    definition_reports = []
    geometry = {}
    for definition in resolved["part_definitions"]:
        definition_id = definition["definition_id"]
        shape = read_step(out_dir / "parts" / f"{definition_id}.step")
        expected = [float(definition["finished_mm"][key]) for key in ("length_mm", "width_mm", "thickness_mm")]
        require(shape.is_valid and len(shape.solids()) == 1 and shape.volume > 0, "Invalid saved part solid")
        near(tuple(shape.bounding_box().size), expected)
        near(tuple(shape.bounding_box().center()), (0, 0, 0))
        expected_volume = math.prod(expected)
        require(abs(shape.volume - expected_volume) <= max(0.001, expected_volume * 1e-10), "Saved part volume mismatch")
        mesh = glb_positions(out_dir / "parts" / f"{definition_id}.glb")
        orientation = glb_orientation(out_dir / "parts" / f"{definition_id}.glb", expected_volume)
        mesh_bounds = bounds(mesh)
        near([mesh_bounds["max"][i] - mesh_bounds["min"][i] for i in range(3)], [expected[0] * .001, expected[2] * .001, expected[1] * .001], GLB_TOLERANCE_M)
        near([(mesh_bounds["max"][i] + mesh_bounds["min"][i]) / 2 for i in range(3)], (0, 0, 0), GLB_TOLERANCE_M)
        geometry[definition_id] = mesh
        definition_reports.append({"definition_id": definition_id, "solid_count": 1, "size_mm": list(shape.bounding_box().size), "center_mm": list(shape.bounding_box().center()), "volume_mm3": shape.volume, "glb_aabb_m": mesh_bounds, "glb_vertex_count": len(mesh), "glb_orientation": orientation})
    assembly = read_step(out_dir / "assembly.step")
    require(assembly.is_valid and len(assembly.solids()) == len(resolved["part_instances"]), "Assembly solid count mismatch")
    expected_aabb = _expected_aabb(resolved["world_aabb_mm"])
    assembly_bounds = _aabb(assembly)
    near(assembly_bounds["min"], expected_aabb["min"])
    near(assembly_bounds["max"], expected_aabb["max"])
    expected_total = float(resolved["total_part_volume_mm3"])
    require(abs(assembly.volume - expected_total) <= max(.001, expected_total * 1e-10), "Assembly volume mismatch")
    scene = read_scene(out_dir / "assembly.step")
    occurrences = list(scene.leaves())
    instances = {item["instance_id"]: item for item in resolved["part_instances"]}
    require(len(occurrences) == len(instances) and {o.label for o in occurrences} == set(instances), "Saved occurrence labels do not exactly match instance IDs")
    shapes, mapping, reports = {}, [], []
    for occurrence in occurrences:
        instance = instances[occurrence.label]
        require(isinstance(occurrence.ref, str) and bool(re.fullmatch(r"#o[0-9]+(?:\.[0-9]+)*", occurrence.ref)), "Unexpected pinned public selector representation")
        selected = scene.resolve(occurrence.ref)
        shape = selected.shape()
        require(shape.is_valid and len(shape.solids()) == 1 and shape.volume > 0, "Invalid saved occurrence")
        transform = shape.location.wrapped.Transformation()
        saved_rotation = [[transform.Value(i + 1, j + 1) for j in range(3)] for i in range(3)]
        saved_center = [transform.Value(i + 1, 4) for i in range(3)]
        for actual, expected in zip(saved_rotation, instance["rotation_cad_rows"]):
            near(actual, expected, 1e-10)
        near(saved_center, [float(instance["center_mm"][axis]) for axis in "xyz"])
        near(tuple(shape.bounding_box().center()), [float(instance["center_mm"][axis]) for axis in "xyz"])
        measured_bounds = _aabb(shape)
        expected_bounds = _expected_aabb(instance["world_aabb_mm"])
        near(measured_bounds["min"], expected_bounds["min"])
        near(measured_bounds["max"], expected_bounds["max"])
        # Instantiate actual exported vertices using the conjugated manifest rotation.
        rotation = instance["viewer_rotation_rows"]
        center = [float(instance["viewer_center_m"][axis]) for axis in "xyz"]
        mesh = geometry[instance["definition_id"]]
        world_mesh = [tuple(sum(rotation[i][j] * p[j] for j in range(3)) + center[i] for i in range(3)) for p in mesh]
        mesh_bounds = bounds(world_mesh)
        corners = [(.001*x, .001*z, -.001*y) for x, y, z in itertools.product(*[(expected_bounds["min"][i], expected_bounds["max"][i]) for i in range(3)])]
        expected_mesh = bounds(corners)
        near(mesh_bounds["min"], expected_mesh["min"], GLB_TOLERANCE_M)
        near(mesh_bounds["max"], expected_mesh["max"], GLB_TOLERANCE_M)
        shapes[occurrence.label] = shape
        mapping.append({"instance_id": occurrence.label, "occurrence_label": occurrence.label, "selector": occurrence.ref})
        reports.append({"instance_id": occurrence.label, "selector": occurrence.ref, "center_mm": list(shape.bounding_box().center()), "saved_rotation_cad_rows": saved_rotation, "saved_translation_mm": saved_center, "world_aabb_mm": measured_bounds, "volume_mm3": shape.volume, "world_glb_aabb_m": mesh_bounds})
    permitted = {tuple(sorted(pair)) for pair in resolved["expected_contact_pairs"]}
    pair_reports = []
    actual_contacts = set()
    tolerated_overlap_volume = 0.0
    for first, second in itertools.combinations(sorted(shapes), 2):
        left, right = shapes[first], shapes[second]
        intersection = left.intersect(right)
        overlap_volume = sum(item.volume for item in intersection) if intersection else 0.0
        distance = left.distance_to(right)
        require(math.isfinite(distance) and math.isfinite(overlap_volume), "Nonfinite native pair inspection")
        touching = distance <= POSITION_TOLERANCE_MM
        pair = (first, second)
        overlap_tolerance = 0.000001
        if pair in permitted and overlap_volume > overlap_tolerance:
            # Rounding a half-micrometer center once can create a numerical contact
            # band. Permit it only at an explicitly declared butt interface and
            # only within the handoff's linear resolved-position tolerance.
            boxes = (left.bounding_box(), right.bounding_box())
            penetration = [min(tuple(boxes[0].max)[i], tuple(boxes[1].max)[i]) - max(tuple(boxes[0].min)[i], tuple(boxes[1].min)[i]) for i in range(3)]
            narrowest = min(range(3), key=lambda i: penetration[i])
            require(0 < penetration[narrowest] <= POSITION_TOLERANCE_MM, f"Unexpected solid overlap: {first}/{second}")
            face_envelope_area = math.prod(max(0, penetration[i]) for i in range(3) if i != narrowest)
            overlap_tolerance = max(overlap_tolerance, face_envelope_area * POSITION_TOLERANCE_MM)
        require(overlap_volume <= overlap_tolerance, f"Unexpected solid overlap: {first}/{second}")
        tolerated_overlap_volume += overlap_volume
        if touching:
            require(pair in permitted, f"Unexpected contact: {first}/{second}")
            common = left.intersect(right, include_touched=True)
            face_area = sum(item.area for item in common) if common else 0.0
            require(face_area > 0, f"Required contact is not a shared face: {first}/{second}")
            actual_contacts.add(pair)
        else:
            face_area = 0.0
        pair_reports.append({"instance_ids": [first, second], "distance_mm": distance, "overlap_volume_mm3": overlap_volume, "overlap_tolerance_mm3": overlap_tolerance, "contact_face_area_mm2": face_area, "permitted_contact": pair in permitted})
    require(actual_contacts == permitted, "Missing required butt-face contact")
    # Measure empty openings between saved opposing faces. This is an inspection
    # of the outputs, independent of the compiler's clear-height arithmetic.
    horizontal = sorted((shape for key, shape in shapes.items() if key in {"bottom", "top"} or key.startswith("shelf_")), key=lambda shape: shape.bounding_box().min.Z)
    require(len(horizontal) - 1 == len(resolved["openings"]), "Saved clear-opening cardinality mismatch")
    left_side = shapes["side_left"].bounding_box()
    right_side = shapes["side_right"].bounding_box()
    saved_clear_width = right_side.min.X - left_side.max.X
    saved_clear_depth = left_side.max.Y - left_side.min.Y
    opening_reports = []
    for index, (lower, upper) in enumerate(zip(horizontal, horizontal[1:])):
        z_min, z_max = lower.bounding_box().max.Z, upper.bounding_box().min.Z
        expected = resolved["openings"][index]
        near((z_min, z_max, z_max - z_min, saved_clear_width, saved_clear_depth),
             (expected["z_min_mm"], expected["z_max_mm"], expected["resolved_clear_height_mm"], expected["clear_width_mm"], expected["clear_depth_mm"]))
        require(z_max > z_min and saved_clear_width > 0 and saved_clear_depth > 0, "Nonpositive saved clear opening")
        opening_reports.append({"opening_index": index, "z_min_mm": z_min, "z_max_mm": z_max, "clear_height_mm": z_max - z_min, "clear_width_mm": saved_clear_width, "clear_depth_mm": saved_clear_depth})
    # An independent native union detects a coincident volume despite correct totals.
    values = list(shapes.values())
    union = values[0].fuse(*values[1:])
    require(union.is_valid and abs(union.volume - expected_total) <= max(.001, expected_total * 1e-10) + tolerated_overlap_volume, "Saved assembly union volume mismatch")
    require(inspected_bytes=={relative:sha256_file(out_dir/relative) for relative in cad_paths},'Native inspection saved CAD bytes changed while checking')
    return {
        "geometry": "passed", "position_tolerance_mm": str(POSITION_TOLERANCE_MM),
        "cad_artifact_sha256": inspected_bytes,
        "definitions": definition_reports, "instances": reports, "pair_checks": pair_reports, "openings": opening_reports,
        "assembly": {"solid_count": len(assembly.solids()), "world_aabb_mm": assembly_bounds, "part_volume_mm3": assembly.volume, "union_volume_mm3": union.volume, "numerical_contact_overlap_mm3": tolerated_overlap_volume},
    }, sorted(mapping, key=lambda item: item["instance_id"])
