"""Render a styled preview PNG of one UI map from extracted root ADTs.

Usage: py -3.13 preview.py <uiMapID> <data_dir> <out.png> [clay|sand|slate]
data_dir holds db2/*.csv, listfile/community-listfile.csv, extract/<map>.wdt and extract/<map>/<map>_X_Y*.adt.
Classes: walkable, too steep with drop-down edges, water, lava, slime, road, forest, building, bridge,
cave outline and entrance, other zone (faded).
"""
import csv
import math
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from adt import UNIT, parse_root, parse_tex0, tile_origin
from objects import m2_boxes, m2_collision, model_entrances, model_triangles, parse_obj0, place, wmo_id
from wdt import read_chunks, region_for, tile_range

WALK_LIMIT_DEG = 50  # shortcut: commonly cited limit, verify in game (spec open question 4)
WATER_MIN_DEPTH = 0.3
MIN_STEEP_CELLS = 25  # steep patches smaller than this (about 430 square yards) are noise for the player
SS = 4  # supersampled pixels per cell. Output is SS / 2 pixels per cell, anti-aliased by a 2x2 box filter.
MARGIN = 8  # cells kept around the map region so blurring has data at the edges
LINE_SCALE = 1.0  # line widths are tuned for a 2560-pixel render. export.py scales them to the actual render width.
STYLES = {
    "sand": {
        "land": (233, 224, 207), "steep": (212, 196, 172), "steep_edge": (168, 148, 118), "barrier": (190, 172, 146),
        "height": ((230, 216, 184), (226, 206, 164), (218, 194, 146)),
        "water": (160, 210, 224), "water_deep": (92, 156, 188), "water_edge": (118, 172, 196),
        "shadow": (80, 60, 40), "outside": (214, 208, 198), "border": (140, 128, 112), "hole": (93, 64, 55),
        "road": (252, 248, 240), "road_edge": (178, 160, 132),
        "sky": (224, 232, 238), "sky_edge": (176, 190, 200),
        "forest": (190, 196, 150), "building": (220, 206, 186), "building_edge": (150, 132, 108),
        "cave": (110, 96, 80), "cave_edge": (90, 76, 60), "entrance": (93, 64, 55), "entrance_ring": (252, 248, 240),
        "ledge": (120, 98, 72), "lava": (226, 112, 58), "lava_edge": (168, 64, 32), "slime": (150, 184, 96), "slime_edge": (96, 128, 56),
        "tar": (72, 62, 54), "tar_edge": (40, 34, 30), "city": (204, 140, 116), "city_edge": (146, 86, 64),
    },
    "clay": {
        "land": (228, 211, 186), "steep": (200, 168, 134), "steep_edge": (150, 112, 80), "barrier": (172, 136, 104),
        "height": ((227, 206, 170), (222, 194, 150), (214, 180, 130)),
        "water": (146, 202, 216), "water_deep": (72, 136, 170), "water_edge": (104, 160, 186),
        "shadow": (90, 50, 30), "outside": (212, 200, 184), "border": (130, 100, 76), "hole": (80, 46, 32),
        "road": (250, 242, 228), "road_edge": (176, 140, 104),
        "sky": (222, 230, 236), "sky_edge": (168, 150, 130),
        "forest": (176, 182, 128), "building": (208, 186, 162), "building_edge": (136, 100, 72),
        "cave": (110, 76, 52), "cave_edge": (96, 60, 38), "entrance": (80, 46, 32), "entrance_ring": (250, 242, 228),
        "ledge": (112, 76, 50), "lava": (226, 112, 58), "lava_edge": (160, 62, 30), "slime": (150, 184, 96), "slime_edge": (96, 128, 56),
        "tar": (70, 56, 46), "tar_edge": (40, 30, 24), "city": (198, 120, 92), "city_edge": (132, 62, 40),
    },
    "slate": {
        "land": (226, 227, 221), "steep": (197, 200, 191), "steep_edge": (146, 152, 144), "barrier": (170, 175, 166),
        "height": ((218, 220, 202), (210, 212, 184), (200, 202, 166)),
        "water": (156, 200, 216), "water_deep": (82, 140, 176), "water_edge": (112, 160, 186),
        "shadow": (40, 50, 60), "outside": (208, 210, 206), "border": (120, 126, 122), "hole": (60, 64, 70),
        "road": (250, 250, 248), "road_edge": (150, 156, 150),
        "sky": (230, 236, 242), "sky_edge": (170, 180, 190),
        "forest": (180, 196, 172), "building": (206, 208, 204), "building_edge": (130, 136, 132),
        "cave": (90, 96, 100), "cave_edge": (70, 76, 80), "entrance": (60, 64, 70), "entrance_ring": (250, 250, 248),
        "ledge": (110, 116, 110), "lava": (226, 112, 58), "lava_edge": (160, 62, 30), "slime": (150, 184, 96), "slime_edge": (96, 128, 56),
        "tar": (66, 66, 70), "tar_edge": (36, 36, 40), "city": (186, 150, 140), "city_edge": (120, 80, 70),
    },
}
SHADOW_OFFSET_PX = 3
ROAD_PATTERN = re.compile(r"road|cobble|street|path|trail")  # ground texture file names that are roads and paths
ROAD_MIN_WEIGHT = 0.3  # Eastern Kingdoms roads are painted at about half strength, Kalimdor's at full
MIN_ROAD_PX = 200  # painted road patches smaller than this (about 900 square yards) are decoration, not roads
ROAD_SPUR_PX = 8  # side branches up to this long (half cells) are thinning artifacts
ROAD_RADIUS_PX = 2.5  # drawn road half width in output pixels
ROAD_MIN_EXTENT_PX = 24  # road pieces spanning less than this (about 50 yards) are rings around props, not roads
DEEP_WATER_CELLS = 40  # distance from shore where water reaches its deepest color (about 170 yards)
TREE_NAMES = ("tree", "palm")  # M2 file names that count as trees
FOREST_SIGMA_CELLS = 2
FOREST_COVER = 0.4  # share of ground under tree canopies above which an area counts as forest
MIN_FOREST_CELLS = 400  # about 7000 square yards: a grove of several trees, not one big canopy
CANOPY_DEFAULT_YARDS = 5.0  # canopy radius for a tree whose model is not extracted
CANOPY_MAX_YARDS = 30.0  # a few tree models have huge bounding boxes; single trees are dropped by MIN_FOREST_CELLS anyway
# Forever's new models have no listfile name and an empty internal name. A tall model whose
# collision covers little of its footprint is a trunk under a canopy, so it counts as a tree.
UNNAMED_TREE_MIN_HEIGHT = 10.0
UNKNOWN_PATH = "models/unknown/"  # listfile placeholder for files nobody has named yet
UNNAMED_TREE_MAX_COLLISION_SHARE = 0.35
# Maps whose space around the land is sky, not sea. Zephras Isle floats in Skywall (area 17221),
# over flat filler terrain at about 1.5 yards that the player never reaches.
SKY_MAPS = {2991: {"areas": {17221, 0}, "filler_height": 1.5}}  # area 0: unassigned filler
CAVE_PATH = "/dungeon/"  # caves, mines and dens live under world/wmo/dungeon/, next to shipwrecks and ruins
CAVE_WORDS = ("cave", "mine", "den", "tunnel", "barrow", "wailing")
BRIDGE_NAME = "bridge"
BUILDING_MAX_YARDS = 250  # models wider than this are whole cities or dungeon complexes; their terrain is shown instead
DASH_PX = 10  # supersampled length of one dash in cave outlines
ENTRANCE_RADIUS_PX = 5  # output pixels
LIQUID_KINDS = {0: "water", 1: "water", 2: "lava", 3: "slime"}  # LiquidType.SoundBank: water, ocean, magma, slime
LEDGE_RISE = 3.0  # yards the ground next to a cliff must sit above the cliff band to count as its top edge
OBSTACLE_MIN_SIZE = 4.0  # yards along the longest side of a prop's collision box
OBSTACLE_MIN_HEIGHT = 2.0  # yards, lower props can be jumped over
OBSTACLE_THIN_YARDS = 2.0  # fences and walls thinner than this stay crisp lines
OBSTACLE_ROUNDING_CELLS = 0.4  # blur that rounds the corners of chunky obstacles
WALKABLE_WORDS = ("bridge", "dock", "pier", "stair", "ramp", "platform", "plank", "boardwalk", "walkway", "floor", "rug")
HEIGHT_BANDS = (45, 85, 130)  # yards above the local basin floor where each band starts
FLOOR_CHUNK_CELLS = 8  # one terrain chunk, about 33 yards
FLOOR_WINDOW_CHUNKS = 25  # about 830 yards: wider than a mountain range, so its top is not mistaken for a floor
FLOOR_PERCENTILE = 20  # low but not the minimum, so one ravine does not lift everything around it
BARRIER_MIN_CELLS = 10000  # blocked mass at least this big (about 170000 square yards) is a mountain range, not a hill
POCKET_WINDOW_CELLS = 29  # how far around a cut-off pocket (about 60 yards each way) to look for the ground it is compared with
OUTSIDE_FADE = 0.6  # opacity of the "outside" color over neighbor zones on the world map
CAPITAL_UIMAPS = (1453, 1454, 1455, 1456, 1457, 1458)  # Stormwind, Orgrimmar, Ironforge, Thunder Bluff, Darnassus, Undercity
CITY_FILL = 0.55  # opacity of the capital highlight on zone maps
MIN_CITY_CELLS = 50
MIN_LABEL_CELLS = 300
MIN_CITY_LABEL_CELLS = 25  # city districts are small; about 430 square yards  # subzones smaller than this (about 5000 square yards) get no label


def wmo_area_names(db2_dir):
    """{(WMO ID, name set): (area ID, English name)} for whole models (group -1)."""
    out = {}
    for r in csv.DictReader(open(os.path.join(db2_dir, "WMOAreaTable.csv"), encoding="utf-8")):
        if r["WMOGroupID"] == "-1":
            out[(int(r["WMOID"]), int(r["NameSetID"]))] = (int(r["AreaTableID"]), r["AreaName_lang"])
    return out


def liquid_kinds(db2_dir):
    """{LiquidType ID: "water" | "lava" | "slime"}."""
    # Fel and green lava behave like magma but look like slime, so their name decides the color.
    # Plain "green" is not enough: Forever's swamp water is "PBRWater - Generic - Swamp - Green".
    def kind(r):
        if re.search(r"\btar\b", r["Name"], re.I):
            return "tar"  # "8SWA Tar Pits" has the magma sound bank but is black
        if re.search(r"slime|green lava|\bfel\b", r["Name"], re.I):
            return "slime"
        return LIQUID_KINDS.get(int(r["SoundBank"]), "water")
    return {int(r["ID"]): kind(r)
            for r in csv.DictReader(open(os.path.join(db2_dir, "LiquidType.csv"), encoding="utf-8"))}


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


def smooth(mask, sigma_cells, scale=None):
    """Mask to a supersampled mask with rounded, smooth edges (blur, then threshold). scale = supersampled px per mask px."""
    f = ndimage.zoom(mask.astype(np.float32), scale or SS, order=1, grid_mode=True, mode="nearest")  # SS read now, export sets it per map
    return ndimage.gaussian_filter(f, sigma_cells * SS) > 0.5


def edge(hi, width_px):
    """Supersampled outline just outside a supersampled mask."""
    r = width_px * 2 * LINE_SCALE  # output pixels to supersampled pixels, scaled so lines keep their weight on the world map
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


def scan_listfile(listfile, fids):
    """Return (road texture IDs, {fid: name} for the given fids) in one pass over the 150 MB listfile."""
    road_ids, names = set(), {}
    for line in open(listfile, encoding="utf-8"):
        fid, name = line.rstrip("\n").split(";", 1)
        if name.startswith("tileset/") and ROAD_PATTERN.search(name.rsplit("/", 1)[-1]):
            road_ids.add(int(fid))
        elif int(fid) in fids:
            names[int(fid)] = name
    return road_ids, names


def is_tree(name, boxes):
    """True for tree models: by file name, or by shape when the model has no known name."""
    if name and not name.startswith(UNKNOWN_PATH):
        return any(t in name.rsplit("/", 1)[-1] for t in TREE_NAMES)
    bbox, collision = boxes
    if not bbox or bbox[5] - bbox[2] < UNNAMED_TREE_MIN_HEIGHT:
        return False
    footprint = (bbox[3] - bbox[0]) * (bbox[4] - bbox[1])
    covered = (collision[3] - collision[0]) * (collision[4] - collision[1]) if collision else 0.0
    return footprint > 0 and covered / footprint < UNNAMED_TREE_MAX_COLLISION_SHARE


def rasterize(tris, shape):
    """Fill (M, 3, 2) triangles given in supersampled (row, col) into a bool mask."""
    img = Image.new("1", (shape[1], shape[0]))
    draw = ImageDraw.Draw(img)
    r, c = tris[..., 0], tris[..., 1]
    area = np.abs((r[:, 1] - r[:, 0]) * (c[:, 2] - c[:, 0]) - (r[:, 2] - r[:, 0]) * (c[:, 1] - c[:, 0]))
    inside = (c.max(1) >= 0) & (c.min(1) < shape[1]) & (r.max(1) >= 0) & (r.min(1) < shape[0])
    for t in tris[(area > 0.1) & inside]:  # walls are flat from above and add nothing
        draw.polygon([(t[0, 1], t[0, 0]), (t[1, 1], t[1, 0]), (t[2, 1], t[2, 0])], fill=1)
    return np.array(img, bool)


def barrier_mask(m):
    """Mountain ranges: steep ground plus the dry shelves on them that no player can walk to."""
    rows, cols = m["steep"].shape
    from_hi = lambda hi: hi.reshape(rows, SS, cols, SS).any(axis=(1, 3))
    structures = from_hi(m["bridge"]) | from_hi(m["building"])
    swim = m["water"] | m["slime"]
    # The drawn steep mask closes small gaps, which seals real passes, so reachability uses the raw slope.
    passable = (~m["raw_steep"] | swim | structures) & ~m["sky"]  # on a floating island the sky would be the largest "ground"
    eight = np.ones((3, 3))
    labels, n = ndimage.label(passable, eight)
    sizes = ndimage.sum(passable, labels, range(1, n + 1))
    # A road, building or cave in a cut-off pocket means a way in the terrain does not show (Razorfen Downs).
    used = structures | m["road"].reshape(rows, 2, cols, 2).any(axis=(1, 3))
    for r, c in m["entrances"]:
        used[min(max(int(r / SS), 0), rows - 1), min(max(int(c / SS), 0), cols - 1)] = True
    # Players can always drop down, so a pocket only counts as cut off if it sits above the ground around it.
    main = labels == 1 + sizes.argmax()
    dry_main = (main & ~m["raw_steep"] & ~swim).astype(np.float32)
    share = ndimage.uniform_filter(dry_main, POCKET_WINDOW_CELLS)
    around = ndimage.uniform_filter(dry_main * m["ground"], POCKET_WINDOW_CELLS) / np.maximum(share, 1e-6)
    ids = np.arange(1, n + 1)
    with np.errstate(invalid="ignore"):
        rise = ndimage.mean(m["ground"] - around, np.where(share > 0, labels, 0), ids)  # NaN for a pocket with no main ground nearby
    keep = np.union1d(np.union1d([1 + sizes.argmax()], labels[used & passable]), ids[rise <= LEDGE_RISE])
    blocked = (m["steep"] | ~np.isin(labels, keep)) & ~swim & ~m["lava"] & ~m["tar"] & ~m["sky"]
    labels, n = ndimage.label(blocked, eight)
    sizes = ndimage.sum(blocked, labels, range(1, n + 1))
    # Masses crossing the zone border count at any size, so both maps of a border knob agree.
    crossing = np.intersect1d(labels[blocked & m["in_zone"]], labels[blocked & ~m["in_zone"]])
    return np.isin(labels, np.union1d(1 + np.flatnonzero(sizes >= BARRIER_MIN_CELLS), crossing))


def height_above_floor(m):
    """Yards each cell sits above the basin floor around it, measured from walkable ground only."""
    walk = (~m["steep"] & ~m["barrier"] & ~m["water"] & ~m["lava"] & ~m["slime"] & ~m["tar"] & ~m["sky"]).astype(np.float32)
    b = FLOOR_CHUNK_CELLS
    share = ndimage.uniform_filter(walk, b)
    mean = ndimage.uniform_filter(walk * m["ground"], b) / np.maximum(share, 1e-6)
    share, mean = share[b // 2::b, b // 2::b], mean[b // 2::b, b // 2::b]
    # Chunks without walkable ground take their nearest neighbor's height, so sea beds and cliffs do not count.
    nearest = ndimage.distance_transform_edt(share < 0.25, return_distances=False, return_indices=True)
    floor = ndimage.percentile_filter(mean[tuple(nearest)], FLOOR_PERCENTILE, size=FLOOR_WINDOW_CHUNKS, mode="nearest")
    floor = ndimage.gaussian_filter(floor, 4, mode="nearest")
    rows, cols = m["ground"].shape
    floor = ndimage.zoom(floor, (rows / floor.shape[0], cols / floor.shape[1]), order=1, grid_mode=True, mode="nearest")
    return ndimage.gaussian_filter(m["ground"] - floor, 1.5)  # bands follow the land, not single terrain cells


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
    adt_dir = os.path.join(data_dir, "extract", prefix)
    tx, ty = tile_range(min_x, min_y, max_x, max_y)
    m2s, wmos = {}, {}
    for y in ty:
        for x in tx:
            obj0 = os.path.join(adt_dir, f"{prefix}_{x}_{y}_obj0.adt")
            if os.path.exists(obj0):
                tm, tw = parse_obj0(open(obj0, "rb").read())
                m2s.update((o["uid"], o) for o in tm)
                wmos.update((o["uid"], o) for o in tw)
    road_ids, names = scan_listfile(os.path.join(data_dir, "listfile", "community-listfile.csv"),
                                    {o["fid"] for o in m2s.values()} | {o["fid"] for o in wmos.values()})
    rows, cols = len(ty) * 128, len(tx) * 128
    heights = np.zeros((rows + 1, cols + 1), np.float32)
    liquid = np.full((rows, cols), np.nan, np.float32)
    liquid_type = np.zeros((rows, cols), np.uint16)
    have = np.zeros((rows, cols), bool)
    zone = np.zeros((rows, cols), np.int32)
    area = np.zeros((rows, cols), np.int32)
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
            liquid[r:r + 128, c:c + 128] = t["liquid"]
            liquid_type[r:r + 128, c:c + 128] = t["liquid_type"]
            have[r:r + 128, c:c + 128] = True
            area[r:r + 128, c:c + 128] = np.kron(t["area"], np.ones((8, 8), np.int32))
            zone[r:r + 128, c:c + 128] = np.kron(np.vectorize(top)(t["area"]), np.ones((8, 8), np.int32))
            tex0 = path[:-4] + "_tex0.adt"
            if os.path.exists(tex0):
                road[2 * r:2 * r + 256, 2 * c:2 * c + 256] = parse_tex0(open(tex0, "rb").read(), road_ids, big_alpha)

    h00, h01, h10, h11 = heights[:-1, :-1], heights[:-1, 1:], heights[1:, :-1], heights[1:, 1:]
    gx = ((h01 - h00) + (h11 - h10)) / (2 * UNIT)
    gy = ((h10 - h00) + (h11 - h01)) / (2 * UNIT)
    raw_steep = np.degrees(np.arctan(np.hypot(gx, gy))) > WALK_LIMIT_DEG
    steep = ndimage.binary_closing(raw_steep, np.ones((3, 3)))  # merge broken cliff rims into one band
    steep = drop_small(steep, MIN_STEEP_CELLS)
    steep |= ~drop_small(~steep, MIN_STEEP_CELLS)  # tiny flat spots inside cliffs are noise too
    ground = (h00 + h01 + h10 + h11) / 4
    wet = np.isfinite(liquid) & (liquid > ground + WATER_MIN_DEPTH)
    kind_of = liquid_kinds(db2_dir)
    kinds = np.vectorize(lambda t: kind_of.get(int(t), "water"), otypes=[object])(liquid_type)
    lava, slime, tar = wet & (kinds == "lava"), wet & (kinds == "slime"), wet & (kinds == "tar")
    sky = np.zeros_like(wet)
    rule = SKY_MAPS.get(int(map_id))
    if rule:
        flat = np.maximum.reduce([h00, h01, h10, h11]) - np.minimum.reduce([h00, h01, h10, h11]) < 0.5
        sky = ~have | (~wet & (np.isin(area, list(rule["areas"])) | (flat & (np.abs(ground - rule["filler_height"]) < 1.5))))
        steep &= ~sky
    water = (~have | (wet & ~lava & ~slime & ~tar)) & ~sky
    # Drop-down edges: dry ground next to a cliff band that sits clearly above the band's average height.
    near = ndimage.uniform_filter(steep.astype(np.float32), 5)
    band_height = ndimage.uniform_filter(np.where(steep, ground, 0), 5) / np.maximum(near, 1e-6)
    ledge = ~steep & (near > 0) & (ground > band_height + LEDGE_RISE)
    in_zone = have & ((zone == zone_area) if zone_area else (zone != 0))  # a map without an area covers everything
    # Capitals on zone maps: their own zone, highlighted so they stand apart from ordinary areas.
    capital_regions = {int(r["AreaID"]): tuple(float(r[k]) for k in ("Region_0", "Region_1", "Region_3", "Region_4"))
                       for r in csv.DictReader(open(assign_csv, encoding="utf-8"))
                       if int(r["UiMapID"]) in CAPITAL_UIMAPS and r["OrderIndex"] == "0"}
    capital_areas = set(capital_regions) - {zone_area}
    city = have & np.isin(zone, list(capital_areas))

    # Crop to the map region plus a margin, in cells.
    ox, oy = tile_origin(tx.start, ty.start)
    r0, r1 = math.floor((ox - max_x) / UNIT), math.ceil((ox - min_x) / UNIT)
    c0, c1 = math.floor((oy - max_y) / UNIT), math.ceil((oy - min_y) / UNIT)
    pad = lambda a, v: np.pad(a, MARGIN, constant_values=v)[r0:r1 + 2 * MARGIN, c0:c1 + 2 * MARGIN]
    steep, water, in_zone, area = pad(steep, False), pad(water, True), pad(in_zone, False), pad(area, 0)
    city, zone = pad(city, False) & ~water, pad(zone, 0)
    lava, slime, tar, ledge, sky = pad(lava, False), pad(slime, False), pad(tar, False), pad(ledge, False), pad(sky, False)
    road = ndimage.gaussian_filter(np.pad(road, 2 * MARGIN)[2 * r0:2 * (r1 + 2 * MARGIN), 2 * c0:2 * (c1 + 2 * MARGIN)], 1.0) > ROAD_MIN_WEIGHT
    road = drop_small(road & ~np.kron(water | sky, np.ones((2, 2), bool)), MIN_ROAD_PX)
    road = drop_short(prune(thin(road), ROAD_SPUR_PX), ROAD_MIN_EXTENT_PX)  # center lines

    # World X, Y to supersampled (row, col) of the cropped image.
    top_x, left_y = ox - (r0 - MARGIN) * UNIT, oy - (c0 - MARGIN) * UNIT
    shape_hi = (steep.shape[0] * SS, steep.shape[1] * SS)
    to_px = lambda wx, wy: np.stack([(top_x - wx) / UNIT * SS, (left_y - wy) / UNIT * SS], -1)

    wmo_dir = os.path.join(data_dir, "extract", "wmo")
    kinds = {"building": [], "bridge": [], "cave": []}
    city_models = {a: [] for a in capital_areas}  # giant models inside a capital's region are the capital itself
    entrances, caves = [], []
    wmo_names = wmo_area_names(db2_dir)
    for w in wmos.values():
        name = names.get(w["fid"], "")
        if CAVE_PATH in name and any(k in name for k in CAVE_WORDS):
            kinds["cave"].append(to_px(*place(model_triangles(wmo_dir, w["fid"], interior_only=True), w)))
            doors = to_px(*place(model_entrances(wmo_dir, w["fid"]), w))
            entrances += list(doors)
            cave_area, cave_name = wmo_names.get((wmo_id(wmo_dir, w["fid"]), w["name_set"]), (0, ""))
            for r, c in doors:
                cell = (min(max(int(r / SS), 0), area.shape[0] - 1), min(max(int(c / SS), 0), area.shape[1] - 1))
                # Unnamed caves fall back to the terrain area at their door.
                if in_zone[cell]:  # caves of neighbor zones belong on their own map
                    caves.append({"r": r, "c": c, "area": cave_area or (0 if cave_name else int(area[cell])), "name": cave_name})
        else:
            kind = "bridge" if BRIDGE_NAME in name.rsplit("/", 1)[-1] else "building"
            wx, wy = place(model_triangles(wmo_dir, w["fid"]), w)
            if wx.size and max(np.ptp(wx), np.ptp(wy)) > BUILDING_MAX_YARDS:
                for a, (x0, y0, x1, y1) in capital_regions.items():
                    if a in city_models and x0 <= w["pos"][0] <= x1 and y0 <= w["pos"][1] <= y1:
                        city_models[a].append(to_px(wx, wy))
                continue
            kinds[kind].append(to_px(wx, wy))
    geo = {k: rasterize(np.concatenate(v), shape_hi) if v else np.zeros(shape_hi, bool) for k, v in kinds.items()}
    # Underground capitals (Ironforge, Undercity) have no terrain chunks of their own, so their model is their area.
    for a, tris in city_models.items():
        if tris:
            cells = rasterize(np.concatenate(tris), shape_hi).reshape(steep.shape[0], SS, steep.shape[1], SS).any(axis=(1, 3))
            cells &= ~water
            city |= cells
            zone = np.where(cells, a, zone)

    # Forest: ground covered by tree canopies. Each tree stamps a disc as wide as its model, so a few
    # giant jungle trees count as much as many small palms.
    m2_dir = os.path.join(data_dir, "extract", "m2")
    canopy = Image.new("L", (steep.shape[1], steep.shape[0]))
    draw = ImageDraw.Draw(canopy)
    trees = {fid for fid in {o["fid"] for o in m2s.values()} if is_tree(names.get(fid, ""), m2_boxes(m2_dir, fid))}
    for o in m2s.values():
        if o["fid"] in trees:
            box = m2_boxes(m2_dir, o["fid"])[0]
            radius = (max(abs(v) for v in (box[0], box[1], box[3], box[4])) if box else CANOPY_DEFAULT_YARDS) * o["scale"]
            radius = min(radius, CANOPY_MAX_YARDS)
            r, c = to_px(*o["pos"][:2]) / SS
            k = radius / UNIT
            draw.ellipse((c - k, r - k, c + k, r + k), fill=255)
    cover = ndimage.gaussian_filter(np.asarray(canopy, np.float32) / 255, FOREST_SIGMA_CELLS)
    forest = drop_small((cover > FOREST_COVER) & ~water & ~sky, MIN_FOREST_CELLS)

    # Large obstacles: the collision box of every prop big enough to block a player.
    quads = {"thin": [], "chunky": []}
    for o in m2s.values():
        file_name = names.get(o["fid"], "").rsplit("/", 1)[-1]
        box = m2_collision(m2_dir, o["fid"])
        if not box or o["fid"] in trees or any(w in file_name for w in WALKABLE_WORDS):
            continue
        s = o["scale"]
        if (box[5] - box[2]) * s < OBSTACLE_MIN_HEIGHT or max(box[3] - box[0], box[4] - box[1]) * s < OBSTACLE_MIN_SIZE:
            continue
        corners = np.array([(box[0], box[1]), (box[3], box[1]), (box[3], box[4]), (box[0], box[4])], np.float32)
        slim = min(box[3] - box[0], box[4] - box[1]) * s < OBSTACLE_THIN_YARDS
        quads["thin" if slim else "chunky"].append(to_px(*place(corners, o)))
    obstacle = np.zeros(shape_hi, bool)
    for kind, qs in quads.items():
        if qs:
            q = np.stack(qs)
            mask = rasterize(np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]]), shape_hi)
            if kind == "chunky":  # rocks, mounds and crystals read better rounded than as boxes
                mask = ndimage.gaussian_filter(mask.astype(np.float32), SS * OBSTACLE_ROUNDING_CELLS) > 0.5
            obstacle |= mask

    # Exact map region inside the rendered image, in output pixels (the image starts at cell r0, c0).
    px = SS / 2
    box = (((oy - max_y) / UNIT - c0) * px, ((ox - max_x) / UNIT - r0) * px, ((oy - min_y) / UNIT - c0) * px, ((ox - min_x) / UNIT - r0) * px)

    # Label anchors: the point deepest inside each subzone's largest piece of dry land.
    labels = []
    cave_areas = {c["area"] for c in caves}
    for a in np.unique(area[in_zone]):
        if a in (0, zone_area) or a in cave_areas:
            continue
        pieces, n = ndimage.label((area == a) & in_zone & ~water)
        if not n:
            continue
        sizes = ndimage.sum(pieces > 0, pieces, range(1, n + 1))
        if sizes.max() < (MIN_CITY_LABEL_CELLS if int(ui_map_id) in CAPITAL_UIMAPS else MIN_LABEL_CELLS):
            continue
        depth = ndimage.distance_transform_edt(pieces == 1 + sizes.argmax())
        r, c = np.unravel_index(depth.argmax(), depth.shape)
        labels.append({"r": (r + 0.5) * SS, "c": (c + 0.5) * SS, "area": int(a)})

    # Capital labels: the deepest point of each capital's largest piece of land on this map.
    cities = []
    visible = np.zeros_like(city)
    visible[MARGIN:-MARGIN, MARGIN:-MARGIN] = True  # anchor labels inside the map, not in the render margin
    for a in sorted(capital_areas):
        pieces, n = ndimage.label(city & (zone == a) & visible)
        if not n:
            continue
        sizes = ndimage.sum(pieces > 0, pieces, range(1, n + 1))
        if sizes.max() < MIN_CITY_CELLS:
            continue
        depth = ndimage.distance_transform_edt(pieces == 1 + sizes.argmax())
        r, c = np.unravel_index(depth.argmax(), depth.shape)
        cities.append({"r": (r + 0.5) * SS, "c": (c + 0.5) * SS, "area": int(a)})

    out = {"city": city, "cities": cities, "steep": steep & ~water & ~lava & ~slime & ~tar, "water": water, "lava": lava, "slime": slime, "tar": tar,
           "ledge": ledge, "sky": sky,
           "in_zone": in_zone, "road": road, "forest": forest, "obstacle": obstacle, "entrances": entrances, "caves": caves, "labels": labels,
           "box": box, "map_id": int(map_id), "raw_steep": pad(raw_steep, False), "ground": pad(ground, 0.0), **geo}
    out["barrier"] = barrier_mask(out)
    out["relief"] = height_above_floor(out)
    return out


def render(masks, style, markers=True, fade=True):
    """Styled RGB image. fade=False leaves other zones unfaded, for tiles shared by the world map and the minimap."""
    s = STYLES[style]
    saturate = lambda v: tuple(np.clip(np.mean(v) + (np.array(v) - np.mean(v)) * 1.12, 0, 255))  # toon look, same hues
    s = {k: [saturate(c) for c in v] if k == "height" else saturate(v) for k, v in s.items()}
    steep_hi, water_hi, zone_hi = smooth(masks["steep"], 0.8), smooth(masks["water"], 0.8), smooth(masks["in_zone"], 3.0)
    barrier_hi = smooth(masks["barrier"], 0.8)
    steep_hi |= barrier_hi  # the shared outline passes then skip the shelves inside a range
    depth = np.clip(ndimage.distance_transform_edt(masks["water"]) / DEEP_WATER_CELLS, 0, 1)
    depth = ndimage.zoom(depth.astype(np.float32), SS // 2, order=1, grid_mode=True, mode="nearest")[..., None]
    depth = np.minimum(np.floor(depth * 3) / 2, 1)  # three flat bands instead of a gradient
    water_color = np.array(s["water"], np.float32) * (1 - depth) + np.array(s["water_deep"], np.float32) * depth
    k = max(1, round(SHADOW_OFFSET_PX * 2 * LINE_SCALE))
    shadow = ndimage.gaussian_filter(np.pad(steep_hi, ((k, 0), (k, 0)))[:-k, :-k].astype(np.float32), k / 4)  # hard, offset down-right

    img = np.empty((steep_hi.shape[0] // 2, steep_hi.shape[1] // 2, 3), np.float32)
    img[:] = s["land"]
    relief = ndimage.zoom(masks["relief"], SS, order=1, grid_mode=True, mode="nearest")
    for limit, color in zip(HEIGHT_BANDS, s["height"]):
        band = relief > limit
        paint(img, band, color)
        paint(img, edge(band, 0.4), s["steep_edge"], 0.45)
    paint(img, smooth(masks["forest"], 1.5), s["forest"], 0.6)
    paint(img, shadow * ~steep_hi, s["shadow"], 0.3)
    paint(img, steep_hi, s["steep"])
    paint(img, barrier_hi, s["barrier"])
    # Cel rims: lit on faces toward the top left light, shaded on the far side.
    r = max(1, round(4 * 2 * LINE_SCALE))
    paint(img, barrier_hi & ~np.pad(barrier_hi, ((r, 0), (r, 0)))[:-r, :-r], (255, 244, 224), 0.22)
    paint(img, barrier_hi & ~np.pad(barrier_hi, ((0, r), (0, r)))[r:, r:], s["shadow"], 0.22)
    paint(img, edge(steep_hi, 1.0) & ~water_hi, s["steep_edge"])
    # Heavier line on the high side of cliffs: you can jump down there but not climb up.
    paint(img, edge(steep_hi, 1.75) & smooth(ndimage.binary_dilation(masks["ledge"]), 0.5) & ~water_hi, s["ledge"])
    for liquid in ("lava", "slime", "tar"):
        liquid_hi = smooth(masks[liquid], 0.8)
        paint(img, liquid_hi, s[liquid])
        paint(img, edge(liquid_hi, 1.0), s[liquid + "_edge"])
    r = ROAD_RADIUS_PX * 2 * LINE_SCALE
    disk = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= r
    road_hi = ndimage.binary_dilation(np.kron(masks["road"], np.ones((SS // 2, SS // 2), bool)), disk)
    paint(img, edge(road_hi, 0.75) & ~water_hi, s["road_edge"])
    paint(img, road_hi, s["road"])
    obstacle = masks["obstacle"] & ~water_hi
    paint(img, obstacle, s["steep"])
    paint(img, edge(obstacle, 0.6) & ~water_hi, s["steep_edge"])
    city_hi = smooth(masks["city"], 2.0)  # area IDs come in 33-yard chunks, so round the steps off
    paint(img, city_hi, s["city"], CITY_FILL)
    paint(img, edge(city_hi, 1.25) & ~smooth(masks["water"], 0.8), s["city_edge"])
    building = masks["building"]
    o = max(1, round(4 * LINE_SCALE))
    b_shadow = ndimage.gaussian_filter(np.pad(building, ((o, 0), (o, 0)))[:-o, :-o].astype(np.float32), 3 * LINE_SCALE)
    paint(img, b_shadow * ~building, s["shadow"], 0.35)
    paint(img, building, s["building"])
    paint(img, edge(building, 0.6), s["building_edge"])
    if fade:
        paint(img, ~zone_hi & ~water_hi, s["outside"], OUTSIDE_FADE)
    paint(img, water_hi, water_color)
    sky_hi = smooth(masks["sky"], 1.5)
    paint(img, sky_hi, s["sky"])
    paint(img, edge(sky_hi, 1.0) & ~water_hi, s["sky_edge"])
    paint(img, edge(water_hi, 1.0), s["water_edge"])
    bridge = masks["bridge"]
    paint(img, edge(bridge, 0.75), s["road_edge"])
    paint(img, bridge, s["road"])
    paint(img, edge(zone_hi, 1.0) & ~water_hi, s["border"], 0.9)
    cave = smooth(masks["cave"][::SS, ::SS], 0.6)  # round off the cave footprint before outlining it
    rows, cols = np.indices(cave.shape)
    paint(img, cave, s["cave"], 0.12)
    paint(img, edge(cave, 0.75) & ((rows + cols) // max(1, round(DASH_PX * LINE_SCALE)) % 2 == 0), s["cave_edge"])
    marks = Image.new("L", (img.shape[1] * 2, img.shape[0] * 2))
    ring, dot = ENTRANCE_RADIUS_PX * 2, (ENTRANCE_RADIUS_PX - 1.5) * 2
    for r, c in masks["entrances"] if markers else []:
        ImageDraw.Draw(marks).ellipse((c - ring, r - ring, c + ring, r + ring), fill=1)
        ImageDraw.Draw(marks).ellipse((c - dot, r - dot, c + dot, r + dot), fill=2)
    marks = np.array(marks)
    paint(img, marks >= 1, s["entrance_ring"])
    paint(img, marks == 2, s["entrance"])
    m = MARGIN * SS // 2
    return Image.fromarray(img[m:-m, m:-m].round().astype(np.uint8))


def fade_overlay(masks, style):
    """RGBA image of the neighbor-zone fade alone, for the world map to lay over unfaded tiles."""
    zone_hi, water_hi = smooth(masks["in_zone"], 3.0), smooth(masks["water"], 0.8)
    alpha = coverage(~zone_hi & ~water_hi & ~smooth(masks["city"], 2.0)) * OUTSIDE_FADE  # capitals stay unfaded
    m = MARGIN * SS // 2
    rgba = np.empty(alpha.shape + (4,), np.uint8)
    rgba[..., :3] = STYLES[style]["outside"]
    rgba[..., 3] = (alpha * 255).round()
    return Image.fromarray(rgba[m:-m, m:-m], "RGBA")


def main(ui_map_id, data_dir, out_png, style="clay"):
    img = render(build(ui_map_id, data_dir), style)
    img.save(out_png)
    print(f"{out_png}: {img.width}x{img.height} px at {UNIT * 2 / SS:.2f} yd/px, style {style}")




if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
