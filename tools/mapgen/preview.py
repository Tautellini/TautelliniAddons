"""Render a styled preview PNG of one UI map from extracted root ADTs.

Usage: py -3.13 preview.py <uiMapID> <data_dir> <out.png> [clay|sand|slate]
data_dir holds db2/*.csv, listfile/community-listfile.csv, extract/<map>.wdt and extract/<map>/<map>_X_Y*.adt.
Classes so far: walkable, too steep, water, road, terrain hole (debug), other zone (faded).
"""
import csv
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

from adt import UNIT, parse_root, parse_tex0, tile_origin
from wdt import read_chunks, region_for, tile_range

WALK_LIMIT_DEG = 50  # shortcut: commonly cited limit, verify in game (spec open question 4)
WATER_MIN_DEPTH = 0.3
MIN_STEEP_CELLS = 25  # steep patches smaller than this (about 430 square yards) are noise for the player
SS = 4  # supersampled pixels per cell. Output is SS / 2 pixels per cell, anti-aliased by a 2x2 box filter.
MARGIN = 8  # cells kept around the map region so blurring has data at the edges
STYLES = {
    "sand": {
        "land": (233, 224, 207), "steep": (212, 196, 172), "steep_edge": (168, 148, 118),
        "water": (160, 210, 224), "water_deep": (92, 156, 188), "water_edge": (118, 172, 196),
        "shadow": (80, 60, 40), "outside": (214, 208, 198), "border": (140, 128, 112), "hole": (93, 64, 55),
        "road": (252, 248, 240), "road_edge": (178, 160, 132),
    },
    "clay": {
        "land": (228, 211, 186), "steep": (200, 168, 134), "steep_edge": (150, 112, 80),
        "water": (146, 202, 216), "water_deep": (72, 136, 170), "water_edge": (104, 160, 186),
        "shadow": (90, 50, 30), "outside": (212, 200, 184), "border": (130, 100, 76), "hole": (80, 46, 32),
        "road": (250, 242, 228), "road_edge": (176, 140, 104),
    },
    "slate": {
        "land": (226, 227, 221), "steep": (197, 200, 191), "steep_edge": (146, 152, 144),
        "water": (156, 200, 216), "water_deep": (82, 140, 176), "water_edge": (112, 160, 186),
        "shadow": (40, 50, 60), "outside": (208, 210, 206), "border": (120, 126, 122), "hole": (60, 64, 70),
        "road": (250, 250, 248), "road_edge": (150, 156, 150),
    },
}
SHADOW_OFFSET_PX = 3
ROAD_NAME = "road"  # ground textures whose file name contains this are roads and paths
MIN_ROAD_PX = 200  # painted road patches smaller than this (about 900 square yards) are decoration, not roads
ROAD_SPUR_PX = 8  # side branches up to this long (half cells) are thinning artifacts
ROAD_RADIUS_PX = 2.5  # drawn road half width in output pixels
ROAD_MIN_EXTENT_PX = 24  # road pieces spanning less than this (about 50 yards) are rings around props, not roads
DEEP_WATER_CELLS = 40  # distance from shore where water reaches its deepest color (about 170 yards)


def zone_of(db2_dir):
    parent = {int(r["ID"]): int(r["ParentAreaID"]) for r in csv.DictReader(open(os.path.join(db2_dir, "AreaTable.csv"), encoding="utf-8"))}

    def top(a):
        while parent.get(a, 0):
            a = parent[a]
        return a
    return top


def drop_small(mask, min_cells, diagonal=False):
    labels, n = ndimage.label(mask, np.ones((3, 3)) if diagonal else None)
    sizes = ndimage.sum(mask, labels, range(1, n + 1))
    return mask & np.isin(labels, 1 + np.flatnonzero(sizes >= min_cells))


def smooth(mask, sigma_cells, scale=SS):
    """Mask to a supersampled mask with rounded, smooth edges (blur, then threshold). scale = supersampled px per mask px."""
    f = ndimage.zoom(mask.astype(np.float32), scale, order=1, grid_mode=True, mode="nearest")
    return ndimage.gaussian_filter(f, sigma_cells * SS) > 0.5


def edge(hi, width_px):
    """Supersampled outline just outside a supersampled mask."""
    r = width_px * 2  # output pixels to supersampled pixels
    disk = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= r
    return ndimage.binary_dilation(hi, disk) & ~hi


def thin(mask):
    """Zhang-Suen thinning: reduce each shape to a one pixel wide center line."""
    m = mask.astype(np.uint8)
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            p = np.pad(m, 1)
            n = [p[:-2, 1:-1], p[:-2, 2:], p[1:-1, 2:], p[2:, 2:], p[2:, 1:-1], p[2:, :-2], p[1:-1, :-2], p[:-2, :-2]]  # N, NE, E, SE, S, SW, W, NW
            b = sum(n)
            a = sum((n[i] == 0) & (n[(i + 1) % 8] == 1) for i in range(8))
            if step == 0:
                c = (n[0] * n[2] * n[4] == 0) & (n[2] * n[4] * n[6] == 0)
            else:
                c = (n[0] * n[2] * n[6] == 0) & (n[0] * n[4] * n[6] == 0)
            rem = (m == 1) & (b >= 2) & (b <= 6) & (a == 1) & c
            if rem.any():
                m[rem] = 0
                changed = True
    return m.astype(bool)


def drop_short(skel, min_extent):
    """Drop 8-connected pieces whose bounding box is smaller than min_extent on both sides."""
    labels, _ = ndimage.label(skel, np.ones((3, 3)))
    keep = [i + 1 for i, s in enumerate(ndimage.find_objects(labels)) if max(s[0].stop - s[0].start, s[1].stop - s[1].start) >= min_extent]
    return np.isin(labels, keep)


def prune(skel, n):
    """Remove line ends n times, which deletes short side branches."""
    k = np.ones((3, 3))
    for _ in range(n):
        skel = skel & ~((ndimage.convolve(skel.astype(np.uint8), k, mode="constant") == 2) & skel)
    return skel


def coverage(hi):
    h, w = hi.shape
    return hi.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


def paint(img, hi, color, opacity=1.0):
    a = (coverage(hi) * opacity)[..., None]
    img *= 1 - a
    img += np.asarray(color, np.float32) * a


def road_texture_ids(listfile):
    ids = set()
    for line in open(listfile, encoding="utf-8"):
        if line.find("tileset/") != -1 and ROAD_NAME in line.rsplit("/", 1)[-1]:
            ids.add(int(line.split(";", 1)[0]))
    return ids


def build(ui_map_id, data_dir):
    db2_dir = os.path.join(data_dir, "db2")
    assign_csv = os.path.join(db2_dir, "UiMapAssignment.csv")
    min_x, min_y, max_x, max_y = region_for(assign_csv, ui_map_id)
    zone_area = next(int(r["AreaID"]) for r in csv.DictReader(open(assign_csv, encoding="utf-8"))
                     if r["UiMapID"] == str(ui_map_id) and r["OrderIndex"] == "0")
    map_id = next(r["MapID"] for r in csv.DictReader(open(assign_csv, encoding="utf-8")) if r["UiMapID"] == str(ui_map_id))
    prefix = next(r["Directory"] for r in csv.DictReader(open(os.path.join(db2_dir, "Map.csv"), encoding="utf-8")) if r["ID"] == map_id).lower()
    mphd = read_chunks(open(os.path.join(data_dir, "extract", prefix + ".wdt"), "rb").read())["MPHD"]
    big_alpha = bool(int.from_bytes(mphd[:4], "little") & 0x84)
    road_ids = road_texture_ids(os.path.join(data_dir, "listfile", "community-listfile.csv"))
    adt_dir = os.path.join(data_dir, "extract", prefix)
    tx, ty = tile_range(min_x, min_y, max_x, max_y)
    rows, cols = len(ty) * 128, len(tx) * 128
    heights = np.zeros((rows + 1, cols + 1), np.float32)
    holes = np.zeros((rows, cols), bool)
    liquid = np.full((rows, cols), np.nan, np.float32)
    have = np.zeros((rows, cols), bool)
    zone = np.zeros((rows, cols), np.int32)
    road = np.zeros((rows * 2, cols * 2), np.float32)  # half-cell resolution
    top = zone_of(db2_dir)

    for j, y in enumerate(ty):
        for i, x in enumerate(tx):
            path = os.path.join(adt_dir, f"{prefix}_{x}_{y}.adt")
            if not os.path.exists(path):
                continue  # no ADT means open ocean
            t = parse_root(open(path, "rb").read(), x, y)
            r, c = j * 128, i * 128
            heights[r:r + 129, c:c + 129] = t["heights"]
            holes[r:r + 128, c:c + 128] = t["holes"]
            liquid[r:r + 128, c:c + 128] = t["liquid"]
            have[r:r + 128, c:c + 128] = True
            zone[r:r + 128, c:c + 128] = np.kron(np.vectorize(top)(t["area"]), np.ones((8, 8), np.int32))
            tex0 = path[:-4] + "_tex0.adt"
            if os.path.exists(tex0):
                road[2 * r:2 * r + 256, 2 * c:2 * c + 256] = parse_tex0(open(tex0, "rb").read(), road_ids, big_alpha)

    h00, h01, h10, h11 = heights[:-1, :-1], heights[:-1, 1:], heights[1:, :-1], heights[1:, 1:]
    gx = ((h01 - h00) + (h11 - h10)) / (2 * UNIT)
    gy = ((h10 - h00) + (h11 - h01)) / (2 * UNIT)
    steep = np.degrees(np.arctan(np.hypot(gx, gy))) > WALK_LIMIT_DEG
    steep = ndimage.binary_closing(steep, np.ones((3, 3)))  # merge broken cliff rims into one band
    steep = drop_small(steep, MIN_STEEP_CELLS)
    steep |= ~drop_small(~steep, MIN_STEEP_CELLS)  # tiny flat spots inside cliffs are noise too
    ground = (h00 + h01 + h10 + h11) / 4
    water = ~have | (np.isfinite(liquid) & (liquid > ground + WATER_MIN_DEPTH))
    in_zone = have & (zone == zone_area)

    # Crop to the map region plus a margin, in cells.
    ox, oy = tile_origin(tx.start, ty.start)
    r0, r1 = math.floor((ox - max_x) / UNIT), math.ceil((ox - min_x) / UNIT)
    c0, c1 = math.floor((oy - max_y) / UNIT), math.ceil((oy - min_y) / UNIT)
    pad = lambda a, v: np.pad(a, MARGIN, constant_values=v)[r0:r1 + 2 * MARGIN, c0:c1 + 2 * MARGIN]
    steep, water, holes, in_zone = pad(steep, False), pad(water, True), pad(holes, False), pad(in_zone, False)
    road = ndimage.gaussian_filter(np.pad(road, 2 * MARGIN)[2 * r0:2 * (r1 + 2 * MARGIN), 2 * c0:2 * (c1 + 2 * MARGIN)], 1.0) > 0.5
    road = drop_small(road & ~np.kron(water, np.ones((2, 2), bool)), MIN_ROAD_PX)
    road = drop_short(prune(thin(road), ROAD_SPUR_PX), ROAD_MIN_EXTENT_PX)  # center lines

    return {"steep": steep & ~water, "water": water, "holes": holes, "in_zone": in_zone, "road": road}


def render(masks, style):
    s = STYLES[style]
    steep_hi, water_hi, zone_hi = smooth(masks["steep"], 0.8), smooth(masks["water"], 0.8), smooth(masks["in_zone"], 3.0)
    depth = np.clip(ndimage.distance_transform_edt(masks["water"]) / DEEP_WATER_CELLS, 0, 1)
    depth = ndimage.zoom(depth.astype(np.float32), SS // 2, order=1, grid_mode=True, mode="nearest")[..., None]
    water_color = np.array(s["water"], np.float32) * (1 - depth) + np.array(s["water_deep"], np.float32) * depth
    k = SHADOW_OFFSET_PX * 2
    shadow = ndimage.gaussian_filter(np.pad(steep_hi, ((k, 0), (k, 0)))[:-k, :-k].astype(np.float32), k)  # soft, offset down-right

    img = np.empty((steep_hi.shape[0] // 2, steep_hi.shape[1] // 2, 3), np.float32)
    img[:] = s["land"]
    paint(img, shadow * ~steep_hi, s["shadow"], 0.3)
    paint(img, steep_hi, s["steep"])
    paint(img, edge(steep_hi, 1.0) & ~water_hi, s["steep_edge"])
    r = ROAD_RADIUS_PX * 2
    disk = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= r
    road_hi = ndimage.binary_dilation(np.kron(masks["road"], np.ones((SS // 2, SS // 2), bool)), disk)
    paint(img, edge(road_hi, 0.75) & ~water_hi, s["road_edge"])
    paint(img, road_hi, s["road"])
    paint(img, ~zone_hi & ~water_hi, s["outside"], 0.6)
    paint(img, water_hi, water_color)
    paint(img, edge(water_hi, 1.0), s["water_edge"])
    paint(img, edge(zone_hi, 1.0) & ~water_hi, s["border"], 0.9)
    paint(img, smooth(masks["holes"], 0.3), s["hole"])
    m = MARGIN * SS // 2
    return Image.fromarray(img[m:-m, m:-m].round().astype(np.uint8))


def main(ui_map_id, data_dir, out_png, style="clay"):
    img = render(build(ui_map_id, data_dir), style)
    img.save(out_png)
    print(f"{out_png}: {img.width}x{img.height} px at {UNIT * 2 / SS:.2f} yd/px, style {style}")




if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
