# WorldLight on CurseForge

Texts and settings for the CurseForge project page. Logo: `logo.png` in this folder (512 x 512).

## Summary

Brightens or darkens the game world by day and night. Your UI stays untouched.

## Description

**Day and night brightness for the game world. Your UI stays untouched.**

WorldLight makes the world of WoW Forever brighter or darker depending on whether it is day or night. Action bars, unit frames, chat, the map, tooltips and menus keep their normal look.

### How WorldLight differs from gamma mods

Gamma mods work by changing the game's Gamma setting. That setting applies to the whole screen, so every change also brightens or darkens your interface. WorldLight never touches Gamma. It places a tint layer between the 3D world and the interface, so only the world changes.

| | Gamma setting mods | WorldLight |
|---|---|---|
| What changes | The whole screen, UI included | Only the 3D world |
| Your own gamma setting | Overwritten | Never touched |
| After disabling the addon | Gamma stays at the last value unless the mod restores it | Everything looks exactly as before |
| Picture | True gamma curve | Tint layer: clean darkening, brightening looks slightly flatter at high values |

You can still set Gamma once to suit your monitor. WorldLight adds the day and night changes on top of it.

### Features

- Separate brightness for day and night, from -100 (darker) to +100 (brighter)
- Follows the server's own day and night, the same signal that drives the sun and moon icon on the minimap, so it matches your region
- Smooth fade between day and night, with adjustable length
- Turns itself off indoors and in dungeons and raids, where the game has no day or night
- Settings under Options > AddOns > WorldLight
- Works in combat

### Slash commands

| Command | Effect |
|---|---|
| `/worldlight` | open the settings |
| `/worldlight on` or `off` | turn WorldLight on or off |
| `/worldlight day <-100 to 100>` | set the day brightness |
| `/worldlight night <-100 to 100>` | set the night brightness |
| `/worldlight status` | show the current state |

### Good to know

- The server switches between day and night at one moment, while the sky changes gradually. WorldLight's fade starts at that switch.

### Feedback

Bug reports and ideas are welcome at https://github.com/Tautellini/TautelliniAddons/issues

## Changelog for 1.0.0

First release.

- Day and night brightness for the game world, UI untouched
- Follows the server's day and night cycle
- Smooth fade with adjustable length
- Off indoors and in instances
- Settings panel and slash commands

## Upload settings

Version 1.0.0 was tested in game and uploaded on 2026-11-05.

| Field | Value |
|---|---|
| File | `.release/WorldLight-1.0.0.zip` |
| Display name | WorldLight 1.0.0 |
| Game version | WoW Forever 1.60.1 |
| Release type | Release |
| Category | Miscellaneous |
