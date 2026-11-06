"""Parse a root ADT terrain tile: heights, holes, area IDs and liquids.

One tile is 16 x 16 chunks, one chunk is 8 x 8 cells, so a tile is 128 x 128 cells.
Arrays are indexed [row, col] with row 0 at the north edge and col 0 at the west edge.
"""
import struct

import numpy as np

from wdt import TILE, read_chunks

CHUNK = TILE / 16
UNIT = CHUNK / 8  # yards per cell
HIGH_RES_HOLES = 0x10000


def tile_origin(x, y):
    """World (X, Y) of a tile's north-west corner. World X points north, world Y points west."""
    return (32 - y) * TILE, (32 - x) * TILE


def iter_chunks(data):
    """Yield (id, payload) in file order. Needed because a root ADT has 256 MCNK chunks."""
    pos = 0
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4][::-1].decode("ascii")
        size = struct.unpack_from("<I", data, pos + 4)[0]
        yield cid, data[pos + 8:pos + 8 + size]
        pos += 8 + size


def parse_root(data, x, y):
    heights = np.zeros((129, 129), np.float32)
    holes = np.zeros((128, 128), bool)
    area = np.zeros((16, 16), np.int32)
    ox, oy = tile_origin(x, y)

    mcnks = [p for cid, p in iter_chunks(data) if cid == "MCNK"]
    assert len(mcnks) == 256, f"tile {x}_{y}: {len(mcnks)} MCNK chunks"
    for mcnk in mcnks:
        flags, ix, iy = struct.unpack_from("<3I", mcnk, 0)
        holes_hi = mcnk[0x14:0x1C]
        area[iy, ix] = struct.unpack_from("<I", mcnk, 0x34)[0]
        holes_lo = struct.unpack_from("<H", mcnk, 0x3C)[0]
        px, py, pz = struct.unpack_from("<3f", mcnk, 0x68)
        # The stored corner must match the tile and chunk index, which also proves the WDT tile order.
        assert abs(px - (ox - iy * CHUNK)) < 0.5 and abs(py - (oy - ix * CHUNK)) < 0.5, (x, y, ix, iy, px, py)

        sub = dict(iter_chunks(mcnk[0x80:]))
        mcvt = np.frombuffer(sub["MCVT"], "<f4", 145)
        # MCVT rows alternate 9 outer and 8 inner vertices. Only the outer grid is kept.
        outer = np.stack([mcvt[r * 17:r * 17 + 9] for r in range(9)]) + pz
        heights[iy * 8:iy * 8 + 9, ix * 8:ix * 8 + 9] = outer

        r0, c0 = iy * 8, ix * 8
        if flags & HIGH_RES_HOLES:
            for r in range(8):
                for c in range(8):
                    holes[r0 + r, c0 + c] = bool(holes_hi[r] >> c & 1)
        else:
            for b in range(16):
                if holes_lo >> b & 1:
                    r, c = b // 4 * 2, b % 4 * 2
                    holes[r0 + r:r0 + r + 2, c0 + c:c0 + c + 2] = True

    liquid = np.full((128, 128), np.nan, np.float32)
    liquid_type = np.zeros((128, 128), np.uint16)
    mh2o = read_chunks(data).get("MH2O")
    if mh2o:
        for i in range(256):
            ofs_inst, layers, _ = struct.unpack_from("<3I", mh2o, i * 12)
            iy, ix = divmod(i, 16)
            for layer in range(layers):
                ltype, _, lo, hi, xo, yo, w, h, ofs_mask, _ = struct.unpack_from("<HHffBBBBII", mh2o, ofs_inst + layer * 24)
                if ofs_mask:
                    bits = int.from_bytes(mh2o[ofs_mask:ofs_mask + (w * h + 7) // 8], "little")
                else:
                    bits = (1 << (w * h)) - 1
                level = (lo + hi) / 2  # shortcut: ignores per-vertex liquid heights, fine for flat water, revisit for rivers on slopes
                for k in range(w * h):
                    if bits >> k & 1:
                        r, c = iy * 8 + yo + k // w, ix * 8 + xo + k % w
                        if not level <= liquid[r, c]:  # also true while the cell is still NaN
                            liquid[r, c] = level
                            liquid_type[r, c] = ltype
    return {"heights": heights, "holes": holes, "area": area, "liquid": liquid, "liquid_type": liquid_type}


def decode_alpha(mcal, ofs, flags, big_alpha):
    """One 64 x 64 alpha map in 0..1."""
    if not big_alpha:
        raw = np.frombuffer(mcal, np.uint8, 2048, ofs)
        return np.stack([raw & 15, raw >> 4], -1).reshape(64, 64) / 15
    if not flags & 0x200:
        return np.frombuffer(mcal, np.uint8, 4096, ofs).reshape(64, 64) / 255
    out, pos = bytearray(), ofs
    while len(out) < 4096:
        b = mcal[pos]
        n = b & 0x7F
        if b & 0x80:  # fill: repeat the next byte n times
            out += bytes([mcal[pos + 1]]) * n
            pos += 2
        else:  # copy: take the next n bytes as they are
            out += mcal[pos + 1:pos + 1 + n]
            pos += 1 + n
    return np.frombuffer(bytes(out[:4096]), np.uint8).reshape(64, 64) / 255


def parse_tex0(data, wanted_ids, big_alpha, res=16):
    """Share of the wanted ground textures per pixel, res x res pixels per chunk.

    Layers are drawn in order, each over the ones before it with its alpha map, so a
    layer's visible weight is its alpha times (1 - alpha) of every later layer.
    """
    chunks = list(iter_chunks(data))
    mdid = next(p for cid, p in chunks if cid == "MDID")
    ids = struct.unpack(f"<{len(mdid) // 4}I", mdid)
    mcnks = [p for cid, p in chunks if cid == "MCNK"]
    assert len(mcnks) == 256
    out = np.zeros((16 * res, 16 * res), np.float32)
    f = 64 // res
    for i, mcnk in enumerate(mcnks):
        sub = dict(iter_chunks(mcnk))  # split tex0 MCNK chunks have no header
        mcly, mcal = sub.get("MCLY", b""), sub.get("MCAL", b"")
        layers = [struct.unpack_from("<3I", mcly, k * 16) for k in range(len(mcly) // 16)]
        alphas = [np.ones((64, 64))] + [decode_alpha(mcal, ofs, fl, big_alpha) for _, fl, ofs in layers[1:]]
        weight, above = np.zeros((64, 64)), np.ones((64, 64))
        for (tex, _, _), a in reversed(list(zip(layers, alphas))):
            if ids[tex] in wanted_ids:
                weight += a * above
            above *= 1 - a
        iy, ix = divmod(i, 16)
        out[iy * res:(iy + 1) * res, ix * res:(ix + 1) * res] = weight.reshape(res, f, res, f).mean(axis=(1, 3))
    return out
