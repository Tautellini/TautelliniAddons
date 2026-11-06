"""Check the WMO yaw convention against stored placement extents.

Needs extracted data. Run from tools/mapgen: py -3.13 test_objects.py <data_dir> <map>
"""
import glob
import os
import sys

from objects import bbox_corners, parse_obj0, place

data_dir, map_name = sys.argv[1:3]
wmo_dir = os.path.join(data_dir, "extract", "wmo")
worst = 0.0
n = 0
for tile in glob.glob(os.path.join(data_dir, "extract", map_name, f"{map_name}_*_obj0.adt")):
    for w in parse_obj0(open(tile, "rb").read())[1]:
        if abs(w["rot"][0]) > 1 or abs(w["rot"][2]) > 1 or not os.path.exists(os.path.join(wmo_dir, f"{w['fid']}.wmo")):
            continue
        x, y = place(bbox_corners(wmo_dir, w["fid"]), w)
        e = w["extents"]
        worst = max(worst, abs(x.min() - e[0]), abs(y.min() - e[1]), abs(x.max() - e[2]), abs(y.max() - e[3]))
        n += 1
assert n and worst < 0.5, (n, worst)
print(f"ok: {n} placements, worst error {worst:.3f} yards")
