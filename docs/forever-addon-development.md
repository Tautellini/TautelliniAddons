# WoW Forever Addon Development

Last checked against client 1.60.1 build 70790 (launch day, 2026-11-04). Forever is young and changes often. Facts marked "verify" are not confirmed by a primary source, so check them in your own client.

## What Forever is for an addon author

World of Warcraft: Forever is Blizzard's Classic+ game. The content is built on the original game, but the client is not a Classic client. Blizzard describes Forever and Midnight as two game types inside the same Mainline code family. In their words, Forever "shares Mainline WoW's UI architecture, including the vast majority of APIs available in 12.1.5" (Blizzard, 2026-09-15).

This has three consequences.

1. Addons written for Classic Era do not load, and Classic API habits do not carry over.
2. Addons written for Midnight usually load and are the right starting point. Midnight's addon restrictions apply in full, including secret values.
3. Classic data sets (quest databases, item stats, NPC lists) are incomplete. Forever adds new zones, quests, dungeons, raids and items.

## Client facts

| Item | Value | Source |
|---|---|---|
| TOC Interface | `16001` | Warcraft Wiki TOC_format, several addon PRs |
| `WOW_PROJECT_ID` | `18` (`WOW_PROJECT_CAMELOT`) | `Blizzard_ProjectConstants/Camelot/ProjectConstants.lua` |
| Internal codename | Camelot | Blizzard UI source |
| TOC game type | `forever`, alias `camelot` | Warcraft Wiki TOC_format |
| TOC game family | `mainline` | Warcraft Wiki TOC_format |
| Launch build | `1.60.1.70790` | wow-ui-source `forever` branch |
| Install folder | `_forever_` inside the WoW folder, for example `C:\World of Warcraft\_forever_` | Windows registry `GamePath` of an installed client. The beta used `_classic_beta_` |
| CurseForge version filter | `gameVersionTypeId=88568` | CurseForge file links |

Check your own client in game:

```
/run print(GetBuildInfo()) print("project", WOW_PROJECT_ID)
```

To find the install folder, open the Battle.net launcher, pick WoW Forever, and use "Show in Explorer".

## TOC files

### Pick a layout

| Situation | Files |
|---|---|
| Forever only | `MyAddon.toc` with `## Interface: 16001` |
| Forever and Midnight, same file list | `MyAddon.toc` with `## Interface: 120105, 16001` |
| Forever and Midnight, different file lists | `MyAddon_Forever.toc` and `MyAddon_Mainline.toc` |
| Classic Era as well | add `MyAddon_Vanilla.toc` with `11509` |

The client looks for a TOC in this order. First the game suffix (`_Forever` or `_Camelot`), then the family suffix (`_Mainline`), then the plain `MyAddon.toc`. So an addon that ships only `_Mainline.toc` also loads on Forever. If that file does not list `16001`, Forever marks it out of date.

Both `_Forever.toc` and `_Camelot.toc` work on the launch client. The `Forever` alias arrived in beta 4 (build 70291). Blizzard has said the Camelot name may change, so use `_Forever.toc` for new addons. Many published addons still ship `_Camelot.toc`.

Minimal TOC:

```
## Interface: 16001
## Title: My Addon
## Notes: What it does in one line
## Author: Tautellini
## Version: @project-version@
## SavedVariables: MyAddonDB

MyAddon.lua
```

Edits to `.lua` files need a `/reload`. New files and TOC changes need a full client restart.

### Load a file only on Forever

The most reliable way is to list a file only in `MyAddon_Forever.toc`. BetterBags does this. A `core/forever.lua` that sets `addon.isForever = true` exists only in its Forever TOC, so detection works even when runtime checks are unreliable.

A shared TOC can also use inline directives such as `ForeverOnly.lua [AllowLoadGameType forever]`. Be careful with this. If none of the listed game types are known to a client, that client treats the condition as satisfied and loads the file anyway.

File lines can use the `[Family]` and `[Game]` variables, for example `[Family]\Compat.lua`. See the TOC_format wiki page for the exact expansions.

## Runtime detection

```lua
-- WOW_PROJECT_CAMELOT is nil outside Forever, so fall back to the literal value
local isForever = WOW_PROJECT_ID == (WOW_PROJECT_CAMELOT or 18)
local isModernClient = WOW_PROJECT_ID == WOW_PROJECT_MAINLINE or isForever
```

Early beta builds (69913 and before) reported `WOW_PROJECT_ID = 1`, the retail value. Addons that used `WOW_PROJECT_ID == WOW_PROJECT_MAINLINE` to mean "modern client" quietly changed behavior when Forever switched to 18. Two rules follow from this.

- When you mean "Midnight or Forever", check both IDs like `isModernClient` above.
- Prefer feature detection over flavor checks. Examples are `if C_DamageMeter then`, probing entries in `Enum.BagIndex`, or `if issecretvalue then`.

## Secret values and addon restrictions

Blizzard: "The addon disarmament changes introduced in Midnight, including secrets, will also be active in Forever."

In practice this means:

- Some APIs return secret values in restricted situations such as combat, encounters and PvP. Addon code runs tainted, and tainted code cannot do arithmetic or comparisons on a secret. Trying to do so raises an error.
- Addon code can still pass a secret to a widget API that accepts one. `StatusBar:SetValue` and `StatusBar:SetMinMaxValues` accept secrets from addon code, so a health bar still works. You just cannot compute the percentage yourself.
- `COMBAT_LOG_EVENT_UNFILTERED` is marked `HasRestrictions` in the API docs. Do not build an addon whose core feature depends on parsing the combat log. Blizzard's own systems are the intended route. Look at `C_DamageMeter`, the Cooldown Manager, `C_CurveUtil` and `C_DurationUtil`.
- The AuraContainer and AuraButton changes from Midnight 12.1.0 are active too. Read `Blizzard_APIDocumentationGenerated` on the `forever` branch before writing aura code.

### Read the API annotations

Every entry in `Interface/AddOns/Blizzard_APIDocumentationGenerated` carries fields that say how it treats secrets. These are the ones you will see most.

| Field | Meaning |
|---|---|
| `SecretReturns = true` | May return secrets. `UnitHealth` has this. |
| `SecretWhen...Restricted = true` | Returns secrets while that restriction is active, for example `SecretWhenUnitHealthMaxRestricted` on `UnitHealthMax`. |
| `SecretArguments = "AllowedWhenTainted"` | Your addon may pass secrets in. `StatusBar:SetValue` has this. |
| `SecretArguments = "AllowedWhenUntainted"` | Only untainted Blizzard code may pass secrets in. Your addon may not. |
| `HasRestrictions = true` (events) | The event is restricted for addons. |

### Helper functions

From `FrameScriptDocumentation.lua`:

| Function | Returns |
|---|---|
| `issecretvalue(v)` | true if `v` is a secret |
| `hasanysecretvalues(...)` | true if any argument is a secret |
| `issecrettable(t)` | true if the table, or access to its contents, produces secrets |
| `canaccessvalue(v)` | true if the calling function may operate on `v` |
| `canaccesstable(t)` | true if the calling function may index `t` |
| `canaccesssecrets()` | true if the calling function may operate on secrets at all |
| `scrubsecretvalues(...)` | the arguments, with secrets replaced by `nil` |

### Pattern: compute when allowed, display always

```lua
local function HealthPercent(unit)
    local cur, maxHealth = UnitHealth(unit), UnitHealthMax(unit)
    if issecretvalue(cur) or issecretvalue(maxHealth) or maxHealth == 0 then
        return nil -- caller shows a fallback instead of a number
    end
    return cur / maxHealth * 100
end

-- The widget takes secrets directly, so the bar keeps working in combat
bar:SetMinMaxValues(0, UnitHealthMax(unit))
bar:SetValue(UnitHealth(unit))
```

Test where secrets actually appear. A test run alone in a city proves nothing. Before a release, test in the open world, in a dungeon and during a boss encounter.

### Restrictions added in Forever 1.60.1

- GUIDs: the server ID and spawn ID parts of creature, vehicle, pet and game object GUIDs are obfuscated so addons cannot compare layers. They stay stable within a session. Do not store them across sessions or use them to detect layers or respawns.
- `GetFrameStrata` returns a secret for frames that have the new FrameStrata secret aspect.
- Trial accounts cannot send addon messages. Your addon must keep working when `C_ChatInfo.SendAddonMessage` fails.
- `SendChatMessage` with `"EMOTE"` needs a hardware event outside instances, like `"SAY"` and `"YELL"`. Only send it from a click or key handler.
- Minimap rotation values are blocked during encounters.
- `C_PvP.IsWarModeFeatureEnabled` returns false.
- `GetInspectHonorData` returns two extra values: current honor and honor needed for the next level.
- Lua `require` is renamed to `import`.

## Forever-only APIs

| API | What it does |
|---|---|
| `C_DateAndTime.IsDayTime()` | true while it is day in the game world |
| `DIEL_CYCLE_CHANGED` event, payload `isDayTime` | fires when the world switches between day and night |

Blizzard's minimap sun and moon icon uses both (`Blizzard_Minimap/Camelot/Diel.lua`). The day and night cycle follows the realm clock, one real hour per game hour, with one clock per region. Use the server flag instead of guessing hours from `GetGameTime()`. WorldLight in this repo is a working example.

## UI and content differences from Midnight

- Unit frames: player, target, pet, target of target, totem and focus frames have Forever skins, and so does the minimap header. Some child frames moved. Check that a frame exists before you anchor to it or skin it. Use `/fstack` to find current names.
- Bank: 9 character bank tabs and no Warband bank. `Enum.BagIndex` still declares account tab entries, so their presence does not prove a Warband bank exists. Build bag ID lists by probing `Enum.BagIndex` instead of hard-coding the retail layout.
- Edit Mode: layouts are saved separately for mouse and keyboard and for gamepad.
- Items and quests: item stats stay hidden until an item first drops, and thousands of items were hidden from data mining. Do not ship static item or quest tables copied from Classic. Read data from the API at runtime and cache what you learn in SavedVariables. Item info that is not cached yet arrives later, so use `Item:CreateFromItemID(id):ContinueOnItemLoad(callback)` or the `GET_ITEM_INFO_RECEIVED` event.
- Built-in features: Forever has a native damage meter, the Cooldown Manager and click casting. Check whether Blizzard already covers a feature before you build it.

## General best practices

### Structure

- Use the addon namespace: `local addonName, ns = ...`. Only SavedVariables, slash command entries and deliberate public APIs belong in globals.
- Use one event frame with a dispatch table (see the template).
- Initialize SavedVariables in `ADDON_LOADED` for your own addon name. Merge defaults so existing users get new settings. Store a schema version once you need migrations.
- Embed libraries through `.pkgmeta` externals instead of committing copies. Before depending on a library, check that it has a release with `16001` in its TOC.
- Keep enUS as the fallback locale. Load other locales with `Locales\[TextLocale].lua` or a locale table.

### Taint and combat

- Never overwrite Blizzard functions or frame methods. Use `hooksecurefunc` and `frame:HookScript`.
- Protected actions fail in combat. Moving or showing secure frames and changing secure attributes are the usual cases. Check `InCombatLockdown()` and defer the work to `PLAYER_REGEN_ENABLED`.
- Use secure templates such as `SecureActionButtonTemplate` for anything that casts, targets or uses items.
- If a Blizzard panel starts throwing errors after your addon touches it, suspect taint. `/console taintLog 1` writes details to `Logs\taint.log`.

### Full-screen tint layers

Findings from WorldLight, tested in game on Forever:

- The `Gamma` setting changes the UI as well as the world. Expect the same from `Brightness` and `Contrast`.
- A frame parented to `WorldFrame` with strata `BACKGROUND` and frame level 0 draws over the 3D world and under the UI.
- Texture blend modes are `DISABLE`, `BLEND`, `ALPHAKEY`, `ADD` and `MOD`. `SetVertexColor` is clamped to 1, so `MOD` can only darken. Brightening with a layer always lifts black and looks washed out. A colored light (for example a cool moonlight) hides that better than white.

### Performance

- Prefer events and `C_Timer` over `OnUpdate`. Throttle `OnUpdate` when you cannot avoid it.
- Unregister events you no longer need.
- Reuse frames and tables. Blizzard's `CreateFramePool` handles frame reuse.

### Debugging tools

| Tool | Use |
|---|---|
| `/console scriptErrors 1` | show Lua errors in game |
| BugGrabber and BugSack | collect errors with stack traces |
| `/fstack` | names of the frames under the cursor |
| `/etrace` | live event log |
| `/dump <expr>` | print any value |
| `/tinspect <expr>` | table inspector |

## Development loop

1. Develop in `addons/<Name>/`. Link the folder into the Forever AddOns folder with a directory junction. Adjust the WoW path to your install.

   ```powershell
   New-Item -ItemType Junction `
     -Path "C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns\MyAddon" `
     -Target "C:\dev\TautelliniAddons\addons\MyAddon"
   ```

2. Run `luacheck .` before you commit.
3. Test with only your addon enabled, then together with popular addons.
4. Test in the open world, in a dungeon and in a boss encounter.

## Releasing

- The BigWigs packager (`release.sh` and the `BigWigsMods/packager` GitHub Action) supports Forever. It maps any `16xxx` Interface to the `forever` game type and accepts `camelot` as an alias.
- Git tags set the version. The packager replaces `@project-version@` in the TOC.
- Uploads need `CF_API_KEY` for CurseForge and `WAGO_API_TOKEN` for Wago as repository secrets.
- Many Forever builds on CurseForge carry a `-forever` version suffix, for example `1.60.21-forever`. That is a community convention, not a requirement.
- Tag each file with the Forever game version on CurseForge and on Wago, or users will not find it in the Forever filter.

## Resources

- Blizzard UI source, `forever` branch: https://github.com/Gethe/wow-ui-source/tree/forever
  - API docs: `Interface/AddOns/Blizzard_APIDocumentationGenerated`
  - Secret value helpers: `Interface/AddOns/Blizzard_SharedXMLBase/SecureTypes.lua`
- Warcraft Wiki
  - TOC format: https://warcraft.wiki.gg/wiki/TOC_format
  - WOW_PROJECT_ID: https://warcraft.wiki.gg/wiki/WOW_PROJECT_ID
  - Patch 1.60.1 API changes: https://warcraft.wiki.gg/wiki/Patch_1.60.1/API_changes/notes
- VS Code WoW API extension (annotations and autocompletion): https://github.com/Ketho/vscode-wow-api
- BigWigs packager: https://github.com/BigWigsMods/packager
- Real Forever ports worth reading
  - BetterBags, Forever support: https://github.com/Cidan/BetterBags/pull/1092
  - Gaar.WowAddons, project ID change: https://github.com/Tgaarden/Gaar.WowAddons/pull/17
  - Quartz, Forever support: https://github.com/Nevcairiel/Quartz/pull/110
- Community list of addons that work on Forever: https://kami-labs.fr/en/addons-wow-forever/
