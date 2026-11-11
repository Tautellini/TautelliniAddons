local addonName, ns = ...

-- Spells whose localized names split the Food & Drink items, because the game has no field for it.
-- shortcut: Classic spell IDs and tooltip wording, items fall back to plain food if a name is missing. Upgrade to a learned cache if the split is wrong in game.
local DRINK_SPELL, WELL_FED_SPELL = 430, 19705

local FIRST_BAG = Enum.BagIndex.Backpack or 0
local LAST_BAG = Enum.BagIndex.Bag_4 or 4

-- The buttons are protected, so the bar counts as protected in combat too.
-- Everything that moves, sizes, shows or hides them waits for the fight to end.
local bar = CreateFrame("Frame", nil, UIParent)
bar:SetSize(1, 1)
bar:SetMovable(true)
bar:SetClampedToScreen(true)

local handle = CreateFrame("Frame", nil, bar)
handle:SetSize(70, 14)
handle:SetPoint("BOTTOMLEFT", bar, "TOPLEFT", 0, 2)
handle:EnableMouse(true)
handle:RegisterForDrag("LeftButton")
local handleBack = handle:CreateTexture(nil, "BACKGROUND")
handleBack:SetAllPoints()
handleBack:SetColorTexture(0, 0, 0, 0.6)
local handleText = handle:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
handleText:SetPoint("CENTER")
handleText:SetText("Breakfast")

local function StopMoving()
    bar:StopMovingOrSizing()
    local point, _, relativePoint, x, y = bar:GetPoint(1)
    if point then
        ns.db.pos = { point, relativePoint, x, y }
    end
end

handle:SetScript("OnDragStart", function()
    if InCombatLockdown() then
        print(ns.L.combat)
        return
    end
    bar:StartMoving()
end)
handle:SetScript("OnDragStop", StopMoving)

-- itemID -> { id, group, level, icon }, or false for items the bar never shows
local known = {}
-- itemIDs whose data the client has not loaded yet
local pending = {}

local function IsBuffFood(itemID, wellFed)
    local data = wellFed and C_TooltipInfo.GetItemByID(itemID)
    for _, line in ipairs(data and data.lines or {}) do
        if type(line.leftText) == "string" and line.leftText:lower():find(wellFed, 1, true) then
            return true
        end
    end
    return false
end

local function Classify(itemID)
    if known[itemID] ~= nil then
        return known[itemID]
    end
    local _, _, _, _, icon, classID, subclassID = C_Item.GetItemInfoInstant(itemID)
    if classID ~= Enum.ItemClass.Consumable then
        known[itemID] = false
        return false
    end
    local _, _, _, level = C_Item.GetItemInfo(itemID)
    if not level then
        pending[itemID] = true
        return false
    end
    pending[itemID] = nil
    local wellFed = C_Spell.GetSpellName(WELL_FED_SPELL)
    local drink = C_Spell.GetSpellName(DRINK_SPELL)
    local group = ns.GroupOf(subclassID, drink ~= nil and C_Item.GetItemSpell(itemID) == drink,
        IsBuffFood(itemID, wellFed and wellFed:lower()))
    local item = group and { id = itemID, group = group, level = level, icon = icon } or false
    -- Plain food is checked again on the next scan, in case the spell or tooltip was not loaded yet
    if group ~= "food" then
        known[itemID] = item
    end
    return item
end

local function Scan()
    local items, seen = {}, {}
    for bag = FIRST_BAG, LAST_BAG do
        for slot = 1, C_Container.GetContainerNumSlots(bag) do
            local itemID = C_Container.GetContainerItemID(bag, slot)
            if itemID and not seen[itemID] then
                seen[itemID] = true
                local item = Classify(itemID)
                if item then
                    items[#items + 1] = item
                end
            end
        end
    end
    return items
end

local buttons = {}

local function NewButton()
    local button = CreateFrame("Button", nil, bar, "SecureActionButtonTemplate")
    button:SetAttribute("type", "item")
    -- Use on release whatever the player's key down setting says, so one registration is enough
    button:SetAttribute("useOnKeyDown", false)
    button:RegisterForClicks("LeftButtonUp")
    button:SetHighlightTexture("Interface\\Buttons\\ButtonHilight-Square", "ADD")

    button.icon = button:CreateTexture(nil, "BACKGROUND")
    button.icon:SetAllPoints()
    button.cooldown = CreateFrame("Cooldown", nil, button, "CooldownFrameTemplate")
    button.cooldown:SetAllPoints()
    button.count = button:CreateFontString(nil, "OVERLAY", "NumberFontNormal")
    button.count:SetPoint("BOTTOMRIGHT", -2, 2)

    button:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetItemByID(self.itemID)
        GameTooltip:Show()
    end)
    button:SetScript("OnLeave", GameTooltip_Hide)
    buttons[#buttons + 1] = button
    return button
end

-- Counts and cooldowns are not protected, so these two also run in combat
local function RefreshCounts()
    for _, button in ipairs(buttons) do
        if button.itemID then
            local count = C_Item.GetItemCount(button.itemID)
            button.count:SetText(count)
            button.icon:SetDesaturated(count == 0)
        end
    end
end

local function RefreshCooldowns()
    for _, button in ipairs(buttons) do
        if button.itemID then
            local start, duration = C_Container.GetItemCooldown(button.itemID)
            if start then
                button.cooldown:SetCooldown(start, duration)
            end
        end
    end
end

local function Rebuild()
    handle:SetShown(not ns.db.locked)
    if InCombatLockdown() then
        -- PLAYER_REGEN_ENABLED rebuilds. Until then used up items stay greyed out with count 0.
        RefreshCounts()
        return
    end
    local db = ns.db
    local list, width, height = ns.Arrange(Scan(), db)
    for index, item in ipairs(list) do
        local button = buttons[index] or NewButton()
        button.itemID = item.id
        button:SetAttribute("item", "item:" .. item.id)
        button.icon:SetTexture(item.icon)
        button:SetSize(db.size, db.size)
        button:ClearAllPoints()
        button:SetPoint("TOPLEFT", bar, "TOPLEFT", item.x, item.y)
        button:Show()
    end
    for index = #list + 1, #buttons do
        buttons[index].itemID = nil
        buttons[index]:Hide()
    end
    bar:SetSize(math.max(width, 1), math.max(height, 1))
    RefreshCounts()
    RefreshCooldowns()
end

local events = CreateFrame("Frame")
events:SetScript("OnEvent", function(self, event, ...)
    self[event](self, ...)
end)

function events:ADDON_LOADED(name)
    if name ~= addonName then return end
    BreakfastDB = ns.Sanitize(BreakfastDB or {})
    ns.db = BreakfastDB
    local pos = ns.db.pos
    if pos then
        bar:SetPoint(pos[1], UIParent, pos[2], pos[3], pos[4])
    else
        bar:SetPoint("CENTER")
    end
    ns.RegisterSettings(ns.db, Rebuild)
    self:UnregisterEvent("ADDON_LOADED")
end

function events:GET_ITEM_INFO_RECEIVED(itemID)
    if pending[itemID] then
        Rebuild()
    end
end

function events:PLAYER_REGEN_DISABLED()
    -- Fires just before the lockdown, so a drag in progress can still end cleanly
    StopMoving()
end

events.PLAYER_ENTERING_WORLD = Rebuild
events.BAG_UPDATE_DELAYED = Rebuild
events.PLAYER_REGEN_ENABLED = Rebuild
events.BAG_UPDATE_COOLDOWN = RefreshCooldowns

for _, event in ipairs({
    "ADDON_LOADED", "PLAYER_ENTERING_WORLD", "BAG_UPDATE_DELAYED", "BAG_UPDATE_COOLDOWN",
    "GET_ITEM_INFO_RECEIVED", "PLAYER_REGEN_DISABLED", "PLAYER_REGEN_ENABLED",
}) do
    events:RegisterEvent(event)
end

SLASH_BREAKFAST1 = "/breakfast"
SlashCmdList.BREAKFAST = function()
    Settings.OpenToCategory(ns.category:GetID())
end
