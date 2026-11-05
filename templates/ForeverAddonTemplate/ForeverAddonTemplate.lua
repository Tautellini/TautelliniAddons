local addonName, ns = ...

-- WOW_PROJECT_CAMELOT is nil outside Forever, so fall back to the literal value
ns.isForever = WOW_PROJECT_ID == (WOW_PROJECT_CAMELOT or 18)

local defaults = {
    enabled = true,
}

local frame = CreateFrame("Frame")
frame:SetScript("OnEvent", function(self, event, ...)
    self[event](self, ...)
end)
frame:RegisterEvent("ADDON_LOADED")
frame:RegisterEvent("PLAYER_LOGIN")

function frame:ADDON_LOADED(name)
    if name ~= addonName then return end
    ForeverAddonTemplateDB = ForeverAddonTemplateDB or {}
    for key, value in pairs(defaults) do
        if ForeverAddonTemplateDB[key] == nil then
            ForeverAddonTemplateDB[key] = value
        end
    end
    ns.db = ForeverAddonTemplateDB
    self:UnregisterEvent("ADDON_LOADED")
end

function frame:PLAYER_LOGIN()
    local _, build, _, interface = GetBuildInfo()
    print(("%s: build %s, interface %d, Forever %s"):format(addonName, build, interface, tostring(ns.isForever)))
end

-- UnitHealth can return a secret in combat. Never do math on a secret.
function ns.HealthPercent(unit)
    local cur, maxHealth = UnitHealth(unit), UnitHealthMax(unit)
    if issecretvalue(cur) or issecretvalue(maxHealth) or maxHealth == 0 then
        return nil
    end
    return cur / maxHealth * 100
end

SLASH_FOREVERADDONTEMPLATE1 = "/fat"
SlashCmdList.FOREVERADDONTEMPLATE = function()
    local pct = ns.HealthPercent("player")
    print(addonName .. ": health " .. (pct and ("%.0f%%"):format(pct) or "hidden right now"))
end
