"""Capital cities drawn from their own building models: every floor a player can reach, seen from above.

Usage: py -3.13 city.py <uiMapID> <data_dir> <out.png>   (a preview with district names)
export.py calls build() and render() for the maps in CITIES.

The up-facing triangles of every building model in the city are rasterized at CELL yards. A cell keeps all of its
floor layers, not only the top one, because roofs and beams would hide the floors below. Layers of neighboring
cells join when the height step is small. The biggest joined region is the city floor. Other big regions count
when they meet the outdoor ground at their own height, which brings in the Ruins of Lordaeron (the elevators down
to Undercity are not part of the model). Roofs and wall tops drop out on their own, since no step reaches them.
"""
import csv
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

import preview
from adt import UNIT, iter_chunks, parse_root, tile_origin
from objects import parse_obj0, parse_wmo_root, place
from preview import CAVE_PATH, CAVE_WORDS, STYLES, edge, liquid_kinds, paint, scan_listfile, smooth
from wdt import region_for, tile_range

# uiMapID: True when the outdoor ground is part of the city (Stormwind, Orgrimmar), False for underground cities.
CITIES = {1453: True, 1454: True, 1455: False, 1458: False}
CELL = 0.5  # yards per raster cell
FLOOR_NZ = 0.64  # about 50 degrees, the walk limit
SAME_LAYER = 0.5  # floor samples of one cell closer than this are one layer (overlapping triangles)
STEP_UP = 1.5  # yards a player steps up between neighboring cells (stairs, ramps)
MIN_REGION_YD2 = 2000  # smaller loose regions are roofs and ledges
MIN_TOUCH_YD2 = 10  # floor area at outdoor ground height that makes a region reachable from outside
LIQUID_ON_FLOOR = 0.5  # liquid shows where its surface is at most this far below the shown floor
POOL_DEPTH = 10  # liquid over no reachable floor still shows above any floor this close below it (lava pits)
LEDGE_STEP = 2.0  # height jump between neighbors drawn as a ledge line
MIN_LEDGE_YARDS = 3  # shorter ledges are props
MIN_OBSTACLE_YD2 = 6  # blocked spots smaller than this (crates, small props) are left out
BODY_YARDS = 2.5  # model geometry this close above the outdoor ground blocks it, higher geometry (arches) does not
BURIED_YARDS = 1.0  # geometry this far below the ground is a buried foundation
SLOPE_SMOOTH_YARDS = 1.5
LIQUIDS = ("water", "lava", "slime", "tar")  # liquid codes 1..4 in the rasters, 0 is none
SKIP_NAMES = {"", "Canals", "Sewers"}  # model parts named after plumbing, not districts
DISTRICT_YD2 = 4000  # named parts at least this big are districts (Essential), smaller ones are rooms such as SI:7


def city_placements(ui_map_id, data_dir):
    """(map prefix, map ID, WMO placements in the map region). Caves and mines are left out, they belong to the zone."""
    db2 = os.path.join(data_dir, "db2")
    assign = os.path.join(db2, "UiMapAssignment.csv")
    map_id = next(r["MapID"] for r in csv.DictReader(open(assign, encoding="utf-8")) if r["UiMapID"] == str(ui_map_id))
    prefix = next(r["Directory"] for r in csv.DictReader(open(os.path.join(db2, "Map.csv"), encoding="utf-8")) if r["ID"] == map_id).lower()
    tx, ty = tile_range(*region_for(assign, ui_map_id))
    wmos = {}
    for y in ty:
        for x in tx:
            path = os.path.join(data_dir, "extract", prefix, f"{prefix}_{x}_{y}_obj0.adt")
            if os.path.exists(path):
                wmos.update((w["uid"], w) for w in parse_obj0(open(path, "rb").read())[1])
    _, names = scan_listfile(os.path.join(data_dir, "listfile", "community-listfile.csv"), {w["fid"] for w in wmos.values()})
    cave = lambda n: CAVE_PATH in n and any(k in n for k in CAVE_WORDS)
    city_model = lambda w: max(w["extents"][2] - w["extents"][0], w["extents"][3] - w["extents"][1]) > preview.BUILDING_MAX_YARDS
    # Underground cities show only their own model. Houses on the surface above them would be islands in the rock.
    return prefix, int(map_id), [w for w in wmos.values() if not cave(names.get(w["fid"], "")) and (CITIES[ui_map_id] or city_model(w))]


def surfaces(wmo_dir, placements, kind_of):
    """Every triangle of the models in world space, plus their liquid tiles.

    Returns xy (M, 3, 2), z (M, 3), a code (M,) that is 0 for floors, -1 for walls and other steep faces and a
    liquid code above 0, and a name key (M,) into the returned list of (WMO ID, name set, group ID).
    """
    xy, zs, liq, key, keys = [], [], [], [], []
    for w in placements:
        root_path = os.path.join(wmo_dir, f"{w['fid']}.wmo")
        if not os.path.exists(root_path):
            continue
        root = open(root_path, "rb").read()
        wmo_id = struct.unpack_from("<I", dict(iter_chunks(root))["MOHD"], 32)[0]
        tris, z, codes, ks = [], [], [], []
        for i, g in enumerate(parse_wmo_root(root)):
            path = os.path.join(wmo_dir, f"{w['fid']}_{i:03d}.wmo")
            if not (g and os.path.exists(path)):
                continue
            mogp = dict(iter_chunks(open(path, "rb").read()))["MOGP"]
            sub = {}
            for k, v in iter_chunks(mogp[0x44:]):
                sub.setdefault(k, v)
            group_liquid, group_id = struct.unpack_from("<2I", mogp, 0x34)
            k = len(keys)
            keys.append((wmo_id, w["name_set"], group_id))
            v = np.frombuffer(sub.get("MOVT", b""), "<f4").reshape(-1, 3)
            t = v[np.frombuffer(sub.get("MOVI", b""), "<u2").reshape(-1, 3)]
            n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
            up = n[:, 2] / np.maximum(np.linalg.norm(n, axis=1), 1e-9) > FLOOR_NZ
            tris.append(t[..., :2]); z.append(t[..., 2]); codes.append(np.where(up, 0, -1).astype(np.int8)); ks.append(np.full(len(t), k))
            m = sub.get("MLIQ")
            if m:
                # Header: vertex and tile counts, corner, material. Then 8-byte vertices (height last), then tile flags.
                xv, yv, xt, yt = struct.unpack_from("<4i", m, 0)
                bx, by, _ = struct.unpack_from("<3f", m, 16)
                h = np.frombuffer(m, "<f4", xv * yv * 2, 30).reshape(yv, xv, 2)[..., 1]
                tiles = np.frombuffer(m, "u1", xt * yt, 30 + xv * yv * 8).reshape(yt, xt)
                code = 1 + LIQUIDS.index(kind_of.get(group_liquid, "water"))  # MOHD flag 0x4: a LiquidType ID
                for j, c in zip(*np.nonzero((tiles & 0x0F) != 0x0F)):  # 0x0F marks a tile without liquid
                    x0, y0 = bx + c * UNIT, by + j * UNIT
                    q = np.array([[x0, y0], [x0 + UNIT, y0], [x0 + UNIT, y0 + UNIT], [x0, y0 + UNIT]], np.float32)
                    tris.append(np.stack([q[[0, 1, 2]], q[[0, 2, 3]]])); z.append(np.full((2, 3), h[j:j + 2, c:c + 2].mean(), np.float32))
                    codes.append(np.full(2, code, np.int8)); ks.append(np.full(2, k))
        if tris:
            wx, wy = place(np.concatenate(tris), w)
            xy.append(np.stack([wx, wy], -1)); zs.append(np.concatenate(z) + w["pos"][2])
            liq.append(np.concatenate(codes)); key.append(np.concatenate(ks))
    return np.concatenate(xy), np.concatenate(zs), np.concatenate(liq), np.concatenate(key), keys


def samples(rc, zv):
    """Every cell center inside every triangle: row, col, z (from the triangle's plane) and triangle index."""
    out = []
    lo, hi = np.floor(rc.min(1)).astype(int), np.ceil(rc.max(1)).astype(int)
    size = np.maximum(hi - lo, 1).max(1)
    bucket = 2 ** np.ceil(np.log2(size)).astype(int)  # triangles of similar size share one grid shape
    for b in np.unique(bucket):
        sel = np.nonzero(bucket == b)[0]
        for part in np.array_split(sel, len(sel) * b * b // 4_000_000 + 1):  # bounded memory per step
            dr, dc = np.mgrid[0:b, 0:b]
            r, c = lo[part, 0, None, None] + dr, lo[part, 1, None, None] + dc
            pr, pc = r + 0.5, c + 0.5
            v0, v1, v2 = (rc[part, i, :, None, None] for i in range(3))
            den = (v1[:, 0] - v0[:, 0]) * (v2[:, 1] - v0[:, 1]) - (v2[:, 0] - v0[:, 0]) * (v1[:, 1] - v0[:, 1])
            den = np.where(np.abs(den) < 1e-12, 1e-12, den)
            a = ((v1[:, 0] - pr) * (v2[:, 1] - pc) - (v2[:, 0] - pr) * (v1[:, 1] - pc)) / den
            b2 = ((v2[:, 0] - pr) * (v0[:, 1] - pc) - (v0[:, 0] - pr) * (v2[:, 1] - pc)) / den
            c2 = 1 - a - b2
            k = np.nonzero((a >= -1e-6) & (b2 >= -1e-6) & (c2 >= -1e-6))
            z = a * zv[part, 0, None, None] + b2 * zv[part, 1, None, None] + c2 * zv[part, 2, None, None]
            out.append((r[k], c[k], z[k], part[k[0]]))
    return [np.concatenate(x) for x in zip(*out)]


def terrain(data_dir, prefix, x1, y1, H, W):
    """Outdoor ground per raster cell: height (NaN without terrain), hole, slope too steep, liquid surface, liquid type, area."""
    X, Y = x1 - (np.arange(H) + 0.5) * CELL, y1 - (np.arange(W) + 0.5) * CELL
    tx, ty = tile_range(X.min(), Y.min(), X.max(), Y.max())
    rows, cols = len(ty) * 128, len(tx) * 128
    heights = np.full((rows + 1, cols + 1), np.nan, np.float32)
    holes = np.ones((rows, cols), bool)
    liquid = np.full((rows, cols), np.nan, np.float32)
    liquid_type = np.zeros((rows, cols), np.uint16)
    area = np.zeros((rows, cols), np.int32)
    for j, y in enumerate(ty):
        for i, x in enumerate(tx):
            path = os.path.join(data_dir, "extract", prefix, f"{prefix}_{x}_{y}.adt")
            if os.path.exists(path):
                t = parse_root(open(path, "rb").read(), x, y)
                r, c = j * 128, i * 128
                heights[r:r + 129, c:c + 129] = t["heights"]
                holes[r:r + 128, c:c + 128] = t["holes"]
                liquid[r:r + 128, c:c + 128] = t["liquid"]
                liquid_type[r:r + 128, c:c + 128] = t["liquid_type"]
                area[r:r + 128, c:c + 128] = np.kron(t["area"], np.ones((8, 8), np.int32))
    ox, oy = tile_origin(tx.start, ty.start)
    fr, fc = (ox - X) / UNIT, (oy - Y) / UNIT  # fractional terrain cell of each raster cell center
    ground = ndimage.map_coordinates(heights, np.meshgrid(fr, fc, indexing="ij"), order=1, mode="nearest")
    # Slope of the slightly smoothed ground, so cliff outlines follow the terrain, not its 4-yard grid.
    gr, gc = np.gradient(ndimage.gaussian_filter(np.nan_to_num(ground), SLOPE_SMOOTH_YARDS / CELL), CELL)
    steep = np.degrees(np.arctan(np.hypot(gr, gc))) > preview.WALK_LIMIT_DEG
    ri, ci = np.clip(fr.astype(int), 0, rows - 1), np.clip(fc.astype(int), 0, cols - 1)
    pick = lambda a: a[np.ix_(ri, ci)]
    return {"height": ground, "hole": pick(holes), "steep": steep, "liquid": pick(liquid), "liquid_type": pick(liquid_type)}


def ground_cover(rc, zv, ground, H, W):
    """Cells where model geometry stands on the outdoor ground: walls, floors and anything within body height of it.

    Arches, bridges and roofs high above a street leave the street open. Foundations buried in the ground are ignored.
    """
    ri = np.clip(rc[..., 0].mean(1).astype(int), 0, H - 1)
    ci = np.clip(rc[..., 1].mean(1).astype(int), 0, W - 1)
    g = ground[ri, ci]  # the ground under each triangle's center
    ok = (zv.min(1) < g + BODY_YARDS) & (zv.max(1) > g - BURIED_YARDS)
    img = Image.new("1", (W, H))
    draw = ImageDraw.Draw(img)
    for t in rc[ok]:  # the outline keeps walls, which are lines seen from above
        draw.polygon([(t[0, 1], t[0, 0]), (t[1, 1], t[1, 0]), (t[2, 1], t[2, 0])], fill=1, outline=1)
    return np.array(img, bool)


def layers(cell, z):
    """Sort floor samples by cell and height and merge near-equal ones. Returns the kept indices."""
    o = np.lexsort((z, cell))
    new = np.ones(len(o), bool)
    new[1:] = (cell[o][1:] != cell[o][:-1]) | (np.diff(z[o]) > SAME_LAYER)
    return o[new]


def regions(fc, fz, W, ground, model):
    """Label floor layers by joined region. Returns (labels, sizes, kept region IDs, main region ID).

    model marks layers that belong to a building model. Regions of outdoor ground alone (mountain tops) are not kept.
    """
    n = len(fc)
    sort_key = fc * 1e4 + (fz + 2000)  # layers are sorted by cell, then height; heights stay within +-2000
    src, dst = [], []
    for d in (1, W):  # right and down neighbors
        j = np.minimum(np.searchsorted(sort_key, (fc + d) * 1e4 + (fz + 2000 - STEP_UP)), n - 1)
        ok = (fc[j] == fc + d) & (np.abs(fz[j] - fz) <= STEP_UP) & ((d == W) | (fc % W != W - 1))
        src.append(np.nonzero(ok)[0]); dst.append(j[ok])
    src, dst = np.concatenate(src), np.concatenate(dst)
    m, lab = connected_components(coo_matrix((np.ones(len(src), np.int8), (src, dst)), shape=(n, n)), directed=False)
    sizes = np.bincount(lab, minlength=m)
    order = np.argsort(sizes)[::-1]
    touches = np.bincount(lab[model & (np.abs(fz - ground[fc]) < STEP_UP)], minlength=m)  # NaN ground compares False
    big = lambda k: sizes[k] * CELL ** 2 >= MIN_REGION_YD2 and touches[k] * CELL ** 2 >= MIN_TOUCH_YD2
    return lab, sizes, [order[0]] + [k for k in order[1:50] if big(k)], order[0]


def build(ui_map_id, data_dir):
    db2 = os.path.join(data_dir, "db2")
    assign = os.path.join(db2, "UiMapAssignment.csv")
    x0, y0, x1, y1 = region_for(assign, ui_map_id)
    H, W = round((x1 - x0) / CELL), round((y1 - y0) / CELL)
    prefix, map_id, placements = city_placements(ui_map_id, data_dir)
    kind_of = liquid_kinds(db2)
    xy, zv, liq, key, keys = surfaces(os.path.join(data_dir, "extract", "wmo"), placements, kind_of)
    rc = np.stack([(x1 - xy[..., 0]) / CELL, (y1 - xy[..., 1]) / CELL], -1)
    near = (rc[..., 0].max(1) >= 0) & (rc[..., 0].min(1) < H) & (rc[..., 1].max(1) >= 0) & (rc[..., 1].min(1) < W)
    rc, zv, liq, key = rc[near], zv[near], liq[near], key[near]
    flat = liq >= 0
    r, c, z, tri = samples(rc[flat], zv[flat])
    tri = np.nonzero(flat)[0][tri]
    inside = (r >= 0) & (r < H) & (c >= 0) & (c < W)
    cell, z, code, grp = (r * W + c)[inside], z[inside], liq[tri][inside], key[tri][inside]
    ground = terrain(data_dir, prefix, x1, y1, H, W)
    height = ground["height"].ravel()

    floor = code == 0
    fc, fz, fg = cell[floor], z[floor], grp[floor]
    outdoor = CITIES[ui_map_id]
    if outdoor:
        # The outdoor ground is a floor too, wherever no model stands on it.
        covered = ground_cover(rc[liq <= 0], zv[liq <= 0], ground["height"], H, W)
        wet = ground["liquid"] > ground["height"] + preview.WATER_MIN_DEPTH  # NaN liquid compares False
        open_ground = np.flatnonzero(~covered & ~ground["hole"] & ~ground["steep"] & ~wet)
        fc, fz, fg = np.concatenate([fc, open_ground]), np.concatenate([fz, height[open_ground]]), np.concatenate([fg, np.full(len(open_ground), -1)])
    keep = layers(fc, fz)
    fc, fz, fg = fc[keep], fz[keep], fg[keep]
    lab, sizes, kept, main = regions(fc, fz, W, height, fg >= 0)
    print(f"{ui_map_id}: {len(fc)} floor layers, regions kept (yd2):", [round(sizes[k] * CELL ** 2) for k in kept])
    reach = np.isin(lab, kept)
    o = np.nonzero(reach)[0]
    o = o[np.lexsort((fz[o], lab[o] == main))]  # the city floor wins over other regions, then the higher floor
    zmap = np.full(H * W, np.nan)
    zmap[fc[o]] = fz[o]
    gmap = np.full(H * W, -1)
    gmap[fc[o]] = fg[o]

    # Liquid shows on the floor you stand on, and in pits whose bottom nobody reaches (the Great Forge's lava).
    lc, lz, lcode = cell[~floor], z[~floor], code[~floor]
    sort_key = fc * 1e4 + (fz + 2000)
    j = np.clip(np.searchsorted(sort_key, lc * 1e4 + (lz + 2000) + 0.01) - 1, 0, len(fc) - 1)
    pool = (fc[j] == lc) & (fz[j] >= lz - POOL_DEPTH)
    shown = zmap[lc]
    ok = np.where(np.isnan(shown), pool, lz > shown - LIQUID_ON_FLOOR)
    liquid = np.zeros(H * W, np.int8)
    liquid[lc[ok]] = lcode[ok]
    if outdoor:  # terrain water: where nothing stands in it, or above the shown floor
        surface = ground["liquid"].ravel()
        codes = {t: 1 + LIQUIDS.index(k) for t, k in kind_of.items()}
        on_top = np.where(np.isnan(zmap), ~covered.ravel(), surface > zmap - LIQUID_ON_FLOOR)
        at = np.flatnonzero(wet.ravel() & on_top & (liquid == 0))
        liquid[at] = [codes.get(int(t), 1) for t in ground["liquid_type"].ravel()[at]]
    zmap[liquid > 0] = np.nan
    walk = ~np.isnan(zmap).reshape(H, W)
    return {"walk": walk, "liquid": liquid.reshape(H, W), "z": zmap.reshape(H, W), "map_id": map_id,
            "box": (0, 0, W, H), "caves": [], "cities": [], "labels": label_points(db2, ui_map_id, map_id, gmap.reshape(H, W), walk, keys)}


def label_points(db2, ui_map_id, map_id, gmap, walk, keys):
    """District names at the deepest point of each named part's largest piece.

    Names come from WMOAreaTable through each model group. Most have no AreaTable row of their own, so they ship
    as English text with area 0. A name that matches an area on the same continent (Ruins of Lordaeron, Valley of
    Heroes) keeps that area's ID, so the game shows it in the player's language. The city's own areas win.
    """
    zone = next(int(r["AreaID"]) for r in csv.DictReader(open(os.path.join(db2, "UiMapAssignment.csv"), encoding="utf-8"))
                if r["UiMapID"] == str(ui_map_id) and r["OrderIndex"] == "0")
    areas = list(csv.DictReader(open(os.path.join(db2, "AreaTable.csv"), encoding="utf-8")))
    zone_name = next(r["AreaName_lang"] for r in areas if r["ID"] == str(zone))
    same_map = sorted((r["ParentAreaID"] == str(zone), int(r["ID"]), r["AreaName_lang"]) for r in areas if r["ContinentID"] == str(map_id))
    area_id = {name: i for _, i, name in same_map}  # sorted so the city's own areas overwrite others
    names = {(int(r["WMOID"]), int(r["NameSetID"]), int(r["WMOGroupID"])): r["AreaName_lang"]
             for r in csv.DictReader(open(os.path.join(db2, "WMOAreaTable.csv"), encoding="utf-8"))}
    name_of = [names.get(k, names.get((k[0], 0, k[2]), "")) for k in keys]
    out = []
    for name in sorted(set(name_of) - SKIP_NAMES - {zone_name}):
        ids = [i for i, n in enumerate(name_of) if n == name]
        pieces, n = ndimage.label(walk & np.isin(gmap, ids))
        if not n:
            continue
        sizes = np.bincount(pieces.ravel())[1:]
        depth = ndimage.distance_transform_edt(pieces == 1 + sizes.argmax())
        r, c = np.unravel_index(depth.argmax(), depth.shape)
        out.append({"r": (r + 0.5) * 2, "c": (c + 0.5) * 2, "area": area_id.get(name, 0), "name": name,
                    "yd2": float(sizes.max() * CELL ** 2)})  # supersampled pixels, as export.py expects
    return out


def render(m, style="clay"):
    """Styled RGB image, one pixel per cell."""
    walk, liquid, z = m["walk"], m["liquid"], m["z"]
    disk = lambda yd: np.hypot(*np.mgrid[-round(yd / CELL):round(yd / CELL) + 1, -round(yd / CELL):round(yd / CELL) + 1]) <= yd / CELL
    blocked = ~walk & (liquid == 0)
    pieces, _ = ndimage.label(blocked)
    blocked &= ~(np.bincount(pieces.ravel()) * CELL ** 2 < MIN_OBSTACLE_YD2)[pieces]  # crates and small props
    s = STYLES[style]
    sc = preview.SS = 2
    preview.LINE_SCALE = walk.shape[1] / 2560
    # High side of a level step: you can drop down here but not climb up.
    lowest = ndimage.minimum_filter(np.where(np.isnan(z), 1000.0, z), footprint=disk(1.0))
    drop = ~np.isnan(z) & (np.nan_to_num(z, nan=-1000.0) - lowest > LEDGE_STEP)
    pieces, _ = ndimage.label(drop)
    drop &= (np.bincount(pieces.ravel()) * CELL >= MIN_LEDGE_YARDS)[pieces]
    blocked_hi, drop_hi = smooth(blocked, 0.8, sc), smooth(drop, 0.4, sc)
    o = max(1, round(2 * preview.LINE_SCALE * 2))
    step_shadow = ndimage.gaussian_filter(np.pad(drop_hi, ((o, 0), (o, 0)))[:-o, :-o].astype(np.float32), 2 * o)
    k = max(1, round(preview.SHADOW_OFFSET_PX * 2 * preview.LINE_SCALE))
    shadow = ndimage.gaussian_filter(np.pad(blocked_hi, ((k, 0), (k, 0)))[:-k, :-k].astype(np.float32), k)
    img = np.empty((blocked_hi.shape[0] // 2, blocked_hi.shape[1] // 2, 3), np.float32)
    img[:] = s["land"]
    paint(img, shadow * ~blocked_hi, s["shadow"], 0.3)
    paint(img, step_shadow * ~drop_hi, s["shadow"], 0.35)
    wet_hi = smooth(liquid > 0, 2.0, sc)
    paint(img, drop_hi & ~blocked_hi & ~wet_hi, s["ledge"])
    paint(img, blocked_hi, s["steep"])
    paint(img, edge(blocked_hi, 1.0), s["steep_edge"])
    for code, kind in enumerate(LIQUIDS, 1):
        if (liquid == code).any():
            hi = smooth(liquid == code, 2.0, sc)
            paint(img, hi, s[kind])
            paint(img, edge(hi, 1.0) & ~blocked_hi, s[kind + "_edge"])
    return Image.fromarray(img.round().astype(np.uint8))


def main(ui_map_id, data_dir, out_png):
    from PIL import ImageDraw, ImageFont
    m = build(int(ui_map_id), data_dir)
    img = render(m)
    draw, font = ImageDraw.Draw(img), ImageFont.truetype("georgiab.ttf", 22)
    for p in m["labels"]:
        draw.text((p["c"] / 2, p["r"] / 2), p["name"].upper(), font=font, fill=(90, 50, 20), anchor="mm", stroke_width=3, stroke_fill=(250, 242, 228))
    img.save(out_png)
    print(out_png, img.size, [(p["name"], round(p["yd2"])) for p in m["labels"]])


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
