-- Run ClearMap's Lua in a stubbed WoW environment to catch runtime errors in our own code.
-- Usage: luatex --luaonly tools/wowmock.lua <addon_dir>
-- The stubs only model what ClearMap touches. Real API mismatches still need an in-game test.
local addonDir = arg[1] or "addons/ClearMap"
unpack = unpack or table.unpack
local calls = {}
local function log(what) calls[#calls + 1] = what end

-- Any widget: unknown methods are no-ops, the ones ClearMap reads return sensible values.
local Widget = {}
Widget.__index = function(self, key)
    local v = rawget(Widget, key)
    if v ~= nil then return v end
    if type(key) == "string" and key:match("^%u") then -- WoW methods are CamelCase, data fields are not
        return function() end
    end
end
local function NewWidget(kind, parent)
    return setmetatable({ kind = kind, parent = parent, shown = true, level = 5, scripts = {}, width = 140, height = 140 }, Widget)
end
function Widget:CreateTexture() return NewWidget("Texture", self) end
function Widget:CreateMaskTexture() return NewWidget("MaskTexture", self) end
function Widget:CreateFontString() return NewWidget("FontString", self) end
function Widget:SetScript(name, fn) self.scripts[name] = fn end
function Widget:GetScript(name) return self.scripts[name] end
function Widget:SetShown(v) self.shown = v and true or false end
function Widget:Show() self.shown = true end
function Widget:Hide() self.shown = false end
function Widget:IsShown() return self.shown end
function Widget:GetFrameLevel() return self.level end
function Widget:SetFrameLevel(l) self.level = l end
function Widget:GetWidth() return self.width end
function Widget:GetHeight() return self.height end
function Widget:GetParent() return self.parent end
function Widget:RegisterEvent(e) self.events = self.events or {}; self.events[e] = true end
function Widget:SetText(t) assert(type(t) == "string", "SetText needs a string"); self.text = t end
function Widget:SetTexture(path) assert(path ~= nil, "SetTexture with nil"); self.texture = path end
function Widget:SetMaskTexture(path) assert(path ~= nil, "SetMaskTexture with nil"); self.mask = path end
function Widget:SetPoint(...) local n = select("#", ...); assert(n >= 1, "SetPoint without arguments") end
function Widget:GetStringWidth() assert(self.text, "measuring a string before SetText"); return 6 * #self.text end
function Widget:GetStringHeight() return 12 end
function Widget:SetFont(path, size, flags) assert(type(path) == "string" and type(size) == "number" and type(flags) == "string", "bad SetFont arguments") end
function Widget:SetColorTexture(r, g, b, a) assert(type(r) == "number" and (a == nil or (a >= 0 and a <= 1)), "bad color") end

function CreateFrame(kind, name, parent, template) return NewWidget(kind, parent) end
function hooksecurefunc(tbl, name, hook)
    local original = tbl[name]
    assert(type(original) == "function", "hooksecurefunc on missing function " .. tostring(name))
    tbl[name] = function(...) local r = { original(...) }; hook(...); return unpack(r) end
end
function issecretvalue() return false end
function IsIndoors() return false end
function print(...) end
SlashCmdList = {}
UIParent = NewWidget("Frame")

-- Map APIs: a 1002 x 668 zone canvas, the player at the center of Durotar.
C_Map = {
    GetMapArtLayers = function() return { { layerWidth = 1002, layerHeight = 668, tileWidth = 256, tileHeight = 256 } } end,
    GetAreaInfo = function(id) return "Area " .. id end,
    GetBestMapForUnit = function() return 1411 end,
    GetPlayerMapPosition = function() return { GetXY = function() return 0.55, 0.45 end } end,
}
C_CVar = { GetCVarBool = function() return false end }
C_Texture = { GetAtlasInfo = function(name) return name == "ui-hud-minimap-frame-generic-mask" and {} or nil end }
GameTooltip = NewWidget("GameTooltip")
GameFontNormal = NewWidget("Font")
function GameFontNormal:GetFont() return "Fonts/FRIZQT__.TTF", 12, "" end
MinimalSliderWithSteppersMixin = { Label = { Right = 1 } }

local function Pool(items)
    return { EnumerateActive = function() local i = 0; return function() i = i + 1; return items[i] end end }
end
local layer = NewWidget("Frame")
layer.detailTilePool = Pool({ NewWidget("Texture"), NewWidget("Texture") })
local explorationPin = NewWidget("Frame")
function explorationPin:RefreshOverlays() log("RefreshOverlays") end
WorldMapFrame = NewWidget("Frame")
WorldMapFrame.mapID = 1411
WorldMapFrame.detailLayerPool = Pool({ layer })
WorldMapFrame.ScrollContainer = NewWidget("ScrollFrame")
function WorldMapFrame:GetMapID() return self.mapID end
function WorldMapFrame:GetCanvas() return NewWidget("Frame") end
function WorldMapFrame:GetCanvasScale() return 0.8 end
function WorldMapFrame:GetCanvasZoomPercent() return 0.5 end
function WorldMapFrame:RefreshDetailLayers() log("RefreshDetailLayers") end
function WorldMapFrame:OnCanvasScaleChanged() log("OnCanvasScaleChanged") end
function WorldMapFrame:EnumeratePinsByTemplate() local done = false; return function() if not done then done = true; return explorationPin end end end

Minimap = NewWidget("Minimap", NewWidget("Frame"))
function Minimap:GetZoom() return 2 end

-- Settings and menus.
local settingObjects = {}
Settings = {
    RegisterVerticalLayoutCategory = function(name) return { name = name, GetID = function() return 1 end } end,
    RegisterAddOnSetting = function(category, variable, key, tbl, varType, name, default)
        assert(type(default) == varType, "default type mismatch for " .. key)
        local s = { key = key }
        function s:SetValueChangedCallback(fn) self.callback = fn end
        function s:SetValue(v) assert(type(v) == varType, "wrong type for " .. key); tbl[key] = v; if self.callback then self.callback(self, v) end end
        function s:GetValue() return tbl[key] end
        settingObjects[key] = s
        return s
    end,
    CreateCheckbox = function(category, setting, tooltip) assert(setting and tooltip) end,
    CreateDropdown = function(category, setting, options, tooltip)
        local data = options()
        assert(#data == 3, "dropdown should have 3 options")
    end,
    CreateControlTextContainer = function()
        local c = { items = {} }
        function c:Add(value, label) self.items[#self.items + 1] = { value = value, label = label } end
        function c:GetData() return self.items end
        return c
    end,
    RegisterAddOnCategory = function() end,
    CreateSliderOptions = function(lo, hi, step)
        assert(lo < hi and step > 0, "bad slider range")
        return { SetLabelFormatter = function() end }
    end,
    CreateSlider = function(category, setting, options, tooltip) assert(setting and options and tooltip) end,
}
local menuItems = {}
MenuUtil = {
    CreateContextMenu = function(owner, generator)
        local root = {}
        function root:CreateTitle(text) menuItems[#menuItems + 1] = { "title", text } end
        function root:CreateCheckbox(text, isSelected, setSelected) menuItems[#menuItems + 1] = { "checkbox", text, isSelected, setSelected } end
        function root:CreateRadio(text, isSelected, setSelected) menuItems[#menuItems + 1] = { "radio", text, isSelected, setSelected } end
        generator(owner, root)
    end,
}

-- Record every frame the addon creates, so the test can reach its event frame, button, pins and minimap driver.
local eventFrames = {}
local realCreate = CreateFrame
CreateFrame = function(...) local f = realCreate(...); eventFrames[#eventFrames + 1] = f; return f end

-- Load the addon the way the client does, in TOC order: every file gets (addonName, ns).
local ns = {}
for _, file in ipairs({ "Tiles/Tiles.lua", "Minimap.lua", "ClearMap.lua" }) do
    local chunk = assert(loadfile(addonDir .. "/" .. file))
    chunk("ClearMap", ns)
end
assert(next(ns.tiles), "Tiles.lua defined no maps")
local eventFrame
for _, f in ipairs(eventFrames) do if f.scripts.OnEvent then eventFrame = f end end
assert(eventFrame, "no event frame")

ClearMapDB = { enabled = true, labels = true } -- an old 1.x setting, to test the migration
local onEvent = eventFrame.scripts.OnEvent
onEvent(eventFrame, "ADDON_LOADED", "ClearMap")
assert(ClearMapDB.labels == nil and ClearMapDB.areaNames == 1 and ClearMapDB.labelBackground == false and ClearMapDB.version == 2,
    "settings migration failed")
onEvent(eventFrame, "PLAYER_LOGIN")

-- World map refresh with every label mode and option.
for _, mode in ipairs({ 0, 1, 2 }) do
    ns.settings.areaNames:SetValue(mode)
    WorldMapFrame:RefreshDetailLayers()
    WorldMapFrame:OnCanvasScaleChanged()
end
ns.settings.labelBackgroundOpacity:SetValue(80)
for _, key in ipairs({ "labelBackground", "cities", "caves", "minimap", "enabled" }) do
    ns.settings[key]:SetValue(false)
    WorldMapFrame:RefreshDetailLayers()
    ns.settings[key]:SetValue(true)
end
explorationPin:RefreshOverlays()

-- A map without tiles.
WorldMapFrame.mapID = 1414
WorldMapFrame:RefreshDetailLayers()
WorldMapFrame.mapID = 1411
WorldMapFrame:RefreshDetailLayers()

-- The map menu: open it, read every item, click every item.
local button
for _, f in ipairs(eventFrames) do if f.kind == "Button" and f.scripts.OnClick then button = f end end
assert(button, "no map button")
button.scripts.OnClick(button)
assert(#menuItems >= 9, "menu has too few items: " .. #menuItems)
for _, item in ipairs(menuItems) do
    if item[1] ~= "title" then
        assert(type(item[3]()) ~= "nil", "isSelected returned nil for " .. item[2])
        item[4]()
        item[4]()
    end
end

-- Cave pin tooltip.
for _, f in ipairs(eventFrames) do
    if f.scripts.OnEnter and f.name == nil then f.name = "x" end
end
for _, f in ipairs(eventFrames) do
    if f.scripts.OnEnter then f.scripts.OnEnter(f); f.scripts.OnLeave(f) end
end

-- Minimap: run the per-frame update, then a mask change from a minimap addon, then indoors.
local driver
for _, f in ipairs(eventFrames) do if f.scripts.OnUpdate and f.parent == nil and f ~= eventFrame then driver = f end end
assert(driver, "no minimap driver")
driver.scripts.OnUpdate(driver, 0.016)
assert(Minimap.mask == "Interface\\AddOns\\ClearMap\\Media\\blank", "minimap terrain not hidden: " .. tostring(Minimap.mask))
Minimap:SetMaskTexture(130937) -- what EllesmereUI sets for a square minimap
assert(Minimap.mask == "Interface\\AddOns\\ClearMap\\Media\\blank", "blank mask not re-applied after an addon changed it")
IsIndoors = function() return true end
driver.scripts.OnUpdate(driver, 0.016)
assert(Minimap.mask == 130937, "indoors should restore the addon's own mask, got " .. tostring(Minimap.mask))
IsIndoors = function() return false end
driver.scripts.OnUpdate(driver, 0.016)

-- Slash command.
SlashCmdList.CLEARMAP("")
SlashCmdList.CLEARMAP("")

print = io.write
io.write("ok: ClearMap ran through load, settings migration, world map refresh in every mode, menu, minimap and slash command\n")
