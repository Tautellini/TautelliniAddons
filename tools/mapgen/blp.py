"""Write BLP2 textures with DXT1 compression and a full mipmap chain, WoW's native texture format.

DXT1 stores each 4 x 4 block as two RGB565 colors plus 2 bits per pixel, 8 bytes per block, so a
1024 x 1024 tile is 512 KB (683 KB with mipmaps) instead of 4 MB as 32-bit TGA.
Self-test: py -3.13 blp.py   (round trip through Pillow's own BLP reader)
"""
import struct

import numpy as np
from PIL import Image


def _to565(rgb):
    rgb = rgb.astype(np.uint32)
    return ((rgb[..., 0] >> 3) << 11) | ((rgb[..., 1] >> 2) << 5) | (rgb[..., 2] >> 3)


def _from565(c):
    r, g, b = (c >> 11) & 31, (c >> 5) & 63, c & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], -1).astype(np.int32)


def encode_dxt1(rgb):
    """RGB uint8 array (H, W, 3), H and W multiples of 4, to DXT1 bytes in row-major block order."""
    h, w, _ = rgb.shape
    blocks = rgb.reshape(h // 4, 4, w // 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 3).astype(np.int32)
    # Endpoints: the brightest and darkest pixel of each block, which suits flat map colors well.
    luma = blocks @ np.array([299, 587, 114])
    hi = blocks[np.arange(len(blocks)), luma.argmax(1)]
    lo = blocks[np.arange(len(blocks)), luma.argmin(1)]
    c0, c1 = _to565(hi), _to565(lo)
    swap = c0 < c1
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    e0, e1 = _from565(c0), _from565(c1)
    # Four-color mode needs c0 > c1. Equal endpoints give a solid block, index 0 everywhere.
    palette = np.stack([e0, e1, (2 * e0 + e1) // 3, (e0 + 2 * e1) // 3], 1)
    dist = ((blocks[:, :, None, :] - palette[:, None, :, :]) ** 2).sum(-1)
    idx = dist.argmin(-1).astype(np.uint32)
    idx[c0 == c1] = 0
    bits = (idx << (2 * np.arange(16, dtype=np.uint32))).sum(1).astype(np.uint32)
    out = np.empty(len(blocks), dtype=[("c0", "<u2"), ("c1", "<u2"), ("bits", "<u4")])
    out["c0"], out["c1"], out["bits"] = c0, c1, bits
    return out.tobytes()


def write_blp(img, path):
    """Save a PIL image (power-of-two size) as BLP2, DXT1, with mipmaps down to 1 x 1."""
    img = img.convert("RGB")
    w, h = img.size
    assert w & (w - 1) == 0 and h & (h - 1) == 0, "BLP sizes must be powers of two"
    mips = []
    level = img
    while True:
        lw, lh = level.size
        a = np.asarray(level, np.uint8)
        pw, ph = max(4, (lw + 3) // 4 * 4), max(4, (lh + 3) // 4 * 4)
        if (pw, ph) != (lw, lh):  # the last levels are smaller than one block
            a = np.pad(a, ((0, ph - lh), (0, pw - lw), (0, 0)), mode="edge")
        mips.append(encode_dxt1(a))
        if lw == 1 and lh == 1 or len(mips) == 16:
            break
        level = level.resize((max(1, lw // 2), max(1, lh // 2)), Image.BOX)
    header_size = 4 + 4 + 4 + 4 + 4 + 64 + 64 + 1024
    offsets, sizes, pos = [], [], header_size
    for m in mips:
        offsets.append(pos)
        sizes.append(len(m))
        pos += len(m)
    offsets += [0] * (16 - len(offsets))
    sizes += [0] * (16 - len(sizes))
    with open(path, "wb") as f:
        # magic, type 1, compression 2 (DXT), alpha depth 0, alpha type 0 (DXT1), has mipmaps 1
        f.write(b"BLP2" + struct.pack("<I4B2I", 1, 2, 0, 0, 1, w, h))
        f.write(struct.pack("<16I", *offsets) + struct.pack("<16I", *sizes) + bytes(1024))
        for m in mips:
            f.write(m)


if __name__ == "__main__":
    import os
    import tempfile
    rng = np.random.default_rng(1)
    # A map-like test image: flat areas, soft gradients and anti-aliased edges.
    y, x = np.mgrid[0:256, 0:256]
    base = np.stack([228 - x // 8, 211 - y // 10, 186 + (x + y) // 20], -1)
    disk = (x - 120) ** 2 + (y - 90) ** 2 < 60 ** 2
    base[disk] = (146, 202, 216)
    base = np.clip(base + rng.integers(-2, 3, base.shape), 0, 255).astype(np.uint8)
    src = Image.fromarray(base)
    path = os.path.join(tempfile.mkdtemp(), "test.blp")
    write_blp(src, path)
    back = np.asarray(Image.open(path).convert("RGB"), np.float64)
    mse = ((back - base) ** 2).mean()
    psnr = 10 * np.log10(255 ** 2 / mse)
    assert back.shape == base.shape, back.shape
    assert psnr > 32, f"PSNR {psnr:.1f} dB too low"
    print(f"ok: round trip through Pillow, PSNR {psnr:.1f} dB, file {os.path.getsize(path)} bytes")
