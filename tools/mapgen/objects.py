"""Object placements (obj0 ADTs) and WMO model geometry.

Usage: py -3.13 objects.py <data_dir> <map> roots|groups
  roots:  write <data_dir>/wmo-roots.txt, a TACTTool list of every WMO placed in extract/<map>/*_obj0.adt
  groups: write <data_dir>/wmo-groups.txt, the group files of every root already in extract/wmo/
"""
import glob
import math
import os
import struct
import sys

import numpy as np

from adt import iter_chunks
from wdt import TILE

ORIGIN = 32 * TILE  # placement coordinates are measured from the map's corner, not its center


def to_world(px, py, pz):
    """Placement space (Y up) to world (X north, Y west, Z up)."""
    return ORIGIN - pz, ORIGIN - px, py


def parse_obj0(data):
    """Return (m2s, wmos). Each entry: fid, uid, world pos, rotation (degrees), scale. WMOs also get world AABB extents.

    An object that crosses a tile border is listed in every tile it touches, with the same uid.
    """
    ch = {k: v for k, v in iter_chunks(data) if k in ("MDDF", "MODF")}
    m2s, wmos = [], []
    md = ch.get("MDDF", b"")
    for i in range(len(md) // 36):
        fid, uid, px, py, pz, rx, ry, rz, scale, flags = struct.unpack_from("<2I6f2H", md, i * 36)
        assert flags & 0x40, "M2 name is not a file ID"
        m2s.append({"fid": fid, "uid": uid, "pos": to_world(px, py, pz), "rot": (rx, ry, rz), "scale": scale / 1024})
    mo = ch.get("MODF", b"")
    for i in range(len(mo) // 64):
        fid, uid, px, py, pz, rx, ry, rz, *ext = struct.unpack_from("<2I12f", mo, i * 64)
        flags, _, _, scale = struct.unpack_from("<4H", mo, i * 64 + 56)
        assert flags & 0x8, "WMO name is not a file ID"
        lo, hi = to_world(*ext[:3]), to_world(*ext[3:])
        wmos.append({"fid": fid, "uid": uid, "pos": to_world(px, py, pz), "rot": (rx, ry, rz), "scale": scale / 1024 if flags & 0x4 else 1.0,
                     "extents": (min(lo[0], hi[0]), min(lo[1], hi[1]), max(lo[0], hi[0]), max(lo[1], hi[1]))})
    return m2s, wmos


def parse_wmo_root(data):
    ch = dict(iter_chunks(data))
    n_groups = struct.unpack_from("<I", ch["MOHD"], 4)[0]
    return list(struct.unpack_from(f"<{n_groups}I", ch["GFID"]))


def parse_wmo_group(data):
    """Return (vertices N x 3 in model space, triangles M x 3, group flags)."""
    mogp = dict(iter_chunks(data))["MOGP"]
    flags = struct.unpack_from("<I", mogp, 8)[0]
    sub = dict(iter_chunks(mogp[0x44:]))
    verts = np.frombuffer(sub.get("MOVT", b""), "<f4").reshape(-1, 3)
    tris = np.frombuffer(sub.get("MOVI", b""), "<u2").reshape(-1, 3)
    return verts, tris, flags


GROUP_EXTERIOR, GROUP_INTERIOR = 0x8, 0x2000
_groups = {}


def load_groups(wmo_dir, fid):
    """[(vertices, triangles, flags) or None per group] of a WMO model. Cached per model."""
    if fid not in _groups:
        out = []
        for i, g in enumerate(parse_wmo_root(open(os.path.join(wmo_dir, f"{fid}.wmo"), "rb").read())):
            path = os.path.join(wmo_dir, f"{fid}_{i:03d}.wmo")
            out.append(parse_wmo_group(open(path, "rb").read()) if g and os.path.exists(path) else None)
        _groups[fid] = out
    return _groups[fid]


def model_triangles(wmo_dir, fid, interior_only=False):
    """Triangles of a WMO model as an (M, 3, 2) array of model X, Y."""
    parts = [v[t][:, :, :2] for v, t, f in filter(None, load_groups(wmo_dir, fid))
             if len(t) and (f & GROUP_INTERIOR or not interior_only)]
    return np.concatenate(parts) if parts else np.zeros((0, 3, 2), np.float32)


def model_entrances(wmo_dir, fid):
    """Model X, Y of every doorway: portals that join an exterior group to an interior group.

    A model without such portals (an open den) gets one point at its bounding box center.
    """
    root = dict(iter_chunks(open(os.path.join(wmo_dir, f"{fid}.wmo"), "rb").read()))
    groups = load_groups(wmo_dir, fid)
    flags = [g[2] if g else 0 for g in groups]
    mopt, mopv, mopr = root.get("MOPT", b""), root.get("MOPV", b""), root.get("MOPR", b"")
    sides = {}
    for k in range(len(mopr) // 8):
        portal, group, _, _ = struct.unpack_from("<HHhH", mopr, k * 8)
        sides.setdefault(portal, set()).add(flags[group] & (GROUP_EXTERIOR | GROUP_INTERIOR))
    verts = np.frombuffer(mopv, "<f4").reshape(-1, 3)
    points = []
    for portal, kinds in sides.items():
        if GROUP_EXTERIOR in kinds and GROUP_INTERIOR in kinds:
            start, count = struct.unpack_from("<HH", mopt, portal * 20)
            points.append(verts[start:start + count, :2].mean(axis=0))
    return np.array(points) if points else bbox_corners(wmo_dir, fid).mean(axis=0, keepdims=True)


def place(xy, wmo):
    """Model X, Y (any leading shape, last axis 2) to world X, Y. Only the yaw is applied.

    Yaw is the stored Y rotation plus 180 degrees, with no mirroring. Matched against the stored
    extents of 233 untilted Durotar placements, worst error 0.1 yards (test_objects.py).
    Tilted placements (about 1 in 8, mostly tents and wrecks) are drawn untilted.
    """
    a = math.radians(wmo["rot"][1] + 180)
    s = wmo["scale"]
    x = xy[..., 0] * math.cos(a) - xy[..., 1] * math.sin(a)
    y = xy[..., 0] * math.sin(a) + xy[..., 1] * math.cos(a)
    return wmo["pos"][0] + x * s, wmo["pos"][1] + y * s


def bbox_corners(wmo_dir, fid):
    mohd = dict(iter_chunks(open(os.path.join(wmo_dir, f"{fid}.wmo"), "rb").read()))["MOHD"]
    b = struct.unpack_from("<6f", mohd, 36)
    return np.array([(x, y) for x in (b[0], b[3]) for y in (b[1], b[4])], np.float32)


def main(data_dir, map_name, step):
    tiles = glob.glob(os.path.join(data_dir, "extract", map_name, f"{map_name}_*_obj0.adt"))
    roots = sorted({w["fid"] for t in tiles for w in parse_obj0(open(t, "rb").read())[1]})
    wmo_dir = os.path.join(data_dir, "extract", "wmo")
    if step == "roots":
        lines = [f"{fid};{fid}.wmo" for fid in roots]
        out = os.path.join(data_dir, "wmo-roots.txt")
    else:
        lines = []
        for fid in roots:
            path = os.path.join(wmo_dir, f"{fid}.wmo")
            if os.path.exists(path):
                lines += [f"{g};{fid}_{i:03d}.wmo" for i, g in enumerate(parse_wmo_root(open(path, "rb").read())) if g]
        out = os.path.join(data_dir, "wmo-groups.txt")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{len(lines)} files -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
