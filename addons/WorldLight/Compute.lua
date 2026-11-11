local _, ns = ...

-- No WoW API calls in this file, so tests can load it in plain Lua

ns.defaults = {
    enabled = true,
    day = 0,
    night = 30,
    fadeMinutes = 60,
    -- Color of the added light, as AARRGGBB hex like Blizzard's color swatch stores it. Default is a cool moonlight.
    lightColor = "ffbfd9ff",
    tintIndoors = false,
    tintInstances = false,
    placeFadeSeconds = 2,
    -- Realm time hours. On by default because the sky already gets darker before the server flag flips.
    customTimes = true,
    nightStart = 20,
    dayStart = 6,
}

ns.ranges = {
    day = { -100, 100 },
    night = { -100, 100 },
    fadeMinutes = { 0, 180 },
    placeFadeSeconds = { 0, 10 },
    nightStart = { 0, 23 },
    dayStart = { 0, 23 },
}

-- shortcut: strongest tint at -100 and +100 is a guess, tune it in game
ns.MAX_DARKEN = 0.6
ns.MAX_BRIGHTEN = 0.25

function ns.Clamp(key, value)
    local range = ns.ranges[key]
    return math.min(range[2], math.max(range[1], value))
end

-- Replaces missing or broken saved values with defaults and keeps numbers in range
function ns.Sanitize(db)
    for key, default in pairs(ns.defaults) do
        if type(db[key]) ~= type(default) or (key == "lightColor" and not db[key]:match("^%x%x%x%x%x%x%x%x$")) then
            db[key] = default
        elseif ns.ranges[key] then
            db[key] = ns.Clamp(key, db[key])
        end
    end
    return db
end

-- Brightness from -100 to 100. After the server flips between day and night,
-- the value fades from the old phase to the new one over fadeMinutes.
function ns.ComputeValue(isDay, now, lastFlip, db)
    local target = isDay and db.day or db.night
    local fade = db.fadeMinutes * 60
    if fade <= 0 or type(lastFlip) ~= "table" or lastFlip.isDay ~= isDay or type(lastFlip.time) ~= "number" then
        return target
    end
    local progress = (now - lastFlip.time) / fade
    if progress < 0 or progress >= 1 then
        return target
    end
    local from = isDay and db.night or db.day
    return from + (target - from) * progress
end

-- Day or night from the realm clock and the configured hours. Returns isDay and the minutes
-- since that phase started. Equal hours mean it is always night.
function ns.ClockPhase(minuteOfDay, db)
    local sinceDay = (minuteOfDay - db.dayStart * 60) % 1440
    if sinceDay < (db.nightStart - db.dayStart) * 60 % 1440 then
        return true, sinceDay
    end
    return false, (minuteOfDay - db.nightStart * 60) % 1440
end

-- Whether the tint shows at the player's location. In an instance only the instance
-- setting counts, because most dungeons are also indoors.
function ns.ShowsTint(indoors, inInstance, db)
    if inInstance then
        return db.tintInstances
    end
    return db.tintIndoors or not indoors
end

-- Returns r, g, b from 0 to 1 for an AARRGGBB hex string
function ns.ParseColor(hex)
    return tonumber(hex:sub(3, 4), 16) / 255, tonumber(hex:sub(5, 6), 16) / 255, tonumber(hex:sub(7, 8), 16) / 255
end

-- Negative values darken with a black layer, positive values brighten with an additive light layer
function ns.ToAlphas(value)
    if value < 0 then
        return -value / 100 * ns.MAX_DARKEN, 0
    end
    return 0, value / 100 * ns.MAX_BRIGHTEN
end
