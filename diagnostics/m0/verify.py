"""Verify setup probes, not the absent canonical project acceptance corpus."""
import argparse
import hashlib
import json
import math
import struct
import sys
from importlib.metadata import version
from pathlib import Path

from cadgen import read_scene, read_step


def mesh_positions(path):
    raw = path.read_bytes()
    assert struct.unpack_from('<III', raw) == (0x46546C67, 2, len(raw))
    size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + size])
    assert raw[16:20] == b'JSON'
    assert raw[24 + size:28 + size] == b'BIN\0'
    binary = raw[28 + size:]
    points = []
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            accessor = doc['accessors'][primitive['attributes']['POSITION']]
            view = doc['bufferViews'][accessor['bufferView']]
            assert accessor['componentType'] == 5126 and accessor['type'] == 'VEC3'
            start = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
            stride = view.get('byteStride', 12)
            points += [struct.unpack_from('<fff', binary, start + i * stride) for i in range(accessor['count'])]
    return points


def near(actual, expected, tolerance=0.0001):
    assert len(actual) == len(expected)
    assert all(abs(a - b) <= tolerance for a, b in zip(actual, expected)), (actual, expected)


def signed_mesh_volume(path):
    raw = path.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + size])
    binary = raw[28 + size:]
    def decode(index):
        accessor = doc['accessors'][index]
        view = doc['bufferViews'][accessor['bufferView']]
        fmt = {5121: 'B', 5123: 'H', 5125: 'I', 5126: 'f'}[accessor['componentType']]
        count = 3 if accessor['type'] == 'VEC3' else 1
        width = struct.calcsize('<' + fmt * count)
        stride = view.get('byteStride', width)
        start = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        return [struct.unpack_from('<' + fmt * count, binary, start + i * stride) for i in range(accessor['count'])]
    volume = 0.0
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            assert primitive.get('mode', 4) == 4
            points = decode(primitive['attributes']['POSITION'])
            indices = [i[0] for i in decode(primitive['indices'])]
            for start in range(0, len(indices), 3):
                a, b, c = [points[i] for i in indices[start:start + 3]]
                cross = (b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0])
                volume += sum(a[i]*cross[i] for i in range(3))/6
    return volume


def main(root):
    out = root / 'out'
    part = read_step(out / 'part.step')
    assert part.is_valid and len(part.solids()) == 1
    near(tuple(part.bounding_box().size), (726, 298.8, 18))
    assert abs(part.volume - 3904718.4) < 0.001
    points = mesh_positions(out / 'part.glb')
    bounds = [(min(p[i] for p in points), max(p[i] for p in points)) for i in range(3)]
    near([b - a for a, b in bounds], (0.726, 0.018, 0.2988), 0.0000001)
    mesh_volume = signed_mesh_volume(out / 'part.glb')
    assert mesh_volume > 0 and abs(mesh_volume - part.volume * 1e-9) < 1e-9

    asymmetric = read_step(out / 'asymmetric.step')
    assert asymmetric.is_valid and len(asymmetric.solids()) == 1
    near(tuple(asymmetric.bounding_box().size), (100, 60, 18))
    expected_volume = 108000 - math.pi * 4**2 * 18
    assert abs(asymmetric.volume - expected_volume) < 0.001
    circular = [edge for edge in asymmetric.edges() if edge.geom_type.name == 'CIRCLE']
    assert len(circular) == 2
    for edge in circular:
        center = tuple(edge.arc_center)
        near(center[:2], (20, 10))
        assert abs(abs(center[2]) - 9) < 0.0001
        assert abs(edge.radius - 4) < 0.0001
    feature_points = mesh_positions(out / 'asymmetric.glb')
    near([max(p[i] for p in feature_points) - min(p[i] for p in feature_points) for i in range(3)], (0.1, 0.018, 0.06), 0.0000001)
    ring = [p for p in feature_points if abs(math.hypot(p[0] - 0.02, p[2] + 0.01) - 0.004) < 0.0000001]
    assert len(ring) >= 12, 'Off-center hole was not mapped (x,z,-y) in meters'
    assert all(abs(abs(p[1]) - 0.009) < 0.0000001 for p in ring)

    scene = read_scene(out / 'two-instances.step')
    leaves = list(scene.leaves())
    assert sorted(o.label for o in leaves) == ['panel_left', 'panel_right']
    mapping = []
    for occurrence in leaves:
        saved = scene.resolve(occurrence.ref)
        assert saved.shape().is_valid
        center = tuple(saved.shape().bounding_box().center())
        expected_x = -60 if occurrence.label == 'panel_left' else 60
        near(center, (expected_x, 0, 0))
        mapping.append({'label': occurrence.label, 'selector': occurrence.ref, 'center_mm': center})

    report = {
        'scope': 'M0 runtime probes only; canonical project acceptance not run',
        'python': sys.version,
        'versions': {name: version(name) for name in ('cadgen', 'build123d', 'cadquery-ocp-novtk', 'playwright')},
        'panel_size_mm': tuple(part.bounding_box().size),
        'panel_volume_mm3': part.volume,
        'panel_glb_size_m': [b - a for a, b in bounds],
        'panel_glb_signed_volume_m3': mesh_volume,
        'asymmetric_volume_mm3': asymmetric.volume,
        'offcenter_hole_glb_vertex_count': len(ring),
        'occurrences': mapping,
        'files': [{'path': p.name, 'size': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir()) if p.is_file() and p.name != 'probe-evidence.json'],
    }
    (out / 'probe-evidence.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('probe_root', type=Path)
    main(parser.parse_args().probe_root)
