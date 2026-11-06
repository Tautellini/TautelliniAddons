# ClearMap

Status: pipeline spike in progress (2026-11-06). Durotar renders with ground, cliffs, water, roads, forests, buildings, bridges, cave outlines and cave entrances. Drop-down edges and large obstacles are still missing. No addon code yet. Target client: WoW Forever (Interface 16001). "ClearMap" is a working name.

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
| Height | No height shading at all. |
| Cliffs | Mark drop-down edges (can jump down, can't climb up) differently from plain blocked ground. |
| Unexplored areas | Show everything. No fog of war. |
| Caves and tunnels | Entrance marker plus a dashed outline of the passages underneath. |
| Toggle | Button on the world map to switch back to the Blizzard map. |
| Minimap | In v1. The user kept it after pushback about the extra work. |
| Labels | Drawn live in game, in the client language. |
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
- Height shading, contour lines, dark style.
- Hand corrections per zone.
- Public release.

## What the player sees

**World map.** Every zone shows the new tiles. Blizzard's own pins (quests, flight masters, dungeon entrances) stay on top, because only the tiles change. The whole zone is visible even if it is not explored.

Map classes and how they look (exact colors chosen during the Durotar milestone):

| Class | Look |
|---|---|
| Walkable ground | Pale beige |
| Forest | Soft green over walkable ground |
| Blocked (too steep) | Darker gray-beige |
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

**Fallbacks.** Anywhere ClearMap has no tile, Blizzard art stays. This covers instances, maps not processed yet and anything that fails to load. Indoors and inside instances, the minimap falls back to Blizzard's.

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
```

Facts confirmed in the spike:

- Kalimdor is map 1 with WDT file ID 782779. Durotar is UI map 1411, the Barrens 1413, Kalimdor 1414. Durotar covers ADT tiles x 35 to 45, y 28 to 35.
- MAID entries are row major (`[y][x]`). The MCNK position check in `adt.py` passes on every Durotar tile.
- Kalimdor's WDT has MPHD flags `0x3ca`, so alpha maps are 64 x 64 bytes and may be compressed.
- Road textures are named like `durotarroad_s.blp`, `barrensroad01_s.blp`, `kalidarroad_s.blp` and `orgrim_road_01_s.blp`.
- obj0 placements use file IDs (MDDF flag `0x40`, MODF flag `0x8`). Objects that cross a tile border appear in each tile with the same unique ID, so placements are deduplicated by it.
- WMO yaw is the stored Y rotation plus 180 degrees, with no mirroring. `test_objects.py` checks this against the stored extents (233 placements, worst error 0.1 yards). About 1 in 8 placements is tilted and drawn untilted.
- Caves are WMOs under `world/wmo/dungeon/` whose path contains cave, mine, den, tunnel, barrow or wailing. Shipwrecks and ruins share that folder and are excluded.
- Trees are M2s whose file name contains "tree" or "palm". Forests are areas where the smoothed tree density passes a threshold.

### Addon (`addons/ClearMap/`, from `templates/ForeverAddonTemplate`)

- **Tiles.** Post-hook the map detail layer's tile refresh and point each tile at our file when one exists for that map. Blizzard sets the tiles in `MapCanvasDetailLayerMixin:RefreshDetailTiles` from a texture pool with `SetTexture(fileID)`. Never replace the function. Hooking the mixin table does not reach layers that already exist, because `Mixin` copies functions when a layer is created. Hook the layer instances instead.
- **Explored overlays.** Required, not optional. Blizzard's base tiles are the unexplored look, and the exploration data provider draws the explored art on top. If only the base tiles are swapped, ClearMap shows only where the player has never been. Hide those overlays while ClearMap is active. How to do it cleanly is open question 8.
- **Labels and cave pins.** One data provider on `WorldMapFrame`. Names come from `C_Map.GetAreaInfo(areaID)`, so they match the client language.
- **Toggle.** Button on the map frame, saved in SavedVariables.
- **Minimap.** Hide Blizzard's terrain with a blank mask texture (`Minimap:SetMaskTexture`), the trick HUD addons use to keep blips. Draw our tiles in a frame below the minimap. Position from `C_Map.GetPlayerMapPosition` and `C_Map.GetWorldPosFromMapPos`, rotation from `GetPlayerFacing` when the rotate-minimap setting is on. Zoom radius per zoom level comes from known tables, checked in game.

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
2. **Cities.** Stormwind, Ironforge and Undercity are mostly WMO buildings. Terrain slope says nothing about their floors. Default: keep Blizzard art for them in v1 unless WMO floor rendering turns out cheap.
3. **Dungeons and raids.** Default: out of v1.
4. **Slope limit.** The commonly cited walk limit is about 50 degrees. Verify in game.
5. **Road detection.** Forever's new zones may use new ground textures, so the name patterns need checking per continent.
6. **Resolution and size.** Pick yards per pixel and the file format (TGA or BLP) after the Durotar milestone. Rough guess for the world map: 70 MB as compressed BLP, about 400 MB as TGA.
7. **Minimap.** Confirm the blank-mask trick and the zoom radius tables on Forever.
8. **Explored overlays.** Find how Forever draws them and how to hide them cleanly. Blocks the Durotar milestone.
9. **Public release.** Shipping files built from Blizzard data is a ToS gray area. Decide before any upload.
10. **Cave entrance detection.** Solved: an entrance is the center of each WMO portal that joins an exterior group (flag `0x8`) to an interior group (flag `0x2000`). Open dens without portals get one marker at their center. Terrain holes were tried first but miss caves cut into cliff faces. The area ID under each entrance gives the pin's name.

## Done criteria

1. **Durotar milestone.** Durotar shows ClearMap tiles in game, in explored and unexplored areas alike. The toggle works and survives a relog. Labels show in the client language. Burning Blade Coven (Skull Rock) and Dustwind Cave show their entrance pins and dashed outlines. The Barrens follows right after.
2. **World milestone.** Every outdoor zone on both continents, Kalimdor first, including Forever's new zones, has tiles. Cities follow open question 2.
3. **Minimap milestone.** The minimap shows ClearMap tiles while walking, turning and zooming, and falls back indoors and in instances.

v1 is done when all three pass in game.

In-game test list: open world zones on both continents, a city, a dungeon (fallback), Burning Blade Coven, the minimap while moving with rotation on and off, every zoom level, the toggle after relog.
