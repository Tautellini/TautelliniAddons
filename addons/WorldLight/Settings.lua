local _, ns = ...

function ns.RegisterSettings(db, onChange)
    local category = Settings.RegisterVerticalLayoutCategory("WorldLight")

    local function Register(key, name)
        local default = ns.defaults[key]
        local setting = Settings.RegisterAddOnSetting(category, "WorldLight_" .. key, key, db, type(default), name, default)
        setting:SetValueChangedCallback(onChange)
        ns.settings[key] = setting
        return setting
    end

    local function Slider(key, name, step, tooltip)
        local range = ns.ranges[key]
        local options = Settings.CreateSliderOptions(range[1], range[2], step)
        options:SetLabelFormatter(MinimalSliderWithSteppersMixin.Label.Right)
        Settings.CreateSlider(category, Register(key, name), options, tooltip)
    end

    Settings.CreateCheckbox(category, Register("enabled", "Enabled"),
        "Tints the game world by day and night. The UI is never tinted.")
    Slider("day", "Day brightness", 5,
        "Brightness of the world during the day. Negative values darken, positive values brighten, 0 leaves it unchanged.")
    Slider("night", "Night brightness", 5,
        "Brightness of the world at night. Negative values darken, positive values brighten, 0 leaves it unchanged.")
    Slider("fadeMinutes", "Fade length (minutes)", 15,
        "How long the change takes after the server switches between day and night. 0 switches at once.")

    Settings.RegisterAddOnCategory(category)
    ns.category = category
end
