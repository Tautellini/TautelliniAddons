local _, ns = ...

local L = {
    buffFood = "Buff food",
    food = "Food",
    drink = "Drinks",
    potion = "Potions",
    elixir = "Elixirs and flasks",
    bandage = "Bandages and scrolls",
    groupTip = "Show this group on the bar.",
    size = "Button size",
    sizeTip = "Width and height of each button in pixels.",
    perRow = "Buttons per row",
    perRowTip = "The bar starts a new row after this many buttons.",
    locked = "Lock position",
    lockedTip = "Hides the drag handle above the bar. Unlock to move the bar by its handle.",
    combat = "Breakfast: the bar updates when the fight ends.",
    hideHint = "Shift + right click: hide this item",
    hidden = "Breakfast: %s is hidden. /breakfast reset shows all hidden items again.",
    reset = "Breakfast: all hidden items are shown again.",
}

if GetLocale() == "deDE" then
    L.buffFood = "Buff-Essen"
    L.food = "Essen"
    L.drink = "Getränke"
    L.potion = "Tränke"
    L.elixir = "Elixiere und Fläschchen"
    L.bandage = "Verbände und Rollen"
    L.groupTip = "Zeigt diese Gruppe auf der Leiste."
    L.size = "Tastengröße"
    L.sizeTip = "Breite und Höhe jeder Taste in Pixeln."
    L.perRow = "Tasten pro Reihe"
    L.perRowTip = "Nach so vielen Tasten beginnt die Leiste eine neue Reihe."
    L.locked = "Position sperren"
    L.lockedTip = "Blendet den Griff über der Leiste aus. Entsperren, um die Leiste am Griff zu verschieben."
    L.combat = "Breakfast: Die Leiste wird nach dem Kampf aktualisiert."
    L.hideHint = "Umschalt + Rechtsklick: Diesen Gegenstand ausblenden"
    L.hidden = "Breakfast: %s ist ausgeblendet. /breakfast reset zeigt alle ausgeblendeten Gegenstände wieder."
    L.reset = "Breakfast: Alle ausgeblendeten Gegenstände werden wieder angezeigt."
end

ns.L = L
