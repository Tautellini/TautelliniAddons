"""Check the WMO yaw convention against stored placement extents.

Needs extracted data. Run from tools/mapgen: py -3.13 test_objects.py <data_dir> <map>

The stored extents also cover a model's decoration (doodads), so for some models (Thunder Bluff's
mesas, moonwells) they are larger than the model's own box. A wrong rotation would push the box's
corners outside the extents, so the check is: every box lies inside its extents, and nearly all fit tightly.
"""
import glob
import os
import sys

from objects import bbox_corners, parse_obj0, place

TOLERANCE = 0.5  # yards
MIN_TIGHT_SHARE = 0.95

data_dir, map_name = sys.argv[1:3]
wmo_dir = os.path.join(data_dir, "extract", "wmo")
seen, tight, outside = set(), 0, []
for tile in glob.glob(os.path.join(data_dir, "extract", map_name, f"{map_name}_*_obj0.adt")):
    for w in parse_obj0(open(tile, "rb").read())[1]:
        if w["uid"] in seen or abs(w["rot"][0]) > 1 or abs(w["rot"][2]) > 1 or not os.path.exists(os.path.join(wmo_dir, f"{w['fid']}.wmo")):
            continue
        seen.add(w["uid"])
        x, y = place(bbox_corners(wmo_dir, w["fid"]), w)
        e = w["extents"]
        gaps = (x.min() - e[0], y.min() - e[1], e[2] - x.max(), e[3] - y.max())  # negative = sticks out
        if min(gaps) < -TOLERANCE:
            outside.append((w["fid"], round(float(min(gaps)), 2)))
        elif max(gaps) < TOLERANCE:
            tight += 1
n = len(seen)
assert n and not outside, f"{len(outside)} of {n} placements stick out of their extents: {outside[:5]}"
assert tight / n >= MIN_TIGHT_SHARE, f"only {tight} of {n} placements fit their extents tightly"
print(f"ok: {n} placements inside their extents, {tight} fit tightly ({tight / n:.1%})")
