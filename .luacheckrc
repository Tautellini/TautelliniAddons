std = "lua51"
max_line_length = false
exclude_files = { ".release/", "**/libs/", "**/Libs/" }
ignore = { "212/self" }

-- Add each addon's SavedVariables and slash command globals here
globals = {
    "ForeverAddonTemplateDB",
    "SLASH_FOREVERADDONTEMPLATE1",
    "WorldLightDB",
    "SLASH_WORLDLIGHT1",
    "ClearMapDB",
    "SLASH_CLEARMAP1",
    "SlashCmdList",
}

-- Add WoW API globals as your addons start using them
read_globals = {
    "CreateFrame", "GetBuildInfo", "InCombatLockdown", "hooksecurefunc",
    "C_Timer", "C_ChatInfo", "C_DamageMeter", "C_CurveUtil", "C_DurationUtil",
    "UnitHealth", "UnitHealthMax", "Enum", "Item",
    "WorldFrame", "C_DateAndTime", "GetServerTime", "GetGameTime", "IsIndoors", "IsInInstance",
    "Settings", "MinimalSliderWithSteppersMixin",
    "WorldMapFrame", "C_Map", "GameTooltip", "Minimap", "C_Texture", "C_CVar",
    "issecretvalue", "hasanysecretvalues", "issecrettable",
    "canaccessvalue", "canaccesstable", "canaccesssecrets", "scrubsecretvalues",
    "WOW_PROJECT_ID", "WOW_PROJECT_MAINLINE", "WOW_PROJECT_CAMELOT",
}
