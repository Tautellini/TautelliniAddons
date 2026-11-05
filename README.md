# TautelliniAddons

World of Warcraft addons, built mainly for World of Warcraft: Forever.

Forever runs on the modern Midnight client with TOC Interface `16001`, not on a Classic client. Midnight's addon restrictions, including secret values, are active. Read the [Forever development guide](docs/forever-addon-development.md) before writing code.

## Layout

| Path | Content |
|---|---|
| `addons/<Name>/` | one folder per addon, named exactly like its `.toc` file |
| `addons/WorldLight/` | tints the 3D world by day and night without touching the UI ([spec](docs/plans/worldlight.md)) |
| `tests/<Name>/` | plain Lua tests, run from the repo root with `lua tests/<Name>/<file>.lua` |
| `templates/ForeverAddonTemplate/` | minimal working addon to copy from |
| `docs/forever-addon-development.md` | client facts, TOC rules, secret values, best practices, releasing |
| `.luacheckrc` | lint configuration for all addons |

## Start a new addon

1. Copy `templates/ForeverAddonTemplate` to `addons/<Name>`.
2. Rename both files and replace `ForeverAddonTemplate` inside them with `<Name>`.
3. Add the new SavedVariables and slash command globals to `.luacheckrc`.
4. Link the folder into the game with a directory junction. Adjust the WoW path to your install.

   ```powershell
   New-Item -ItemType Junction `
     -Path "C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns\<Name>" `
     -Target "C:\dev\TautelliniAddons\addons\<Name>"
   ```

5. Restart the client so it sees the new TOC. After that, `/reload` picks up Lua changes.

## Tooling

- [luacheck](https://github.com/lunarmodules/luacheck) for linting: `luacheck .`
- [VS Code WoW API extension](https://github.com/Ketho/vscode-wow-api) for API autocompletion
- [BigWigs packager](https://github.com/BigWigsMods/packager) for CurseForge and Wago releases
