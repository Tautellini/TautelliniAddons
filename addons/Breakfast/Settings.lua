local _, ns = ...

function ns.RegisterSettings(db, onChange)
    local L = ns.L
    local category = Settings.RegisterVerticalLayoutCategory("Breakfast")

    local function Register(key)
        local default = ns.defaults[key]
        local setting = Settings.RegisterAddOnSetting(category, "Breakfast_" .. key, key, db, type(default), L[key], default)
        setting:SetValueChangedCallback(onChange)
        return setting
    end

    local function Slider(key, step)
        local range = ns.ranges[key]
        local options = Settings.CreateSliderOptions(range[1], range[2], step)
        options:SetLabelFormatter(MinimalSliderWithSteppersMixin.Label.Right)
        Settings.CreateSlider(category, Register(key), options, L[key .. "Tip"])
    end

    for _, group in ipairs(ns.GROUPS) do
        Settings.CreateCheckbox(category, Register(group), L.groupTip)
    end
    Slider("size", 2)
    Slider("perRow", 1)
    Settings.CreateCheckbox(category, Register("locked"), L.lockedTip)

    Settings.RegisterAddOnCategory(category)
    ns.category = category
end
