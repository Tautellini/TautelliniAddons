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
    "BreakfastDB",
    "SLASH_BREAKFAST1",
    "LoreLinesDB",
    "SLASH_LORELINES1",
    "BINDING_HEADER_LORELINES",
    "BINDING_NAME_LORELINES_TOGGLE",
    "SlashCmdList",
}

-- Add WoW API globals as your addons start using them
read_globals = {
    "CreateFrame", "GetBuildInfo", "InCombatLockdown", "hooksecurefunc",
    "C_Timer", "C_ChatInfo", "C_DamageMeter", "C_CurveUtil", "C_DurationUtil",
    "UnitHealth", "UnitHealthMax", "Enum", "Item",
    "WorldFrame", "C_DateAndTime", "GetServerTime", "GetGameTime", "IsIndoors", "IsInInstance",
    "Settings", "MinimalSliderWithSteppersMixin",
    "WorldMapFrame", "C_Map", "GameTooltip", "Minimap", "C_Texture", "C_CVar", "MenuUtil", "GetMinimapShape", "GameFontNormal",
    "GetLocale", "UnitRace", "UnitExists", "UIParent", "UISpecialFrames", "tinsert", "ChatFrame1", "ChatFrameUtil",
    "ButtonFrameTemplate_HidePortrait", "ButtonFrameTemplate_HideButtonBar", "GameTooltip_Hide",
    "CreateScrollBoxListLinearView", "ScrollUtil", "CreateDataProvider", "ScrollBoxConstants",
    "GameFontHighlight", "GameFontDisable",
    "C_Container", "C_Item", "C_Spell", "C_TooltipInfo",
    "issecretvalue", "hasanysecretvalues", "issecrettable",
    "canaccessvalue", "canaccesstable", "canaccesssecrets", "scrubsecretvalues",
    "WOW_PROJECT_ID", "WOW_PROJECT_MAINLINE", "WOW_PROJECT_CAMELOT",
}
