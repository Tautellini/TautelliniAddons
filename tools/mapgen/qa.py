"""Stitch exported tiles back into one PNG per map, for reviewing what the addon will show.

Usage: py -3.13 qa.py <addon_dir> <out_dir> [width] [uiMapID ...]
       py -3.13 qa.py --sheets <addon_dir> <out_dir> <UiMap.csv>   (2 x 2 maps per image, labeled)
"""
import json
import os
import sys

import csv

from PIL import Image, ImageDraw


AREA_NAMES = {}


def draw_labels(img, meta, db2_dir):
    """Write the essential area labels (brown) and capital labels (red) where the addon will place them."""
    if not AREA_NAMES:
        AREA_NAMES.update((int(r["ID"]), r["AreaName_lang"]) for r in csv.DictReader(open(os.path.join(db2_dir, "AreaTable.csv"), encoding="utf-8")))
    draw = ImageDraw.Draw(img)
    for key, color in (("essential", (90, 50, 20)), ("cities", (150, 20, 10))):
        for l in meta.get(key, []):
            text = AREA_NAMES.get(l["area"], "?")
            x, y = l["x"] * img.width, l["y"] * img.height
            draw.text((x, y), text.upper() if key == "cities" else text, fill=color, anchor="mm", stroke_width=2, stroke_fill=(255, 250, 240))


def stitch(tiles_dir, ui_map_id, width, db2_dir=None):
    meta = json.load(open(os.path.join(tiles_dir, str(ui_map_id), "meta.json"), encoding="utf-8"))
    tile = Image.open(os.path.join(tiles_dir, str(ui_map_id), "0_0.tga")).width
    img = Image.new("RGB", (meta["cols"] * tile, meta["rows"] * tile))
    for r in range(meta["rows"]):
        for c in range(meta["cols"]):
            img.paste(Image.open(os.path.join(tiles_dir, str(ui_map_id), f"{r}_{c}.tga")).convert("RGB"), (c * tile, r * tile))
    # The client shows the grid at the map's own aspect (about 3:2), not the grid's.
    img = img.resize((width, round(width * 2 / 3)), Image.LANCZOS).convert("RGBA")
    fade = os.path.join(tiles_dir, str(ui_map_id), "fade.tga")
    if os.path.exists(fade):  # the world map lays the neighbor-zone fade over the tiles
        img.alpha_composite(Image.open(fade).convert("RGBA").resize(img.size, Image.LANCZOS))
    img = img.convert("RGB")
    if db2_dir:
        draw_labels(img, meta, db2_dir)
    return img


def sheets(addon_dir, out_dir, ui_map_csv, cell=700):
    names = {r["ID"]: r["Name_lang"] for r in csv.DictReader(open(ui_map_csv, encoding="utf-8"))}
    tiles_dir = os.path.join(addon_dir, "Tiles")
    ids = sorted((d for d in os.listdir(tiles_dir) if d.isdigit()), key=int)
    os.makedirs(out_dir, exist_ok=True)
    for n in range(0, len(ids), 4):
        sheet = Image.new("RGB", (2 * cell + 8, 2 * round(cell * 2 / 3) + 8), (40, 40, 40))
        for k, m in enumerate(ids[n:n + 4]):
            img = stitch(tiles_dir, m, cell, os.path.dirname(ui_map_csv))
            ImageDraw.Draw(img).text((8, 6), f"{m} {names.get(m, '?')}", fill=(20, 20, 20))
            sheet.paste(img, ((k % 2) * (cell + 8), (k // 2) * (round(cell * 2 / 3) + 8)))
        sheet.save(os.path.join(out_dir, f"sheet_{n // 4:02d}.png"))
    print(f"{len(ids)} maps on {(len(ids) + 3) // 4} sheets -> {out_dir}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--sheets"]:
        sheets(*sys.argv[2:5])
        sys.exit()
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    addon_dir, out_dir = sys.argv[1:3]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1200
    tiles_dir = os.path.join(addon_dir, "Tiles")
    ids = sys.argv[4:] or sorted(d for d in os.listdir(tiles_dir) if d.isdigit())
    os.makedirs(out_dir, exist_ok=True)
    for m in ids:
        stitch(tiles_dir, m, width).save(os.path.join(out_dir, f"{m}.png"))
    print(f"{len(ids)} maps -> {out_dir}")
