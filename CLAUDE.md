# Agent guide for TautelliniAddons

This repo holds World of Warcraft addons that target World of Warcraft: Forever. The full guide is `docs/forever-addon-development.md`. Read it before you change addon code.

## Hard rules

- Forever is a Mainline client (Midnight 12.1.5 API base), not Classic. Never use Classic-only APIs or copy Classic addon code without checking the API exists on Forever.
- TOC Interface is `16001`. Use a plain `<Name>.toc` for Forever-only addons. Use `<Name>_Forever.toc` when an addon also ships for another client.
- Detect Forever with `WOW_PROJECT_ID == (WOW_PROJECT_CAMELOT or 18)`. Do not treat `WOW_PROJECT_MAINLINE` as "any modern client".
- Assume any unit, aura, threat or combat value can be a secret. Check with `issecretvalue` before arithmetic or comparisons. Pass secrets straight to widgets that accept them, such as `StatusBar:SetValue`.
- Do not build features on `COMBAT_LOG_EVENT_UNFILTERED`. It is restricted for addons.
- Before using an API, confirm it and its `SecretArguments` and `SecretReturns` fields in `Interface/AddOns/Blizzard_APIDocumentationGenerated` on the `forever` branch of https://github.com/Gethe/wow-ui-source. Do not trust memory or Midnight-only docs.
- No new globals except SavedVariables, slash command entries and deliberate public APIs. Add them to `.luacheckrc`.
- Never replace Blizzard functions. Use `hooksecurefunc` or `HookScript`. Defer protected changes while `InCombatLockdown()` is true.

## Workflow

- Each addon lives in `addons/<Name>/`. Start from `templates/ForeverAddonTemplate`.
- Run `luacheck .` after changes when luacheck is installed.
- Nothing here can be tested outside the game client. Say so when you hand over a change, and list what the user should test in game (open world, dungeon, boss encounter).
