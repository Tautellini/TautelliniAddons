local _, ns = ...

-- No WoW API calls in this file, so tests can load it in plain Lua

-- Display order of the groups. Each name is also the settings key of its checkbox.
ns.GROUPS = { "buffFood", "food", "drink", "potion", "elixir", "bandage" }

ns.defaults = {
    buffFood = true,
    food = true,
    drink = true,
    potion = true,
    elixir = true,
    bandage = true,
    size = 36,
    perRow = 12,
    locked = false,
}

ns.ranges = {
    size = { 24, 56 },
    perRow = { 1, 24 },
}

ns.SPACING = 2
ns.GROUP_GAP = 8

-- Replaces missing or broken saved values with defaults and keeps numbers in range
function ns.Sanitize(db)
    for key, default in pairs(ns.defaults) do
        if type(db[key]) ~= type(default) then
            db[key] = default
        elseif ns.ranges[key] then
            db[key] = math.min(ns.ranges[key][2], math.max(ns.ranges[key][1], db[key]))
        end
    end
    local pos = db.pos
    if type(pos) ~= "table" or type(pos[1]) ~= "string" or type(pos[2]) ~= "string"
        or type(pos[3]) ~= "number" or type(pos[4]) ~= "number" then
        db.pos = nil
    end
    return db
end

-- Values of Enum.ItemConsumableSubclass, checked on the forever branch
local SUBCLASS_GROUP = {
    [1] = "potion",
    [2] = "elixir",
    [3] = "elixir", -- flasks
    [4] = "bandage", -- scrolls
    [7] = "bandage",
}
local FOOD_DRINK = 5

-- Group for a consumable, or nil if Breakfast does not show that kind
function ns.GroupOf(subclassID, isDrink, isBuffFood)
    if subclassID ~= FOOD_DRINK then
        return SUBCLASS_GROUP[subclassID]
    end
    return isBuffFood and "buffFood" or isDrink and "drink" or "food"
end

local order = {}
for index, group in ipairs(ns.GROUPS) do
    order[group] = index
end

local function Before(a, b)
    if a.group ~= b.group then
        return order[a.group] < order[b.group]
    end
    if a.level ~= b.level then
        return a.level > b.level
    end
    return a.id < b.id
end

-- Takes items as { id, group, level }. Returns the items of enabled groups in display order,
-- each with x and y as offsets from the bar's top left corner, plus the bar's width and height.
function ns.Arrange(items, db)
    local list = {}
    for _, item in ipairs(items) do
        if db[item.group] then
            list[#list + 1] = item
        end
    end
    table.sort(list, Before)

    local step = db.size + ns.SPACING
    local col, row, x, width, lastGroup = 0, 0, 0, 0, nil
    for _, item in ipairs(list) do
        if col == db.perRow then
            col, x, row = 0, 0, row + 1
        elseif lastGroup and lastGroup ~= item.group then
            x = x + ns.GROUP_GAP
        end
        item.x, item.y = x, -row * step
        x, col, lastGroup = x + step, col + 1, item.group
        width = math.max(width, x - ns.SPACING)
    end
    return list, width, #list > 0 and (row + 1) * step - ns.SPACING or 0
end
