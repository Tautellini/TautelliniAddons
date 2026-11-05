local addonName, ns = ...

local TICK_SECONDS = 10
local INDOOR_FADE_SECONDS = 1

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

local function Update()
    local db = ns.db
    ns.isDay = C_DateAndTime.IsDayTime()
    ns.value = db.enabled and ns.ComputeValue(ns.isDay, GetServerTime(), db.lastFlip, db) or 0
    local darkAlpha, lightAlpha = ns.ToAlphas(ns.value)
    dark:SetAlpha(darkAlpha)
    light:SetColorTexture(ns.ParseColor(db.lightColor))
    light:SetAlpha(lightAlpha)
end

-- Indoors and in instances there is no day or night, so the tint fades out there
local outdoor, outdoorTarget = 1, 1

local function FadeStep(self, elapsed)
    local step = elapsed / INDOOR_FADE_SECONDS
    if outdoor < outdoorTarget then
        outdoor = math.min(outdoorTarget, outdoor + step)
    else
        outdoor = math.max(outdoorTarget, outdoor - step)
    end
    self:SetAlpha(outdoor)
    if outdoor == outdoorTarget then
        self:SetScript("OnUpdate", nil)
    end
end

local function UpdateOutdoor()
    outdoorTarget = (IsIndoors() or IsInInstance()) and 0 or 1
    if outdoor ~= outdoorTarget then
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
    ns.RegisterSettings(ns.db, Update)
    self:UnregisterEvent("ADDON_LOADED")
end

function events:PLAYER_LOGIN()
    Update()
    C_Timer.NewTicker(TICK_SECONDS, Update)
end

function events:DIEL_CYCLE_CHANGED(isDayTime)
    -- Only a real change starts a fade, in case the event repeats the current state
    if ns.isDay ~= nil and isDayTime ~= ns.isDay then
        local hour, minute = GetGameTime()
        ns.db.lastFlip = { time = GetServerTime(), isDay = isDayTime, realmTime = ("%02d:%02d"):format(hour, minute) }
    end
    Update()
end

events.PLAYER_ENTERING_WORLD = UpdateOutdoor
events.ZONE_CHANGED = UpdateOutdoor
events.ZONE_CHANGED_INDOORS = UpdateOutdoor
events.ZONE_CHANGED_NEW_AREA = UpdateOutdoor

for event in pairs({
    ADDON_LOADED = true, PLAYER_LOGIN = true, DIEL_CYCLE_CHANGED = true, PLAYER_ENTERING_WORLD = true,
    ZONE_CHANGED = true, ZONE_CHANGED_INDOORS = true, ZONE_CHANGED_NEW_AREA = true,
}) do
    events:RegisterEvent(event)
end

local function PrintStatus()
    local hour, minute = GetGameTime()
    local flip = ns.db.lastFlip
    print(("WorldLight: %s, realm time %02d:%02d, %s, value %.0f, %s%s"):format(
        ns.db.enabled and "on" or "off", hour, minute, ns.isDay and "day" or "night", ns.value or 0,
        (IsIndoors() or IsInInstance()) and "indoors or in an instance" or "outdoors",
        flip and flip.realmTime and (", last switch to %s at %s"):format(flip.isDay and "day" or "night", flip.realmTime) or ""))
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
