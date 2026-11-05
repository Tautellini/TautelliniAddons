# WorldLight

Status: v1 tested in game and released as 1.0.0 on CurseForge (2026-11-05). 1.0.1 with the light color tested in game (2026-11-05). 1.0.2 fixes the indoor check for buildings, not yet tested in game. Target client: WoW Forever (Interface 16001).

## Goal

WorldLight changes how bright the 3D game world looks, based on whether it is day or night in game. In the user's words: "it should not affect the menu/ui but only the game itself."

## Why not the Gamma setting

The game's `Gamma` setting (range 0.3 to 2.8, default 1.0) brightens the UI as well. The user confirmed this in game with `/console Gamma 2.0`. So WorldLight never touches `Gamma`, `Brightness` or `Contrast`. It draws a full-screen tint layer that sits above the 3D world and below the UI. The player's own gamma setting stays as it is.

Trade-off, accepted by the user: darkening looks clean. Brightening adds light on top of the picture. That lifts dark areas but looks a bit washed out at high values. It is not a real gamma curve.

## How Forever's day and night work

Research result, 2026-11-05:

- The sky follows the realm clock, one real hour per game hour, 24 hours per cycle. Each region runs one clock. NA realms used Pacific time in the beta, and Oceania shares the Americas clock. Source: community reports, Blizzard has not published exact hours.
- Forever has a server flag for day and night that Midnight does not have. `C_DateAndTime.IsDayTime()` returns it and the `DIEL_CYCLE_CHANGED` event (payload `isDayTime`) fires when it flips. Blizzard's own minimap sun and moon icon uses exactly this (`Blizzard_Minimap/Camelot/Diel.lua`).
- The only community measurement of the light curve says: full night 00:00 to 06:00, dawn 06:00 to 12:00, full day 12:00 to 18:00, dusk 18:00 to 24:00, with light changing linearly. This is unconfirmed.

Decision: WorldLight follows the server flag instead of configured hours. It is always right for the player's region, and it keeps working if Blizzard changes the cycle length or gives Oceania its own clock. This replaces the sunrise and sunset settings from the first draft of this spec.

## Scope

In v1:

- Tint layer that can brighten or darken the world.
- One brightness value for day and one for night. Both are configurable in either direction.
- Smooth fade between the two values after the server switches between day and night.
- Configurable fade length.
- No tint indoors and inside instances by default, with a short fade. Since 1.0.2 both can be turned on, and the fade length is configurable.
- Settings in Blizzard's own panel (Options > AddOns) and slash commands for quick changes.
- Settings are saved account-wide.

Out of v1:

- Changing the `Gamma`, `Brightness` or `Contrast` settings.
- Configured sunrise and sunset hours. The server decides.
- Colored tints, for example a blue moonlight look. Candidate for v2.
- Per-character settings. Candidate for v2.
- Rules for weather, specific zones or the moon.
- Clients other than Forever.

## User-facing behavior

Brightness values go from -100 (darker) to +100 (brighter). 0 means no change.

- During the day the world uses the day value. At night it uses the night value.
- When the server flips, the value blends linearly from the old phase value to the new one over the fade length.
- A `/reload` or relog during a fade resumes the fade at the right point, because the time of the last switch is saved.
- Indoors (`IsIndoors()`) and in instances (`IsInInstance()`), the tint fades out over the indoor fade length (default 2 seconds). It fades back in when the player is outside again.
- "Tint indoors" and "Tint in instances" keep the tint on there. In an instance only "Tint in instances" counts, because most dungeons are also indoors.
- The UI is never tinted. That covers action bars, unit frames, chat, minimap, world map, menus and tooltips.
- Hiding the UI with Alt+Z keeps the tint, because it belongs to the world picture.
- Changes in the settings panel or by slash command apply at once.

### Slash commands

| Command | Effect |
|---|---|
| `/worldlight` | open the settings panel |
| `/worldlight on` and `/worldlight off` | turn the addon on or off |
| `/worldlight day <-100..100>` | set the day value |
| `/worldlight night <-100..100>` | set the night value |
| `/worldlight status` | print state, realm time, day or night, current value, indoor state and the realm time of the last switch |

## Architecture

| File | Content |
|---|---|
| `addons/WorldLight/WorldLight.toc` | `## Interface: 16001`, `## SavedVariables: WorldLightDB` |
| `addons/WorldLight/Compute.lua` | defaults, ranges, sanitizing, blend and alpha math. No WoW API calls. |
| `addons/WorldLight/Settings.lua` | Blizzard settings panel |
| `addons/WorldLight/WorldLight.lua` | tint layer, events, indoor fade, slash commands |
| `tests/WorldLight/compute_test.lua` | plain Lua 5.1 test for `Compute.lua`, run from the repo root |

### Tint layer

- One frame parented to `WorldFrame`, covering all of it, strata `BACKGROUND`, frame level 0.
- A black texture darkens. A white texture with blend mode `ADD` brightens.
- A negative value sets the black texture's alpha. A positive value sets the white texture's alpha. At 0 both are invisible, so a fade from a negative day value to a positive night value has no visible jump.
- The strongest tint is `MAX_DARKEN = 0.6` and `MAX_BRIGHTEN = 0.25` in `Compute.lua`. Both are guesses to tune in game.

### Logic

- On `PLAYER_LOGIN` the addon reads `C_DateAndTime.IsDayTime()` and starts a 10 second ticker.
- On `DIEL_CYCLE_CHANGED` it saves `{ time, isDay, realmTime }` as `lastFlip`, but only if the state really changed. An event that repeats the current state does not start a fade.
- `ns.ComputeValue(isDay, now, lastFlip, db)` returns the current value. It is pure and covered by the test.
- `PLAYER_ENTERING_WORLD`, `ZONE_CHANGED`, `ZONE_CHANGED_INDOORS` and `ZONE_CHANGED_NEW_AREA` re-check the indoor and instance state. Walking into a building (for example a bank) changes no zone, so none of these fire there. Since 1.0.2, `NEW_WMO_CHUNK` and `MINIMAP_UPDATE_ZOOM` also trigger the check, the same events the minimap uses to switch to its indoor view, and the 10 second ticker re-checks as a fallback. The indoor fade runs in an `OnUpdate` that removes itself when done. `ns.ShowsTint(indoors, inInstance, db)` decides where the tint shows and is covered by the test.

### Restrictions

- The tint frame is a plain addon frame. It makes no protected calls, so it works in combat.
- `IsDayTime`, `GetGameTime`, `IsIndoors` and `IsInInstance` carry no secret annotations on the `forever` branch.

## Configuration

| Setting | Range | Default |
|---|---|---|
| Enabled | on or off | on |
| Day brightness | -100 to 100, steps of 5 | 0 |
| Night brightness | -100 to 100, steps of 5 | 30 |
| Fade length | 0 to 180 minutes, steps of 15 | 60 |
| Light color (since 1.0.1) | any color, Blizzard color picker, stored as `AARRGGBB` hex | `ffbfd9ff`, a cool moonlight |
| Tint indoors (since 1.0.2) | on or off | off |
| Tint in instances (since 1.0.2) | on or off | off |
| Indoor fade (since 1.0.2) | 0 to 10 seconds, steps of 0.5 | 2 |

The light color is used whenever the value is positive. White light lifts every pixel evenly and reads as grey fog. A cool blue-white reads as moonlight, which looks like lighting instead of haze.

## Performance

One small computation every 10 seconds and a short fade on indoor changes. No per-frame work in normal play.

## Failure modes

- Invalid slash command input: print the usage and change nothing.
- Missing or broken SavedVariables entries: fall back to the default for that key and clamp values to their range.
- Broken saved `lastFlip` data: use the current phase value without a fade.
- Fade length 0: switch at once.

## Known limits

- The server flag flips at one moment, but the game's light may change over hours. The fade starts at the flip, so it can lag behind the sky.
- If the flip happens while the player is in an instance or offline, there is no fade. The new value applies directly.
- Grouping with a player from another world can switch the sky within seconds. WorldLight still fades over the full fade length.

## Why brightening washes out

An addon layer cannot read the picture below it. WoW offers the blend modes `DISABLE`, `BLEND`, `ALPHAKEY`, `ADD` and `MOD` (see `UI.xsd`). `MOD` multiplies by at most 1, so it can only darken. Any stack of these layers maps each pixel to `p * in + q` with `p <= 1`. Brightening therefore always lifts black as well, and that is the washed-out look. Only a real gamma curve avoids it, and the game's Gamma setting changes the UI too. Forever has no world-only exposure or lighting API.

What a layer can still use: position on the screen, and what the addon knows about the game (day or night, indoors, swimming, zone, nameplates).

## Ideas for later versions

0. Ruled out, multiply above 1: a `MOD` texture multiplies by `vertex color x texel color`, so `SetVertexColor(2, 2, 2)` would have been a real exposure gain. Tested in game on 2026-11-05: `GetVertexColor()` returns `1 1 1 1`, the value is clamped. A layer cannot brighten without lifting black.
1. Horizon gradient: lift the lower screen (ground, character, enemies) fully and the upper screen (night sky) much less, or even darken it. A lifted night sky is the most visible fog. `Texture:SetGradient` can do this on the light layer.
2. Black anchor vignette: darken the screen edges slightly while the center is lifted. The eye judges contrast from the darkest area in view, so real black at the edges makes the center read as brighter instead of foggy. Needs a radial texture shipped with the addon.
3. Lantern: lift a soft circle around the character instead of the whole screen. Close range becomes visible, the distance stays dark, and the distance is where fog shows most.
4. Real light at night: raise the `maxLightDist` and `maxLightCount` graphics settings at night so torches and lamps light more of the world. Real lighting, no washout, UI untouched. `maxLightDist` exists on Forever with the default 2048 (checked in game on 2026-11-05). `maxLightCount` is still unchecked. Next test: does a higher value visibly change night scenes, and can addon code set it with `C_CVar.SetCVar`. It only affects how far away lamps and torches still light the world, not the general darkness around the player. The player's own values must be restored by day and when the addon is turned off, and the Graphics settings panel may rewrite them when a quality preset changes.
5. Context values: an own value underwater (`IsSubmerged()`), per-zone overrides.
6. Enemy halos: faint light behind enemy nameplates outdoors so mobs stand out at night.
7. Hybrid gamma mode: the player raises Gamma once, WorldLight only darkens by day.

## Open questions

1. At which realm time does `DIEL_CYCLE_CHANGED` fire? `/worldlight status` prints the time of the last switch. Use it to tune the fade length and the default values.
2. Nameplates and floating combat text are attached to `WorldFrame`. They might get tinted too. Check in game.
3. How strong should -100 and +100 be? Tune `MAX_DARKEN` and `MAX_BRIGHTEN` in game.
4. Is +30 a good night default?

## Done criteria

Tested in game by the user before the 1.0.0 release.

- Loads on Forever without Lua errors (BugSack stays empty).
- UI elements stay unchanged at both -100 and +100. Check with screenshots.
- The tint follows the server's day and night and fades over the configured length.
- No tint indoors and in instances, and the tint fades back in outside.
- The settings panel and slash commands change values live. Values survive `/reload` and a relog.
- `tests/WorldLight/compute_test.lua` passes. Done: passes under Lua 5.1.
- Works in combat.
