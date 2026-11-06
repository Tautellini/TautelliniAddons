"""Read a WDT terrain index and list the ADT files a UI map needs.

Usage: py -3.13 -I wdt.py <map.wdt> <UiMapAssignment.csv> <uiMapID> <prefix> <out_list.txt>
Writes a TACTTool list file (<fileDataID>;<name> per line) for the root, obj0 and tex0 ADTs.
"""
import csv
import math
import struct
import sys

TILE = 1600 / 3  # yards per ADT tile
MAID_NAMES = ("root", "obj0", "obj1", "tex0", "lod", "mapTexture", "mapTextureN", "minimapTexture")
WANTED = {"root": "", "obj0": "_obj0", "tex0": "_tex0"}


def read_chunks(data):
    """Return {chunk id: payload}. Chunk ids are stored byte-reversed on disk."""
    chunks, pos = {}, 0
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4][::-1].decode("ascii")
        size = struct.unpack_from("<I", data, pos + 4)[0]
        chunks[cid] = data[pos + 8:pos + 8 + size]
        pos += 8 + size
    return chunks


def parse_maid(data):
    """Return {(x, y): {name: fileDataID}} for every tile that has a root ADT."""
    maid = read_chunks(data)["MAID"]
    tiles = {}
    for i in range(64 * 64):
        ids = struct.unpack_from("<8I", maid, i * 32)
        if ids[0]:
            # shortcut: assumes row-major [y][x] like MAIN, checked against the listfile in the spike
            tiles[(i % 64, i // 64)] = dict(zip(MAID_NAMES, ids))
    return tiles


def tile_range(min_x, min_y, max_x, max_y):
    """World bounds to inclusive ADT index ranges. ADT x follows world Y, ADT y follows world X."""
    tx = range(math.floor(32 - max_y / TILE), math.floor(32 - min_y / TILE) + 1)
    ty = range(math.floor(32 - max_x / TILE), math.floor(32 - min_x / TILE) + 1)
    return tx, ty


def region_for(assign_csv, ui_map_id):
    for r in csv.DictReader(open(assign_csv, encoding="utf-8")):
        if r["UiMapID"] == str(ui_map_id) and r["OrderIndex"] == "0":
            return float(r["Region_0"]), float(r["Region_1"]), float(r["Region_3"]), float(r["Region_4"])
    raise SystemExit(f"uiMapID {ui_map_id} not in {assign_csv}")


def main(wdt_path, assign_csv, ui_map_id, prefix, out_path):
    tiles = parse_maid(open(wdt_path, "rb").read())
    tx, ty = tile_range(*region_for(assign_csv, ui_map_id))
    lines = []
    for (x, y), ids in sorted(tiles.items()):
        if x in tx and y in ty:
            lines += [f"{ids[k]};{prefix}_{x}_{y}{suffix}.adt" for k, suffix in WANTED.items() if ids[k]]
    open(out_path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{len(lines)} files for tiles x {tx.start}-{tx.stop - 1}, y {ty.start}-{ty.stop - 1} -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 6:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
