# ClearMap

Status (2026-11-09): all zone maps were re-exported with mountain barriers, the toon look and height bands (see Decisions) and reviewed from QA sheets in `C:\dev\mapgen-data\qa-toon`. Released as 1.1.0 (`.release/ClearMap-1.1.0.zip`, tag `ClearMap-1.1.0`), following 1.0.0 on CurseForge. No in-game test of this look is recorded yet.

Status (2026-11-06): 1.0.0 prepared for CurseForge: `assets/ClearMap/` holds the logo, description (`curseforge.md`) and changelog, and `.release/ClearMap-1.0.0.zip` (65.2 MB, built from the addon folder because the tiles are gitignored) is the upload. All 51 zone maps are exported, every layer from the spec is in, and each map was reviewed from its stitched QA image. Since 2026-11-06 the four model-built capitals (Stormwind, Orgrimmar, Ironforge, Undercity) are drawn from their models' floors too (open question 2), not yet tested in game. Tested in game: the first build with Durotar (tile swap, explored overlays hidden, toggle button, `/clearmap`), then cave pins and area labels, which the user asked to make smaller and off by default. Not yet tested in game: the settings panel, the minimap, the neighbor-zone fade overlay and every map other than Durotar. Target client: WoW Forever (Interface 16001). "ClearMap" is a working name.

## Goal

Replace the world map art with new, clean map tiles generated from the game's terrain data. In the user's words: "the current worldmap is using very unclear textures, its unclear where you can run along, where cave entrances or tunnels are."

It is not a recolor. The user: "We need new map files, not just a recolor. It needs to be simple and effective, getting rid of 'wrong' detail that does not matter to the player." The look should be "modern and clean".

## Decisions

From the planning session on 2026-11-06.

| Topic | Decision |
|---|---|
| Distribution | Personal use first. Public release decided later. |
| Look | Google Maps light, Material palette. Full color, not monochrome. The user picked the "clay" palette from three previews: warm earth tones, not white, because plain white looked "drawn from a child on a paper". Smooth anti-aliased shapes, thin outlines on cliffs and shores, a soft shadow under cliffs, water fading from light shore to deep sea, roads at constant width with an outline. |
| Shown | Walkable ground, cliffs, water, roads and paths, buildings, caves and tunnels, forests, large obstacles. |
| Height | First decided: no height shading at all. Changed on 2026-11-09 after a Barrens test: "we might need some height shading to indicate that its a walkable area ON a mountain so to say. Not just the same kind of walkable area as the ground level". Walkable ground now gets three hard-edged gold bands by its height above the local basin floor. Blocked rock stays brown, so "high but walkable" and "can't go there" look different. |
| Mountain barriers | 2026-11-09: "the outer skirts behave as a natural barrier between the maps". Big blocked masses are one flat, darker fill, without the fake trails their cut-off shelves used to draw. Small hills keep the old look. |
| Toon look | 2026-11-09: "make the map art/style a LITTLE more stylized to fit the game/toon shaders more". Water in three flat bands instead of a gradient, hard cliff shadows, cel-shaded rims on barriers, 12 % more saturation on the clay palette. City maps have their own renderer and are unchanged. |
| Cliffs | Mark drop-down edges (can jump down, can't climb up) differently from plain blocked ground. |
| Unexplored areas | Show everything. No fog of war. |
| Caves and tunnels | Entrance marker plus a dashed outline of the passages underneath. |
| Toggle | A "ClearMap" button on the world map opens a menu with every option: Clear map, City maps, Cave entrances, Minimap, and Area names (Off, Essential, All). The user asked for "checkboxes for areas and so on on the map itself, not just in the menu". The options panel has the same settings and stays in sync. |
| Minimap | In v1. The user kept it after pushback about the extra work. Rotating minimap falls back to Blizzard's terrain in v1. Must work with minimap addons ("it should be made compatible"): the first build showed nothing under EllesmereUI, which moves the minimap out of `MinimapCluster` and fades the cluster to 0. Our terrain frame is now a child of the minimap one level below it, and the mask hook is installed at load time. The second build showed tiles "all over the screen": outside its rectangle a mask repeats its edge pixels, and a square mask is white at the edge. Tiles now sit in a frame with `SetClipsChildren(true)`, and masks use `CLAMPTOBLACKADDITIVE` edges. |
| Resolution | "it seems very blurry, probably because our base resolution isn't high enough". Every map now gets 1024-pixel tiles at about 1.5 yards per pixel (was a fixed 2048 pixels across, up to 5 yards per pixel for the Barrens), saved as BLP2 with DXT1 compression and mipmaps (`blp.py`, checked against Pillow's BLP reader). Line widths scale with the render width, so the world map keeps the approved look. Small maps (Thunder Bluff, Darnassus, Moonglade) still get at least 2 x 2 tiles, because the world map zooms in about three times, and supersampling may go up to 16 for them. |
| Scope | 2026-11-06 the user set the goal "finish this addon, all maps, check the quality yourself". All 51 zone maps (UiMap type 3) are exported, the 4 model-built capitals by `city.py`. Each map is reviewed from its stitched QA image before release. |
| Labels | Drawn live in game, in the client language. Off by default after the first in-game look: "the area labels should be off by default and should be a configurable toggle". Then split into Essential and All: "The original map shows way less and sometimes different areas then we do". Essential is exactly the areas Blizzard's map labels, its exploration overlays (`WorldMapOverlay`), placed at the center of each overlay's hit rect on the 1002 x 668 map canvas. Some overlays have no hit rect, and those use their texture rectangle (fixed 2026-11-06, before that 8 maps had labels piled in the top left corner). All is every subzone. Then: "The Text Labels are too big ... The original text is baked in, which means its actually smaller when far away ... The original uses uppercase text as well", and "The labels should have a configurable rectangle dark transparent background". Labels are now uppercase, 10 px for areas and 12 px for capitals when zoomed out, growing to 1.6 times at full zoom like baked-in text. A dark box behind them can be switched on, with its opacity in the options. On the box the text turns light. Defaults after the next in-game look: "the default should be area names: essential, and label deactivated". Settings version 2 applies these two defaults once to existing saved settings. "the areas in big cities like thunderbluff should count as essential": city maps have no exploration overlays, so a map without overlays uses all its subzones as essential (Thunder Bluff's three rises, Darnassus's four terraces). With a map addon that makes the map smaller, labels got "extraordinary big" when zoomed in. Labels and cave pins now size like Blizzard's own pins (`MapCanvasPinMixin:ApplyCurrentScale`): the zoom share is capped at 100 % and the map's global pin scale applies. |
| Capitals | "the big cities should be shown differently, so they are distinguishable on the map ... areas and cities arent necessarily the same kind of information". On zone maps each capital's area is highlighted in a brick tone with an outline, left out of the neighbor fade, and labeled in larger dark-red capitals. The labels show with Essential and All area names. A separate "Capital cities" switch only hid those labels and was removed: "its part of the essential settings" (2026-11-06). Its area comes from terrain area IDs plus, for underground Ironforge and Undercity, the footprint of its giant city model inside the capital map's region. The capital maps themselves are drawn from their models' floors (open question 2). |
| Cave pins | Our own frames on the map canvas, counter-scaled so they keep their size when zooming. 11 px, made "slightly smaller" after the first in-game look. Not a Blizzard data provider, so no addon code runs inside Blizzard's map refresh. Can be switched off in the map menu. |
| Corrections | Fully automatic. No hand-fix files. Errors are tuned globally. |
| Release scope | All outdoor zones in the first release. The pipeline is proven on Durotar before scaling. The user plays Horde, so Horde zones come first. |

## Scope

In v1:

- Offline pipeline that turns game files into map tiles and data files.
- New tiles for every outdoor zone on both continents, including Forever's new zones.
- Live area labels and cave entrance pins on the world map.
- Toggle button on the world map. The choice is saved.
- Minimap that shows the same tiles around the player.

Out of v1:

- Dungeon and raid maps (open question 3).
- Contour lines, dark style.
- Hand corrections per zone.
- Public release.

## What the player sees

**World map.** Every zone shows the new tiles. Blizzard's own pins (quests, flight masters, dungeon entrances) stay on top, because only the tiles change. The whole zone is visible even if it is not explored.

Map classes and how they look (exact colors chosen during the Durotar milestone):

| Class | Look |
|---|---|
| Walkable ground | Pale beige |
| Forest | Soft green over walkable ground |
| High walkable ground | Three gold bands, starting 45, 85 and 130 yards above the local basin floor |
| Blocked (too steep) | Darker gray-beige |
| Mountain barrier | One flat brown mass with cel-shaded rims |
| Drop-down edge | Ledge line on the high side, so you see where you can jump down |
| Large obstacle | Same as blocked |
| Water | Soft blue |
| Road or path | White with a thin gray edge |
| Building | Light gray footprint |
| Cave or tunnel | Dashed outline over the surface, entrance pin where you go in |

**Labels.** Town and area names drawn by the addon, crisp at any zoom, in the client's language.

**Cave entrance pins.** A pin at each entrance. The tooltip shows the cave's name.

**Toggle.** A small button in a corner of the map frame switches between ClearMap and Blizzard tiles.

**Minimap.** Same style, centered on the player, following zoom and rotation. Gathering and tracking blips still show.

**Fallbacks.** Anywhere ClearMap has no tile, Blizzard art stays. This covers instances, maps not processed yet and anything that fails to load. Indoors outside the capitals and inside instances, the minimap falls back to Blizzard's.

## Architecture

Two parts. A pipeline that runs on the PC, and an addon that only swaps files and draws pins.

### Pipeline (`tools/mapgen/`, Python)

1. **Extract.** Read the Forever install at `C:\World of Warcraft\_forever_` (product `wowf`, build 1.60.1.70790 on 2026-11-06). Needed: ADT terrain tiles, the WMO and M2 models they place, and the DB2 tables `Map`, `UiMap`, `UiMapAssignment`, `AreaTable`. The tool is chosen in the first spike (wow.export or a CASC library).
2. **Classify.** Build one raster per continent at a fixed yards-per-pixel scale. Each pixel gets one class:
   - Blocked: terrain slope above the walk limit.
   - Drop-down edge: steep drop between two walkable areas. The ledge mark goes on the high side.
   - Water: liquid data in the ADT.
   - Road: ground texture layers whose texture name matches road or path patterns, above an alpha threshold.
   - Building: footprint of outdoor WMO placements.
   - Cave or tunnel: indoor WMO groups below the terrain, drawn as a dashed outline. Entrances go to a data file.
   - Forest: density of tree models (M2 placements).
   - Obstacle: large M2 models with collision, above a size threshold.
3. **Style.** Turn classes into colors with the palette. Smooth edges.
4. **Cut.** `UiMapAssignment` maps world positions to each zone map. Cut tiles in the same grid as Blizzard's map art layer for that map (`C_Map.GetMapArtLayers`), at a higher resolution so zooming stays sharp.
5. **Data files.** Write `Data/Labels.lua` (area ID and position per map, from each terrain chunk's area ID) and `Data/Caves.lua` (entrance positions per map).

All tuning values (slope limit, scale, texture name patterns, tree patterns, obstacle size, palette) live in one config file.

### Running the pipeline

Game data lives outside the repo in `C:\dev\mapgen-data`. Nothing in it is committed.

| Folder | Content | Source |
|---|---|---|
| `db2/` | `Map`, `UiMap`, `UiMapAssignment`, `AreaTable` as CSV | `https://wago.tools/db2/<Table>/csv?build=1.60.1.70790` |
| `listfile/` | `community-listfile.csv` (file ID to name) | wowdev/wow-listfile releases |
| `extract/<map>.wdt`, `extract/<map>/` | Terrain index and ADT tiles | TACTTool |
| `cache/` | TACTTool download cache | TACTTool, run with this folder as working directory |
| `preview/` | Rendered PNGs | `preview.py` |

TACTTool 0.2.0-alpha1 sits in `C:\dev\tools\TACTTool\`. A project permission rule in `.claude/settings.local.json` allows it. It reads the local install and falls back to Blizzard's CDN for archives the running game has locked, so WoW can stay open. List files use `<fileDataID>;<name>` per line.

```
cd C:/dev/mapgen-data
TACTTool.exe -p wowf -r eu -d "C:/World of Warcraft" -m fdid -i 782779 -o extract/kalimdor.wdt
py -3.13 <repo>/tools/mapgen/wdt.py extract/kalimdor.wdt db2/UiMapAssignment.csv 1411 kalimdor durotar.txt
TACTTool.exe -p wowf -r eu -d "C:/World of Warcraft" -m list -i durotar.txt -o extract/kalimdor
py -3.13 <repo>/tools/mapgen/preview.py 1411 C:/dev/mapgen-data preview/durotar.png
py -3.13 <repo>/tools/mapgen/export.py 1411 C:/dev/mapgen-data <repo>/addons/ClearMap
```

`export.py` writes BLP tiles (and a small `fade.tga`) to `addons/ClearMap/Tiles/<uiMapID>/` and regenerates `Tiles/Tiles.lua`. The `Tiles` folder is gitignored, so a fresh clone needs this step before the addon loads. The addon is linked into the game with a junction at `C:\World of Warcraft\_forever_\Interface\AddOns\ClearMap`. Tile files are cached by the client, so a re-export may need a full restart to show.

Known limit: the addon draws its grid on every detail layer of a map. Zone maps have one layer. Fix this before continent maps get tiles.

For all maps: `wdt.py <wdt> <csv> all <map> tiles-<map>.txt extract/<map>` lists every tile of a continent and skips files already extracted, so rerunning it after a CDN timeout only fetches what is missing. `objects.py <data_dir> <map> roots|groups|m2` does the same for WMO roots, WMO groups and M2 props. `export_all.py <data_dir> <addon_dir>` exports every zone map with three worker processes and writes `Tiles.lua` once at the end. The four model-built capitals go through `city.py`, which `export.py` picks for them. `city.py <uiMapID> <data_dir> <out.png>` renders one capital with its district names for review. Memory for Stormwind was not measured. If `export_all.py` runs out of memory, export the capitals alone with `export.py`. `qa.py <addon_dir> <out_dir>` stitches each map's tiles and fade back together for review.

Each map is rendered at about 2560 pixels across before it is resampled to the 2048-pixel tile grid. The supersampling factor is picked per map (2 for the Barrens, 4 for Durotar, up to 8 for small cities), so line weights look the same on every map.

### Checking the addon without the game

luacheck is not installed, so two checks stand in before every in-game test:

```
py -3.13 tools/luasyntax.py addons/ClearMap/*.lua addons/ClearMap/Tiles/Tiles.lua
"C:/Program Files/MiKTeX/miktex/bin/x64/luatex.exe" --luaonly tools/wowmock.lua addons/ClearMap
```

`luasyntax.py` parses Lua 5.1 syntax and has a self-test (`--selftest`). `wowmock.lua` runs the addon under LuaTeX's Lua with stubbed WoW APIs: load, settings migration, world map refresh in every label mode, every option on and off, a map without tiles, the map menu, cave tooltips, the minimap update, a mask change from a minimap addon, the indoor fallback and the slash command. Planted bugs in the label, minimap and tile code paths all make it fail. It cannot find mismatches with the real WoW API. Those still need the game.

Facts confirmed in the spike:

- Kalimdor is map 1 with WDT file ID 782779. Durotar is UI map 1411, the Barrens 1413, Kalimdor 1414. Durotar covers ADT tiles x 35 to 45, y 28 to 35.
- MAID entries are row major (`[y][x]`). The MCNK position check in `adt.py` passes on every Durotar tile.
- Kalimdor's WDT has MPHD flags `0x3ca`, so alpha maps are 64 x 64 bytes and may be compressed.
- Road textures are named like `durotarroad_s.blp`, `barrensroad01_s.blp`, `kalidarroad_s.blp` and `orgrim_road_01_s.blp`.
- obj0 placements use file IDs (MDDF flag `0x40`, MODF flag `0x8`). Objects that cross a tile border appear in each tile with the same unique ID, so placements are deduplicated by it.
- WMO yaw is the stored Y rotation plus 180 degrees, with no mirroring. `test_objects.py` checks this against the stored extents: on both continents all 3087 upright placements lie inside their extents and 98.6 % fit within half a yard. The rest (Thunder Bluff's mesas, moonwells, goblin gates) have extents that also cover their decoration. About 1 in 8 placements is tilted and drawn untilted.
- Caves are WMOs under `world/wmo/dungeon/` whose path contains cave, mine, den, tunnel, barrow or wailing. Shipwrecks and ruins share that folder and are excluded.
- Trees are M2s whose file name contains "tree" or "palm". Forests are areas where the smoothed tree density passes a threshold.
- Large obstacles are M2 props with collision (MD20 collision index count at offset 216) whose collision box (offset 188) is at least 4 yards long and 2 yards tall. They are drawn as the rotated box. Boxes at least 2 yards thick are rounded (rocks, mounds, crystals), thinner ones stay crisp lines (fences, walls). Trees and walkable props (bridge, dock, pier, stair, ramp, platform and similar names) are skipped.
- Forever's new models have only placeholder names in the listfile (`models/unknown/...`) and an empty internal name. Such a model counts as a tree when it is at least 10 yards tall and its collision covers less than 35 % of its footprint (a trunk under a canopy). Without this, Forever's Elwynn trees were drawn as square obstacles.
- Tar ("8SWA Tar Pits", Un'Goro and Feralas) has the magma sound bank but is drawn dark brown as its own liquid kind.
- Liquid kinds come from `LiquidType.SoundBank`: 0 water, 1 ocean, 2 magma, 3 slime. Lava and slime are drawn orange and green. Liquids named "slime", "green" or "fel" are drawn as slime even though their sound bank is magma, because Forever's Felwood pools ("1.60.0 FX - Fel - Generic - Bright - Lake") and Green Lava look green in game.
- Zephras Isle (map 2991) floats in Skywall. Its map has no water data, only a map-wide ocean type and flat filler terrain at about 1.5 yards. On that map the Skywall area (17221), area 0 and the flat filler are drawn as pale sky. UI map 2665 has area 0, so all of its land counts as in zone.
- Forest is measured as canopy cover, not tree count. Each tree stamps a disc as wide as its model's bounding box (MD20 offset 160), capped at 30 yards, and forest needs 40 % cover over at least 400 cells (about 7000 square yards). Stranglethorn's few giant trees and Durotar's many small palms both come out right, and single trees are dropped.
- Drop-down edges: dry ground next to a cliff band that sits at least 3 yards above the band's average height marks the cliff's top. That side gets a heavier line.
- Mountain barriers (`barrier_mask`): a flood fill from the largest walkable area, over the slope mask from before gaps are closed, because closing seals real passes. Water, bridges and buildings count as passable. A cut-off pocket still counts as reachable if it holds a road, building or cave entrance, or if it does not sit more than `LEDGE_RISE` above the ground around it, since players can always drop down (Razorfen Downs is 39 yards below its surroundings). Blocked ground plus the remaining pockets becomes a barrier when the mass has at least 10000 cells or crosses the zone border. `test_barrier.py` is the self-check.
- Height bands (`height_above_floor`): the floor is the 20th percentile of walkable ground within about 830 yards. A relative floor keeps a basin that slowly rises across a zone plain. Tuned on the Barrens (28 % of walkable ground gets a band) and Durotar (3 %).
- Cave names come from `WMOAreaTable` via the WMO's ID (MOHD offset 32) and the placement's name set (MODF offset 60). Example: model 648 with name set 3 is Burning Blade Coven, with name set 2 it is Skull Rock.

### Addon (`addons/ClearMap/`, from `templates/ForeverAddonTemplate`)

- **Tiles.** Post-hook the map detail layer's tile refresh and point each tile at our file when one exists for that map. Blizzard sets the tiles in `MapCanvasDetailLayerMixin:RefreshDetailTiles` from a texture pool with `SetTexture(fileID)`. Never replace the function. Hooking the mixin table does not reach layers that already exist, because `Mixin` copies functions when a layer is created. Hook the layer instances instead.
- **Explored overlays.** Required, not optional. Blizzard's base tiles are the unexplored look, and the exploration data provider draws the explored art on top. If only the base tiles are swapped, ClearMap shows only where the player has never been. Hide those overlays while ClearMap is active. How to do it cleanly is open question 8.
- **Labels and cave pins.** One data provider on `WorldMapFrame`. Names come from `C_Map.GetAreaInfo(areaID)`, so they match the client language.
- **Toggle.** Button on the map frame, saved in SavedVariables.
- **Minimap** (`Minimap.lua`). Forever's minimap sets the mask atlas `ui-hud-minimap-frame-generic-mask` and sets it again when the rotation setting changes (`Blizzard_Minimap/Camelot/Minimap.lua`). The addon swaps it for a fully transparent mask (`Media/blank.tga`), which hides Blizzard's terrain. Blips, the player arrow and child frames such as minimap buttons are not affected by the mask. `Minimap:SetAlpha`, which FarmHud uses, was rejected because it also fades child frames. A post-hook on `Minimap:SetMaskTexture` remembers any mask Blizzard or a shape addon sets, re-applies the blank one, and uses the remembered shape for our own terrain frame. That frame sits one level below the minimap and draws the zone tiles of the current zone and its neighbors on the same continent, current zone on top. The player's world position comes from `C_Map.GetPlayerMapPosition` on the best map and the zone's world bounds in `Tiles.lua`. The view size is `C_Minimap.GetViewRadius()`, the yards from the minimap's center to its edge (on the `forever` branch, no secret returns). It follows the zoom, the indoor view and the minimap's size. HereBeDragons uses it whenever the client has it, and its fixed zoom table is only a fallback. ClearMap first used that table, and in Orgrimmar the user saw blips "swimming around" against the tiles while moving (2026-11-06). City maps are marked `city = true` in `Tiles.lua`, so the minimap keeps their tiles indoors. Indoors outside the capitals, in instances, without a position and with a rotating minimap it falls back to Blizzard's terrain.
- **Neighbor-zone fade.** Tiles are rendered without the fade so the minimap can use them seamlessly across borders. Each map gets a small `fade.tga` (256 x 256) that the world map lays over its tiles.

### Verified on the `forever` branch (2026-11-06)

| Fact | Where |
|---|---|
| Tiles set in `RefreshDetailTiles` from `detailTilePool` with `SetTexture` | `Blizzard_MapCanvas/Blizzard_MapCanvasDetailLayer.lua` |
| `AddDataProvider` and `AcquirePin` exist | `Blizzard_MapCanvas/Blizzard_MapCanvas.lua` |
| `GetPlayerMapPosition` has no secret returns, can be nil, "Only works for the player and party members" | `MapDocumentation.lua` |
| `GetPlayerFacing` has no secret returns, can be nil | `PlayerScriptDocumentation.lua` |
| `GetAreaInfo` returns the area name, no secret returns | `MapDocumentation.lua` |
| `GetMapArtLayers`, `GetMapArtLayerTextures`, `GetMapChildrenInfo`, `GetMapRectOnMap` have no secret returns | `MapDocumentation.lua` |
| The Minimap widget has no terrain override. It only has mask, zoom, blip and quest-area settings. | `MinimapFrameAPIDocumentation.lua` |

## Configuration

- In game: the toggle. Nothing else in v1.
- Pipeline: the config file above, edited by the developer.

## Performance

- World map: no per-frame cost. Files are swapped when Blizzard refreshes tiles.
- Minimap: moves a small fixed set of textures each frame while the player moves. No texture creation per frame.
- Tile files must exist when the client starts. New or changed tiles need a full client restart, not just `/reload`.
- Size budget is open (open question 6).

## Failure modes

- No tile for a map: Blizzard art stays.
- Slope errors: accepted. Fix by tuning global values, not per zone.
- Blizzard patches terrain: rerun the pipeline by hand.
- The blank-mask trick doesn't work on Forever: the minimap part stays on Blizzard art and the world map part still ships.
- Player position is nil (instances, some indoor areas): the minimap falls back to Blizzard's.

## Open questions

1. **Extraction.** Solved: TACTTool reads the `wowf` product (see "Running the pipeline").
2. **Cities.** First decided on 2026-11-06 to keep Blizzard's art for Stormwind, Orgrimmar, Ironforge and Undercity, since each is one giant WMO and drawn as a footprint it covers the whole city. The same day the user asked about Undercity, approved a test render from the model's floors ("Looks pretty good. do the cities like that and update the addon"), and all four are now drawn by `tools/mapgen/city.py`. Thunder Bluff and Darnassus stay on the terrain renderer. On zone maps, any building model wider than 250 yards is still left out, so the capitals show as a highlight there and Blackrock Mountain shows its terrain instead of a blob. How `city.py` works:
   - The up-facing triangles of the city's models are rasterized at 0.5 yd per cell. Each cell keeps all of its floor layers, not only the top one, because roofs and beams would hide the floors below. Underground cities (Undercity, Ironforge) use only their giant model. Stormwind and Orgrimmar use every model in the region except caves and mines, plus the outdoor ground.
   - Outdoor ground counts as a floor where no model stands on it. A model triangle blocks the ground under it when it reaches within 2.5 yd of the ground and is not buried more than 1 yd below it, so walls and floors cut the ground but arches and bridges over a street leave it open.
   - Layers of neighboring cells join when the height step is at most 1.5 yd. The biggest joined region is the city floor. Other regions of at least 2000 square yards count when their model floors meet the outdoor ground at their own height, which brings in the Ruins of Lordaeron (the elevators are not part of the model). Wall tops, roofs and mountain plateaus drop out by themselves.
   - The city floor wins over other regions in the same cell, then the higher floor. Liquid shows above the shown floor, and in pits whose bottom nobody reaches, such as the lava of the Great Forge. Its kind comes from the group's LiquidType (MOGP + 0x34). Level steps over 2 yd get a ledge line and a soft shadow.
   - Names come from `WMOAreaTable` through each group's ID (MOGP + 0x38). Almost all of them point to the city's own area, and AreaTable has no rows for the districts, so they ship as English text with area 0. A name that matches an area on the same continent keeps that area's ID and shows in the client language: Ruins of Lordaeron (153), Valley of Heroes (1617), Stormwind Harbor (17203). Parts named "Canals" and "Sewers" and the city's own name get no label. Essential shows parts of at least 4000 square yards (districts), All adds rooms such as SI:7 and the War Room.
   - "Lets make the city maps/minimaps configurable, defaulting to on": the City maps option (`cityMaps`, default on) switches the four back to Blizzard's maps, on the world map and the minimap. `ns.GridFor` in `ClearMap.lua` decides for both. Thunder Bluff and Darnassus are ordinary zone maps and follow Clear map only.
   - Not drawn on city maps: caves, roads, forest, trees and other props, elevators, and the neighbor-zone fade.
3. **Dungeons and raids.** Default: out of v1.
4. **Slope limit.** The commonly cited walk limit is about 50 degrees. Verify in game.
5. **Road detection.** Checked on all continents. Road textures match "road", "cobble", "street", "path" or "trail" (Elwynn, Westfall and Duskwood use cobblestone). Eastern Kingdoms roads are painted at about half strength, so the threshold is 0.3 instead of 0.5.
6. **Resolution and size.** Pick yards per pixel and the file format (TGA or BLP) after the Durotar milestone. Rough guess for the world map: 70 MB as compressed BLP, about 400 MB as TGA.
7. **Minimap.** Confirm the blank-mask trick and the zoom radius tables on Forever.
8. **Explored overlays.** Find how Forever draws them and how to hide them cleanly. Blocks the Durotar milestone.
9. **Public release.** Shipping files built from Blizzard data is a ToS gray area. The user asked to prepare the CurseForge release on 2026-11-06. The tiles are drawn from terrain geometry and object placements, not copied from Blizzard's map art.
10. **Cave entrance detection.** Solved: an entrance is the center of each WMO portal that joins an exterior group (flag `0x8`) to an interior group (flag `0x2000`). Open dens without portals get one marker at their center. Terrain holes were tried first but miss caves cut into cliff faces. The area ID under each entrance gives the pin's name.

## Done criteria

1. **Durotar milestone.** Durotar shows ClearMap tiles in game, in explored and unexplored areas alike. The toggle works and survives a relog. Labels show in the client language. Burning Blade Coven (Skull Rock) and Dustwind Cave show their entrance pins and dashed outlines. The Barrens follows right after.
2. **World milestone.** Every outdoor zone on both continents, Kalimdor first, including Forever's new zones, has tiles. Cities follow open question 2.
3. **Minimap milestone.** The minimap shows ClearMap tiles while walking, turning and zooming, and falls back indoors and in instances.

v1 is done when all three pass in game.

In-game test list: open world zones on both continents, a city, a dungeon (fallback), Burning Blade Coven, the minimap while moving with rotation on and off, every zoom level, the toggle after relog.
