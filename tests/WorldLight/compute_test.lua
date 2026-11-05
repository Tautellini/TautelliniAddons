-- Run from the repo root: lua tests/WorldLight/compute_test.lua
local ns = {}
assert(loadfile("addons/WorldLight/Compute.lua"))("WorldLight", ns)

local db = ns.Sanitize({ day = 0, night = 30, fadeMinutes = 60 })
local now = 100000

-- No recorded flip: use the current phase value
assert(ns.ComputeValue(true, now, nil, db) == 0)
assert(ns.ComputeValue(false, now, nil, db) == 30)

-- Halfway through a day to night fade
assert(ns.ComputeValue(false, now, { time = now - 1800, isDay = false }, db) == 15)

-- Halfway through a night to day fade
assert(ns.ComputeValue(true, now, { time = now - 1800, isDay = true }, db) == 15)

-- Fade finished, flip in the future, or flip direction does not match the current phase
assert(ns.ComputeValue(false, now, { time = now - 3600, isDay = false }, db) == 30)
assert(ns.ComputeValue(false, now, { time = now + 60, isDay = false }, db) == 30)
assert(ns.ComputeValue(true, now, { time = now - 60, isDay = false }, db) == 0)

-- Broken saved flip data falls back to the phase value
assert(ns.ComputeValue(false, now, { time = "x", isDay = false }, db) == 30)

-- Fade length 0 switches at once
local instant = ns.Sanitize({ day = -40, night = 20, fadeMinutes = 0 })
assert(ns.ComputeValue(false, now, { time = now - 1, isDay = false }, instant) == 20)

-- Fade across 0 from a darkening day to a brightening night
local cross = ns.Sanitize({ day = -40, night = 40, fadeMinutes = 60 })
assert(ns.ComputeValue(false, now, { time = now - 1800, isDay = false }, cross) == 0)

-- Alphas
local d, l = ns.ToAlphas(-100)
assert(d == ns.MAX_DARKEN and l == 0)
d, l = ns.ToAlphas(100)
assert(d == 0 and l == ns.MAX_BRIGHTEN)
d, l = ns.ToAlphas(0)
assert(d == 0 and l == 0)

-- Sanitize fixes wrong types and out of range values
local broken = ns.Sanitize({ enabled = "yes", day = 500, night = -500, fadeMinutes = "long" })
assert(broken.enabled == true and broken.day == 100 and broken.night == -100 and broken.fadeMinutes == 60)

-- Light color: default moonlight parses, broken colors fall back, valid custom colors stay
local r, g, b = ns.ParseColor(ns.defaults.lightColor)
assert(r == 191 / 255 and g == 217 / 255 and b == 1)
assert(ns.Sanitize({ lightColor = "blue" }).lightColor == ns.defaults.lightColor)
assert(ns.Sanitize({ lightColor = 42 }).lightColor == ns.defaults.lightColor)
assert(ns.Sanitize({ lightColor = "FF00ff80" }).lightColor == "FF00ff80")
r, g, b = ns.ParseColor("FF00ff80")
assert(r == 0 and g == 1 and b == 128 / 255)

-- Where the tint shows. In an instance only the instance setting counts.
local place = ns.Sanitize({})
assert(ns.ShowsTint(false, false, place) == true)
assert(ns.ShowsTint(true, false, place) == false)
assert(ns.ShowsTint(false, true, place) == false)
assert(ns.ShowsTint(true, true, place) == false)
place.tintIndoors = true
assert(ns.ShowsTint(true, false, place) == true)
assert(ns.ShowsTint(true, true, place) == false)
place.tintInstances = true
place.tintIndoors = false
assert(ns.ShowsTint(true, true, place) == true)
assert(ns.ShowsTint(true, false, place) == false)

-- New settings get defaults and the fade is clamped
local fresh = ns.Sanitize({ placeFadeSeconds = 99, tintIndoors = "yes" })
assert(fresh.placeFadeSeconds == 10 and fresh.tintIndoors == false and fresh.tintInstances == false)

print("compute_test: all passed")
