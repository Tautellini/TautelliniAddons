# Breakfast

Status: spec agreed and v1 written on 2026-11-11, not yet tested in game. Target client: WoW Forever (Interface 16001).

## Goal

A separate bar that shows every consumable the character carries as a clickable button. In the user's words: "So I always see all the different buff foods and normal food/drinks I have or loot without managing them in my bars or backpack."

## Scope

In v1:

- One button per distinct item with its stack count, found automatically in the bags.
- Six groups: buff food, food, drinks, potions, elixirs and flasks, bandages and scrolls.
- Click uses the item. Hover shows the item tooltip. The cooldown shows on the button.
- Wrapping grid, movable, lockable.
- Settings in Blizzard's panel (Options > AddOns), saved account wide.
- English and German text for the settings.

Out of v1:

- A hide list for single items.
- "Best item per group" mode.
- Key bindings for buttons.
- Hiding in combat or on mouseover.
- Masque or other skin support.
- Items in the bank.
- Other consumables such as explosives, item enhancements (sharpening stones, oils) and quest items.
- Clients other than Forever.

## User-facing behavior

- The bar lists every bag item that falls into a group that is turned on. Items come from the current character's bags.
- Group order: buff food, food, drinks, potions, elixirs and flasks, bandages and scrolls. Inside a group the highest item level comes first. Equal levels sort by item ID so the order never flickers.
- Layout is a wrapping grid. Buttons per row is a setting, default 12. A group continues where the last one ended, with a small gap between groups.
- Each button shows the icon, the total count across all bags and the cooldown swipe.
- Left click uses the item. There is no other click action in v1.
- Looting a new item adds a button. Using up an item removes its button.
- In combat the game blocks adding and removing clickable buttons. So during a fight:
  - An item that runs out stays in place, greyed out with count 0, and goes away when the fight ends.
  - New loot shows up when the fight ends.
  - Counts and cooldowns keep updating, because they are not protected.
- With no matching items the bar is hidden.
- When the bar is unlocked it shows a small drag handle, also while empty, so it can always be moved. Locked hides the handle.
- `/breakfast` opens the settings.

## Architecture

Folder `addons/Breakfast/`, started from `templates/ForeverAddonTemplate`. Plain `Breakfast.toc`, SavedVariables `BreakfastDB`.

| File | Job |
|---|---|
| `Logic.lua` | Pure Lua, no WoW API. Defaults, sanitize, group order, sorting, grid positions. Testable like `addons/WorldLight/Compute.lua`. |
| `Breakfast.lua` | Bag scan, classification, secure buttons, events, drag handle, slash command. |
| `Settings.lua` | Settings panel, same pattern as `addons/WorldLight/Settings.lua`. |
| `Locales.lua` | enUS strings with a deDE table on top. |
| `tests/Breakfast/logic_test.lua` | Asserts for sorting, grouping and grid positions. |

Data flow:

1. `BAG_UPDATE_DELAYED` and `PLAYER_ENTERING_WORLD` trigger a scan of all bag slots. The scan builds a list of `{ itemID, group, itemLevel, count }`.
2. `Logic.lua` sorts the list and returns a grid position for each entry.
3. Out of combat the addon takes buttons from a pool, sets the item on each one and places it. In combat it only sets a "dirty" flag and refreshes counts. `PLAYER_REGEN_ENABLED` runs the full rebuild.
4. `BAG_UPDATE_COOLDOWN` refreshes the cooldown swipes.
5. Item data that is not cached yet triggers a rescan on `GET_ITEM_INFO_RECEIVED`.

Buttons use `SecureActionButtonTemplate` with `type = "item"`. The bar frame itself is not protected, only the buttons are.

Classification reads the item's class and subclass from the API at runtime. No static item tables, as the dev guide demands.

| Group | Source |
|---|---|
| Potions | Consumable, subclass Potion |
| Elixirs and flasks | Consumable, subclass Elixir or Flask |
| Bandages and scrolls | Consumable, subclass Bandage or Scroll |
| Buff food, food, drinks | Consumable, subclass Food & Drink, then split as described below |

The game has no field that separates buff food, food and drinks. Plan for the split:

- Drink or food: compare the name of the item's use spell with the localized names of the basic "Food" and "Drink" spells.
- Buff food: look for the localized "Well Fed" aura name in the item tooltip.
- If a check fails, the item lands in the plain food group. Nothing is ever dropped from the bar because of a failed split.

## Configuration

All settings are account wide in `BreakfastDB`.

| Setting | Default | Range |
|---|---|---|
| Six group checkboxes | all on | on or off |
| Button size | 36 | 24 to 56 |
| Buttons per row | 12 | 1 to 24 |
| Lock position | off | on or off |
| Position | screen center | set by dragging |

## Performance notes

- No `OnUpdate`. Everything runs from events.
- One scan covers at most a few hundred bag slots and only runs after `BAG_UPDATE_DELAYED`, which the game already batches.
- Buttons come from a frame pool and are reused.

## Verify before coding

Confirmed in the `forever` branch source on 2026-11-11:

- `C_Container.GetContainerNumSlots`, `C_Container.GetContainerItemID`, `C_Container.GetItemCooldown`, `C_Item.GetItemInfoInstant`, `C_Item.GetItemInfo`, `C_Item.GetItemCount`, `C_Item.GetItemSpell`, `C_TooltipInfo.GetItemByID` and `C_Spell.GetSpellName` exist. None is marked with `SecretReturns`.
- `Enum.ItemConsumableSubclass`: Potion 1, Elixir 2, Flasksphials 3, Scroll 4, Fooddrink 5, Bandage 7.
- Tooltip lines carry `leftText`, and `GameTooltip:SetItemByID` exists (`TooltipDataHandler.lua`).
- A secure button with the attribute `useOnKeyDown = false` acts on release, whatever the player's key down setting says (`SecureTemplates.lua`).

Still open, needs the client:

- Whether Forever's items really use these subclasses. Classic data once put almost everything into one generic subclass. Test with `/dump C_Item.GetItemInfoInstant(itemID)` on a bandage, a scroll, an elixir and a flask.
- Whether spell 430 ("Drink") and spell 19705 ("Well Fed") exist. Test with `/dump C_Spell.GetSpellName(430), C_Spell.GetSpellName(19705)`.

## Open questions

- Is the buff food split reliable on a German client? It depends on tooltip wording. If it is not, the fallback is one shared food group or a small learned cache in SavedVariables.
- Do conjured mage food and water sort well by item level, or do they need their own rule?

## Done criteria

- Every food, drink, potion, elixir, flask, bandage and scroll in the bags has a button in the right group.
- A click uses the item, also in combat for potions and bandages.
- Looting and using up items updates the bar out of combat at once and after the fight in combat, with no "action blocked" error.
- Position, lock, size, row length and group toggles survive a `/reload`.
- `luacheck .` is clean and `tests/Breakfast/logic_test.lua` passes.
- Tested in the open world, in a dungeon and in a boss encounter.
