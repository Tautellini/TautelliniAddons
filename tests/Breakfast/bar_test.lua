-- Runs the whole addon against a stubbed WoW API, on a German client.
-- Run from the repo root: lua tests/Breakfast/bar_test.lua
-- The stubs only model what Breakfast touches. Real API mismatches still need an in-game test.
unpack = unpack or table.unpack

local inCombat = false
local printed = {}

-- Protected frames (the secure buttons and their parent bar) must not be changed in combat
local PROTECTED_CALLS = { SetAttribute = true, Show = true, Hide = true, SetPoint = true, ClearAllPoints = true,
    SetSize = true, StartMoving = true, StopMovingOrSizing = true }

local Widget = {}
Widget.__index = function(self, key)
    local method = rawget(Widget, key)
    if method == nil and type(key) == "string" and key:match("^%u") then -- WoW methods are CamelCase, data fields are not
        method = function() end
    end
    if method and PROTECTED_CALLS[key] then
        return function(frame, ...)
            assert(not (inCombat and frame.protected), key .. " on a protected frame in combat")
            return method(frame, ...)
        end
    end
    return method
end
local function NewWidget(kind, parent, template)
    local widget = setmetatable({ kind = kind, parent = parent, shown = true, scripts = {}, attributes = {} }, Widget)
    if template == "SecureActionButtonTemplate" then
        widget.protected = true
        parent.protected = true
    end
    return widget
end
function Widget:CreateTexture() return NewWidget("Texture", self) end
function Widget:CreateFontString() return NewWidget("FontString", self) end
function Widget:SetScript(name, fn) self.scripts[name] = fn end
function Widget:SetShown(shown) self.shown = shown and true or false end
function Widget:Show() self.shown = true end
function Widget:Hide() self.shown = false end
function Widget:IsShown() return self.shown end
function Widget:SetAttribute(name, value) self.attributes[name] = value end
function Widget:SetText(text) self.text = tostring(text) end
function Widget:SetTexture(texture) assert(texture ~= nil, "SetTexture with nil"); self.texture = texture end
function Widget:SetDesaturated(desaturated) self.desaturated = desaturated end
function Widget:SetSize(width, height) assert(width > 0 and height > 0, "bad size"); self.width, self.height = width, height end
function Widget:SetPoint(...) assert(select("#", ...) >= 1, "SetPoint without arguments"); self.point = { ... } end
function Widget:GetPoint() return "TOPLEFT", UIParent, "TOPLEFT", 120, -340 end
function Widget:StartMoving() self.moving = true end
function Widget:StopMovingOrSizing() self.moving = false end
function Widget:SetCooldown(start, duration)
    assert(type(start) == "number" and type(duration) == "number", "bad cooldown")
    self.cooldownStart = start
end
function Widget:RegisterEvent(event) self.events = self.events or {}; self.events[event] = true end
function Widget:SetItemByID(itemID) assert(type(itemID) == "number", "tooltip without an item"); self.itemID = itemID end

local frames = {}
function CreateFrame(kind, _, parent, template)
    local frame = NewWidget(kind, parent, template)
    frames[#frames + 1] = frame
    return frame
end
UIParent = NewWidget("Frame")
GameTooltip = NewWidget("GameTooltip")
function GameTooltip_Hide() end
function InCombatLockdown() return inCombat end
local shiftDown = false
function IsShiftKeyDown() return shiftDown end
function GetLocale() return "deDE" end
function print(...) printed[#printed + 1] = table.concat({ ... }, " ") end
SlashCmdList = {}
Enum = { BagIndex = { Backpack = 0, Bag_4 = 4 }, ItemClass = { Consumable = 0 } }

-- The item database. loaded = false models data the client has not received yet.
local CONSUMABLE, WEAPON = 0, 2
local itemData = {
    [100] = { class = CONSUMABLE, sub = 5, level = 45, spell = "Essen", tip = "Benutzen: Stellt Gesundheit wieder her. Ihr werdet satt und erhaltet Ausdauer." },
    [101] = { class = CONSUMABLE, sub = 5, level = 35, spell = "Essen", tip = "Benutzen: Stellt Gesundheit wieder her." },
    [102] = { class = CONSUMABLE, sub = 5, level = 25, spell = "Essen", tip = "Benutzen: Stellt Gesundheit wieder her." },
    [103] = { class = CONSUMABLE, sub = 5, level = 35, spell = "Trinken", tip = "Benutzen: Stellt Mana wieder her." },
    [104] = { class = CONSUMABLE, sub = 1, level = 30, spell = "Heiltrank", tip = "Benutzen: Heilt." },
    [105] = { class = CONSUMABLE, sub = 7, level = 20, spell = "Erste Hilfe", tip = "Benutzen: Heilt." },
    [106] = { class = CONSUMABLE, sub = 0, level = 20, spell = "Sprengstoff", tip = "Benutzen: Explodiert." },
    [107] = { class = WEAPON, sub = 7, level = 60 },
    [108] = { class = CONSUMABLE, sub = 2, level = 40, spell = "Elixier", tip = "Benutzen: Mehr Beweglichkeit.", loaded = false },
    [109] = { class = CONSUMABLE, sub = 4, level = 15, spell = "Rolle", tip = "Benutzen: Mehr Ausdauer." },
}
-- bags[bag][slot] = { itemID, count }
local bags = {
    [0] = { { 104, 5 }, { 107, 1 }, { 101, 20 }, { 100, 3 } },
    [1] = { { 103, 10 }, { 105, 8 }, { 106, 2 }, { 101, 4 }, { 108, 1 } },
    [2] = { { 102, 7 } },
    [3] = {},
    [4] = {},
}

C_Container = {
    GetContainerNumSlots = function(bag) return #bags[bag] end,
    GetContainerItemID = function(bag, slot) return bags[bag][slot][1] end,
    GetItemCooldown = function(itemID) return itemID == 104 and 500 or 0, itemID == 104 and 120 or 0, 1 end,
}
C_Item = {
    GetItemInfoInstant = function(itemID)
        local item = itemData[itemID]
        return itemID, "", "", "", 9000 + itemID, item.class, item.sub
    end,
    GetItemInfo = function(itemID)
        local item = itemData[itemID]
        if item.loaded == false then return end
        return "Item " .. itemID, "", 1, item.level
    end,
    GetItemSpell = function(itemID) return itemData[itemID].spell end,
    GetItemCount = function(itemID)
        local total = 0
        for bag = 0, 4 do
            for _, slot in ipairs(bags[bag]) do
                if slot[1] == itemID then total = total + slot[2] end
            end
        end
        return total
    end,
}
C_Spell = { GetSpellName = function(spellID) return ({ [430] = "Trinken", [19705] = "Satt" })[spellID] end }
C_TooltipInfo = {
    GetItemByID = function(itemID) return { lines = { { leftText = "Item " .. itemID }, { leftText = itemData[itemID].tip }, {} } } end,
}

local settings = {}
Settings = {
    RegisterVerticalLayoutCategory = function() return { GetID = function() return 7 end } end,
    RegisterAddOnSetting = function(_, _, key, tbl, varType, name, default)
        assert(type(default) == varType and type(name) == "string", "bad setting " .. key)
        local setting = { name = name }
        function setting:SetValueChangedCallback(fn) self.callback = fn end
        function setting:SetValue(value) tbl[key] = value; self.callback(self, value) end
        settings[key] = setting
        return setting
    end,
    CreateCheckbox = function(_, setting, tooltip) assert(setting and type(tooltip) == "string") end,
    CreateSliderOptions = function(low, high, step)
        assert(low < high and step > 0, "bad slider range")
        return { SetLabelFormatter = function() end }
    end,
    CreateSlider = function(_, setting, options, tooltip) assert(setting and options and type(tooltip) == "string") end,
    RegisterAddOnCategory = function() end,
    OpenToCategory = function(id) settings.opened = id end,
}
MinimalSliderWithSteppersMixin = { Label = { Right = 1 } }

-- Load the addon the way the client does: every file in TOC order gets (addonName, ns)
local ns = {}
for line in io.lines("addons/Breakfast/Breakfast.toc") do
    if line:match("%.lua$") then
        assert(loadfile("addons/Breakfast/" .. line))("Breakfast", ns)
    end
end

local events, bar, handle
for _, frame in ipairs(frames) do
    if frame.scripts.OnEvent then events = frame end
    if frame.scripts.OnDragStart then handle = frame end
end
bar = handle.parent
local function Fire(event, ...) events.scripts.OnEvent(events, event, ...) end
local function Shown()
    local ids = {}
    for _, frame in ipairs(frames) do
        if frame.protected and frame ~= bar and frame.shown then
            ids[#ids + 1] = frame.attributes.item .. "x" .. frame.count.text .. (frame.icon.desaturated and "!" or "")
        end
    end
    return table.concat(ids, " ")
end
local function ButtonFor(itemID)
    for _, frame in ipairs(frames) do
        if frame.shown and frame.attributes.item == "item:" .. itemID then return frame end
    end
end

-- Every event the addon handles is registered, and a foreign ADDON_LOADED is ignored
for _, event in ipairs({ "ADDON_LOADED", "PLAYER_ENTERING_WORLD", "BAG_UPDATE_DELAYED", "BAG_UPDATE_COOLDOWN",
    "GET_ITEM_INFO_RECEIVED", "PLAYER_REGEN_DISABLED", "PLAYER_REGEN_ENABLED" }) do
    assert(events.events[event] and events[event], "event not wired: " .. event)
end
Fire("ADDON_LOADED", "SomeOtherAddon")
assert(BreakfastDB == nil)

-- A saved position is restored, broken values are repaired
BreakfastDB = { size = 999, pos = { "TOPLEFT", "TOPLEFT", 50, -60 } }
Fire("ADDON_LOADED", "Breakfast")
assert(BreakfastDB.size == 56 and bar.point[1] == "TOPLEFT" and bar.point[4] == 50 and bar.point[5] == -60)
assert(settings.drink.name == "Getränke" and settings.locked.name == "Position sperren", "German names missing")
settings.size:SetValue(36)

-- First scan: groups in order, stacks added up, the weapon, the explosive and the unloaded elixir left out
Fire("PLAYER_ENTERING_WORLD")
assert(Shown() == "item:100x3 item:101x24 item:102x7 item:103x10 item:104x5 item:105x8", Shown())
-- Six buttons, five spacings and a gap before each of the four later groups
assert(bar.width == 6 * 36 + 5 * 2 + 4 * 8 and bar.height == 36)
local potion = ButtonFor(104)
-- Only the left button uses the item, so a right click can never eat or drink by accident
assert(potion.attributes.type1 == "item" and potion.attributes.type == nil and potion.attributes.useOnKeyDown == false)
assert(potion.icon.texture == 9104 and potion.cooldown.cooldownStart == 500 and potion.width == 36)

-- The elixir's data arrives. Other items' data does not trigger a rescan.
itemData[108].loaded = nil
Fire("GET_ITEM_INFO_RECEIVED", 555)
assert(not ButtonFor(108))
Fire("GET_ITEM_INFO_RECEIVED", 108)
assert(Shown() == "item:100x3 item:101x24 item:102x7 item:103x10 item:104x5 item:108x1 item:105x8", Shown())

-- Tooltip and slash command
potion.scripts.OnEnter(potion)
assert(GameTooltip.itemID == 104)
SlashCmdList.BREAKFAST("")
assert(settings.opened == 7 and SLASH_BREAKFAST1 == "/breakfast")

-- Looting out of combat adds a button at once
table.insert(bags[3], { 109, 2 })
Fire("BAG_UPDATE_DELAYED")
assert(Shown() == "item:100x3 item:101x24 item:102x7 item:103x10 item:104x5 item:108x1 item:105x8 item:109x2", Shown())

-- In combat: a used up potion stays greyed out, new loot waits, settings wait, dragging is refused.
-- The widget stub fails the test if a protected frame is touched here.
Fire("PLAYER_REGEN_DISABLED")
inCombat = true
table.remove(bags[0], 1)
table.insert(bags[3], { 102, 3 })
bags[1][5] = { 100, 1 }
Fire("BAG_UPDATE_DELAYED")
Fire("BAG_UPDATE_COOLDOWN")
assert(Shown() == "item:100x4 item:101x24 item:102x10 item:103x10 item:104x0! item:108x0! item:105x8 item:109x2", Shown())
settings.drink:SetValue(false)
settings.perRow:SetValue(3)
assert(ButtonFor(103), "a setting changed the bar in combat")
handle.scripts.OnDragStart(handle)
-- The mouse release still fires after a refused drag
handle.scripts.OnDragStop(handle)
assert(not bar.moving and printed[#printed] == "Breakfast: Die Leiste wird nach dem Kampf aktualisiert.")

-- After the fight everything catches up: used up items gone, drinks off, three per row
inCombat = false
Fire("PLAYER_REGEN_ENABLED")
assert(Shown() == "item:100x4 item:101x24 item:102x10 item:105x8 item:109x2", Shown())
assert(bar.height == 2 * 36 + 2 and ButtonFor(105).point[5] == -38 and ButtonFor(105).point[4] == 0)
settings.drink:SetValue(true)
settings.perRow:SetValue(12)
assert(ButtonFor(103))

-- Dragging saves the position, locking hides the handle
handle.scripts.OnDragStart(handle)
assert(bar.moving)
handle.scripts.OnDragStop(handle)
assert(not bar.moving and BreakfastDB.pos[1] == "TOPLEFT" and BreakfastDB.pos[3] == 120 and BreakfastDB.pos[4] == -340)
settings.locked:SetValue(true)
assert(handle.shown == false)
settings.locked:SetValue(false)
assert(handle.shown == true)

-- Shift + right click hides an item for good. Other clicks do not.
local bandage = ButtonFor(105)
bandage.scripts.PostClick(bandage, "RightButton")
bandage.scripts.PostClick(bandage, "LeftButton")
shiftDown = true
bandage.scripts.PostClick(bandage, "LeftButton")
assert(ButtonFor(105) and next(BreakfastDB.hidden) == nil)
bandage.scripts.PostClick(bandage, "RightButton")
assert(not ButtonFor(105) and BreakfastDB.hidden[105])
assert(printed[#printed] == "Breakfast: Item 105 ist ausgeblendet. /breakfast reset zeigt alle ausgeblendeten Gegenstände wieder.")
Fire("BAG_UPDATE_DELAYED")
assert(not ButtonFor(105))

-- Hiding in combat takes effect after the fight
inCombat = true
local scroll = ButtonFor(109)
scroll.scripts.PostClick(scroll, "RightButton")
assert(ButtonFor(109) and BreakfastDB.hidden[109])
inCombat = false
Fire("PLAYER_REGEN_ENABLED")
assert(not ButtonFor(109))
shiftDown = false

-- /breakfast reset brings hidden items back
SlashCmdList.BREAKFAST(" Reset ")
assert(ButtonFor(105) and ButtonFor(109) and next(BreakfastDB.hidden) == nil)

-- Empty bags: no buttons, the bar keeps a valid size
for bag = 0, 4 do bags[bag] = {} end
Fire("BAG_UPDATE_DELAYED")
assert(Shown() == "" and bar.width == 1 and bar.height == 1)

-- A food item whose tooltip loads late moves to buff food on a later scan
itemData[102].tip = nil
bags[0] = { { 102, 1 } }
C_Spell.GetSpellName = function() end
Fire("BAG_UPDATE_DELAYED")
assert(Shown() == "item:102x1")
C_Spell.GetSpellName = function(spellID) return ({ [430] = "Trinken", [19705] = "Satt" })[spellID] end
itemData[102].tip = "Ihr werdet satt."
bags[0][2] = { 101, 1 }
Fire("BAG_UPDATE_DELAYED")
assert(Shown() == "item:102x1 item:101x1", Shown())

-- print is stubbed above, so report through io.write
io.write("bar_test: all passed\n")
