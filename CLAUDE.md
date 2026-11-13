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

## Releasing

A pushed tag `<Name>-<version>` publishes that addon on CurseForge. `.github/workflows/release.yml` runs `tools/release.py`, which builds the zip and uploads it with the matching changelog section as release notes. Details are in the Releasing section of the guide.

Do the steps in this order:

1. Ask the user before you start. A release is public and cannot be taken back. Agree on the version number: patch for fixes, minor for new features.
2. Check the addon was tested in game since its last change. If not, say so and let the user decide.
3. Set `## Version` in `addons/<Name>/<Name>.toc`.
4. In `assets/<Name>/CHANGELOG.md` rename `## Unreleased` to `## <version>`. Write the entries for players, not for developers.
5. Update `assets/<Name>/curseforge.md` when the description changed. Tell the user to paste it on CurseForge, the upload does not send it.
6. Run `python tools/release.py <Name>` as a dry run and read the printed release notes.
7. Commit only that addon's files: `addons/<Name>/`, `assets/<Name>/`, its tests and its plan. Other addons often have unfinished work in the tree. Commit message: `<Name> <version>: <short summary>`.
8. Push `main`, then create and push the tag `<Name>-<version>`. The tag must match the TOC version or the script stops.
9. Watch the run with `gh run watch` and report the result. On failure read the log, fix the cause and tell the user. Never move or reuse a tag that already uploaded a file. Use the next patch version.

Rules:

- Never run `tools/release.py` with `--upload` and never push a release tag without the user's go for that exact addon and version.
- ClearMap is released from this machine, because its tiles are not in git. Run `python tools/release.py ClearMap --upload` with `CF_API_KEY` set in the environment, then push the tag as a marker. The workflow ignores `ClearMap-` tags.
- The token lives in the GitHub secret `CF_API_KEY`. Never write it into a file, a command line or a log.
- A new addon needs its CurseForge project created by the user first. Then add `## X-Curse-Project-ID` to its TOC and create `assets/<Name>/CHANGELOG.md`.
- A dry run rewrites `.release/<Name>-<version>.zip`. Do not dry run a version that is already released if the old zip should stay.
- CurseForge reviews each file before it is public. An upload that succeeded can take a while to show.

## Workflow

- Each addon lives in `addons/<Name>/`. Start from `templates/ForeverAddonTemplate`.
- Run `luacheck .` after changes when luacheck is installed.
- Nothing here can be tested outside the game client. Say so when you hand over a change, and list what the user should test in game (open world, dungeon, boss encounter).
