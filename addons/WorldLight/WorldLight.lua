local addonName, ns = ...

local TICK_SECONDS = 10

ns.settings = {}

-- Child of WorldFrame at the lowest strata: above the 3D world, below the UI
local overlay = CreateFrame("Frame", nil, WorldFrame)
overlay:SetAllPoints(WorldFrame)
overlay:SetFrameStrata("BACKGROUND")
overlay:SetFrameLevel(0)

local dark = overlay:CreateTexture(nil, "BACKGROUND")
dark:SetAllPoints()
dark:SetColorTexture(0, 0, 0)
dark:SetAlpha(0)

local light = overlay:CreateTexture(nil, "BACKGROUND")
light:SetAllPoints()
light:SetColorTexture(1, 1, 1)
light:SetBlendMode("ADD")
light:SetAlpha(0)

-- The server's phase, kept apart from ns.isDay so custom times never record a server flip
local serverIsDay

local function Update()
    local db = ns.db
    local now, flip = GetServerTime(), db.lastFlip
    serverIsDay = C_DateAndTime.IsDayTime()
    ns.isDay = serverIsDay
    if db.customTimes then
        local hour, minute = GetGameTime()
        local minutes
        ns.isDay, minutes = ns.ClockPhase(hour * 60 + minute, db)
        -- The clock says when the phase started, so the fade is right even after a login
        flip = { time = now - minutes * 60, isDay = ns.isDay }
    end
    ns.value = db.enabled and ns.ComputeValue(ns.isDay, now, flip, db) or 0
    local darkAlpha, lightAlpha = ns.ToAlphas(ns.value)
    dark:SetAlpha(darkAlpha)
    light:SetColorTexture(ns.ParseColor(db.lightColor))
    light:SetAlpha(lightAlpha)
end

-- Indoors and in instances there is no day or night, so by default the tint fades out there
local shown, shownTarget = 1, 1

local function FadeStep(self, elapsed)
    local seconds = ns.db.placeFadeSeconds
    local step = seconds > 0 and elapsed / seconds or 1
    if shown < shownTarget then
        shown = math.min(shownTarget, shown + step)
    else
        shown = math.max(shownTarget, shown - step)
    end
    self:SetAlpha(shown)
    if shown == shownTarget then
        self:SetScript("OnUpdate", nil)
    end
end

local function UpdatePlace()
    shownTarget = ns.ShowsTint(IsIndoors(), IsInInstance(), ns.db) and 1 or 0
    if shown ~= shownTarget then
        overlay:SetScript("OnUpdate", FadeStep)
    end
end

local events = CreateFrame("Frame")
events:SetScript("OnEvent", function(self, event, ...)
    self[event](self, ...)
end)

function events:ADDON_LOADED(name)
    if name ~= addonName then return end
    WorldLightDB = ns.Sanitize(WorldLightDB or {})
    ns.db = WorldLightDB
    ns.RegisterSettings(ns.db, function()
        Update()
        UpdatePlace()
    end)
    self:UnregisterEvent("ADDON_LOADED")
end

function events:PLAYER_LOGIN()
    Update()
    -- Also re-checks the location in case no event fired for a building transition
    C_Timer.NewTicker(TICK_SECONDS, function()
        Update()
        UpdatePlace()
    end)
end

function events:DIEL_CYCLE_CHANGED(isDayTime)
    -- Only a real change starts a fade, in case the event repeats the current state
    if serverIsDay ~= nil and isDayTime ~= serverIsDay then
        local hour, minute = GetGameTime()
        ns.db.lastFlip = { time = GetServerTime(), isDay = isDayTime, realmTime = ("%02d:%02d"):format(hour, minute) }
    end
    Update()
end

events.PLAYER_ENTERING_WORLD = UpdatePlace
events.ZONE_CHANGED = UpdatePlace
events.ZONE_CHANGED_INDOORS = UpdatePlace
events.ZONE_CHANGED_NEW_AREA = UpdatePlace
-- Walking into a building changes no zone. These two fire there, the minimap uses them too.
events.NEW_WMO_CHUNK = UpdatePlace
events.MINIMAP_UPDATE_ZOOM = UpdatePlace

for event in pairs({
    ADDON_LOADED = true, PLAYER_LOGIN = true, DIEL_CYCLE_CHANGED = true, PLAYER_ENTERING_WORLD = true,
    ZONE_CHANGED = true, ZONE_CHANGED_INDOORS = true, ZONE_CHANGED_NEW_AREA = true,
    NEW_WMO_CHUNK = true, MINIMAP_UPDATE_ZOOM = true,
}) do
    events:RegisterEvent(event)
end

local function PrintStatus()
    local hour, minute = GetGameTime()
    local custom = ns.db.customTimes
    local flip = ns.db.lastFlip
    local indoors, inInstance = IsIndoors(), IsInInstance()
    print(("WorldLight: %s, realm time %02d:%02d, %s (%s), value %.0f, %s%s%s"):format(
        ns.db.enabled and "on" or "off", hour, minute, ns.isDay and "day" or "night",
        custom and ("night %d:00 to %d:00"):format(ns.db.nightStart, ns.db.dayStart) or "server", ns.value or 0,
        inInstance and "in an instance" or indoors and "indoors" or "outdoors",
        ns.ShowsTint(indoors, inInstance, ns.db) and "" or ", tint off here",
        flip and flip.realmTime and (", last server switch to %s at %s"):format(flip.isDay and "day" or "night", flip.realmTime) or ""))
end

SLASH_WORLDLIGHT1 = "/worldlight"
SlashCmdList.WORLDLIGHT = function(msg)
    local cmd, arg = msg:lower():match("^%s*(%S*)%s*(.-)%s*$")
    local number = tonumber(arg)
    if cmd == "" then
        Settings.OpenToCategory(ns.category:GetID())
    elseif cmd == "on" or cmd == "off" then
        ns.settings.enabled:SetValue(cmd == "on")
    elseif (cmd == "day" or cmd == "night") and number then
        ns.settings[cmd]:SetValue(ns.Clamp(cmd, math.floor(number + 0.5)))
    elseif cmd == "status" then
        PrintStatus()
    else
        print("WorldLight: /worldlight [on | off | day <-100..100> | night <-100..100> | status]")
    end
end
