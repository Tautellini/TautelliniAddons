"""Export every zone map (UiMap type 3) in parallel, then write the addon index once.

Usage: py -3.13 export_all.py <data_dir> <addon_dir> [uiMapID ...]
"""
import csv
import os
import sys
import traceback
from multiprocessing import Pool

import export

WORKERS = 3  # at 1.5 yards per pixel the largest zones need several GB of rasters each


def zone_ids(data_dir):
    """Every zone map, the four model-built capitals included (export.py draws them with city.py)."""
    return [int(r["ID"]) for r in csv.DictReader(open(os.path.join(data_dir, "db2", "UiMap.csv"), encoding="utf-8"))
            if r["Type"] == "3"]


def run(args):
    ui_map_id, data_dir, addon_dir = args
    try:
        export.main(str(ui_map_id), data_dir, addon_dir, index=False)
        return ui_map_id, None
    except Exception:
        return ui_map_id, traceback.format_exc()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    data_dir, addon_dir = sys.argv[1:3]
    ids = [int(a) for a in sys.argv[3:]] or zone_ids(data_dir)
    with Pool(WORKERS, maxtasksperchild=1) as pool:
        failed = [(m, err) for m, err in pool.imap_unordered(run, [(m, data_dir, addon_dir) for m in ids]) if err]
    export.write_index(os.path.join(addon_dir, "Tiles"))
    for m, err in failed:
        print(f"FAILED {m}:\n{err}")
    print(f"done: {len(ids) - len(failed)} of {len(ids)} maps")
