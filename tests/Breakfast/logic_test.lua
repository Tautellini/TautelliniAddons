-- Run from the repo root: lua tests/Breakfast/logic_test.lua
local ns = {}
assert(loadfile("addons/Breakfast/Logic.lua"))("Breakfast", ns)

-- Sanitize fills defaults, clamps numbers and drops a broken position
local db = ns.Sanitize({ size = 500, perRow = 0, food = "yes", pos = { "CENTER", 1 } })
assert(db.size == 56 and db.perRow == 1 and db.food == true and db.locked == false and db.pos == nil)
local kept = ns.Sanitize({ pos = { "TOPLEFT", "TOPLEFT", 10, -20 } })
assert(kept.pos[3] == 10 and kept.size == 36 and kept.perRow == 12)

-- Groups by consumable subclass. Food & Drink (5) is split, unknown kinds are left out.
assert(ns.GroupOf(1) == "potion" and ns.GroupOf(2) == "elixir" and ns.GroupOf(3) == "elixir")
assert(ns.GroupOf(4) == "bandage" and ns.GroupOf(7) == "bandage")
assert(ns.GroupOf(0) == nil and ns.GroupOf(6) == nil and ns.GroupOf(8) == nil)
assert(ns.GroupOf(5, false, false) == "food" and ns.GroupOf(5, true, false) == "drink")
assert(ns.GroupOf(5, false, true) == "buffFood" and ns.GroupOf(5, true, true) == "buffFood")

-- Order: groups first, then higher level, then lower item ID
local items = {
    { id = 4, group = "potion", level = 10 },
    { id = 3, group = "food", level = 5 },
    { id = 2, group = "food", level = 25 },
    { id = 9, group = "buffFood", level = 1 },
    { id = 1, group = "food", level = 5 },
}
local list, width, height = ns.Arrange(items, ns.Sanitize({}))
local ids = {}
for index, item in ipairs(list) do ids[index] = item.id end
assert(table.concat(ids, ",") == "9,2,1,3,4")

-- One row: 36 px buttons, 2 px spacing, 8 px extra before each new group
local xs = {}
for index, item in ipairs(list) do xs[index] = item.x; assert(item.y == 0) end
assert(table.concat(xs, ",") == "0,46,84,122,168")
assert(width == 204 and height == 36)

-- Wrapping: a new row starts at x 0 with no group gap
list, width, height = ns.Arrange(items, ns.Sanitize({ perRow = 2 }))
assert(list[3].x == 0 and list[3].y == -38 and list[4].x == 38)
assert(list[5].x == 0 and list[5].y == -76)
assert(width == 82 and height == 112)

-- A group that is turned off is left out, an empty bar has no size
list = ns.Arrange(items, ns.Sanitize({ food = false }))
assert(#list == 2 and list[1].id == 9 and list[2].id == 4)
list, width, height = ns.Arrange({}, ns.Sanitize({}))
assert(#list == 0 and width == 0 and height == 0)

print("logic_test: all passed")
