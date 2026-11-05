local _, ns = ...

-- No WoW API calls in this file, so tests can load it in plain Lua

ns.defaults = {
    enabled = true,
    day = 0,
    night = 30,
    fadeMinutes = 60,
}

ns.ranges = {
    day = { -100, 100 },
    night = { -100, 100 },
    fadeMinutes = { 0, 180 },
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
        if type(db[key]) ~= type(default) then
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

-- Negative values darken with a black layer, positive values brighten with an additive white layer
function ns.ToAlphas(value)
    if value < 0 then
        return -value / 100 * ns.MAX_DARKEN, 0
    end
    return 0, value / 100 * ns.MAX_BRIGHTEN
end
