# WorldLight

Status: v1 implemented, not yet tested in game. Target client: WoW Forever (Interface 16001).

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
- No tint indoors and inside instances. The tint fades back in outside.
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
- Indoors (`IsIndoors()`, this includes cities like Ironforge) and in instances (`IsInInstance()`), the tint fades out over one second. It fades back in when the player is outside again.
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
- `PLAYER_ENTERING_WORLD`, `ZONE_CHANGED`, `ZONE_CHANGED_INDOORS` and `ZONE_CHANGED_NEW_AREA` re-check the indoor and instance state. The one second fade runs in an `OnUpdate` that removes itself when done.

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

## Performance

One small computation every 10 seconds and a one second fade on indoor changes. No per-frame work in normal play.

## Failure modes

- Invalid slash command input: print the usage and change nothing.
- Missing or broken SavedVariables entries: fall back to the default for that key and clamp values to their range.
- Broken saved `lastFlip` data: use the current phase value without a fade.
- Fade length 0: switch at once.

## Known limits

- The server flag flips at one moment, but the game's light may change over hours. The fade starts at the flip, so it can lag behind the sky.
- If the flip happens while the player is in an instance or offline, there is no fade. The new value applies directly.
- Grouping with a player from another world can switch the sky within seconds. WorldLight still fades over the full fade length.

## Open questions

1. At which realm time does `DIEL_CYCLE_CHANGED` fire? `/worldlight status` prints the time of the last switch. Use it to tune the fade length and the default values.
2. Nameplates and floating combat text are attached to `WorldFrame`. They might get tinted too. Check in game.
3. How strong should -100 and +100 be? Tune `MAX_DARKEN` and `MAX_BRIGHTEN` in game.
4. Is +30 a good night default?

## Done criteria

- Loads on Forever without Lua errors (BugSack stays empty).
- UI elements stay unchanged at both -100 and +100. Check with screenshots.
- The tint follows the server's day and night and fades over the configured length.
- No tint indoors and in instances, and the tint fades back in outside.
- The settings panel and slash commands change values live. Values survive `/reload` and a relog.
- `tests/WorldLight/compute_test.lua` passes. Done: passes under Lua 5.1.
- Works in combat.
