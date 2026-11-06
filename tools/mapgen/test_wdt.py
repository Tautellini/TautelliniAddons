"""Self-check for wdt.py. Run from tools/mapgen: py -3.13 test_wdt.py"""
import struct

from wdt import parse_maid, tile_range


def chunk(cid, payload):
    return cid[::-1].encode("ascii") + struct.pack("<I", len(payload)) + payload


maid = bytearray(64 * 64 * 32)
struct.pack_into("<8I", maid, (30 * 64 + 40) * 32, 111, 222, 0, 333, 0, 0, 0, 444)  # tile x 40, y 30
wdt = chunk("MVER", struct.pack("<I", 18)) + chunk("MAID", bytes(maid))

tiles = parse_maid(wdt)
assert list(tiles) == [(40, 30)], tiles
assert tiles[(40, 30)]["root"] == 111 and tiles[(40, 30)]["tex0"] == 333 and tiles[(40, 30)]["minimapTexture"] == 444

# Durotar's UiMapAssignment region on build 1.60.1.70790
tx, ty = tile_range(-1716.6666, -7249.9995, 1808.3333, -1962.4999)
assert (tx.start, tx.stop - 1, ty.start, ty.stop - 1) == (35, 45, 28, 35), (tx, ty)
print("ok")
