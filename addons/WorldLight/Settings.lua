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
    Settings.CreateColorSwatch(category, Register("lightColor", "Light color"),
        "Color of the light added when brightening. The default cool moonlight looks less foggy than white. Pick white for a neutral lift.")
    Settings.CreateCheckbox(category, Register("customTimes", "Custom day and night times"),
        "Night and day start at the realm time hours below. Turn off to follow the server's own day and night switch. The game's sky is not changed, only the tint.")
    Slider("nightStart", "Night starts (hour)", 1,
        "Realm time hour at which the night begins. Needs custom day and night times.")
    Slider("dayStart", "Day starts (hour)", 1,
        "Realm time hour at which the day begins. Needs custom day and night times.")
    Slider("fadeMinutes", "Fade length (minutes)", 15,
        "How long the change takes after day and night switch. 0 switches at once.")
    Settings.CreateCheckbox(category, Register("tintIndoors", "Tint indoors"),
        "Keep the tint inside buildings and caves. Off by default, because there is no day or night indoors.")
    Settings.CreateCheckbox(category, Register("tintInstances", "Tint in instances"),
        "Keep the tint in dungeons, raids and other instances. Off by default, because instances have their own fixed lighting.")
    Slider("placeFadeSeconds", "Indoor fade (seconds)", 0.5,
        "How long the tint takes to fade out or back in when you enter or leave a building or instance. 0 switches at once.")

    Settings.RegisterAddOnCategory(category)
    ns.category = category
end
