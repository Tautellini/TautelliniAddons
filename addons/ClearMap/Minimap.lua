local _, ns = ...

local BLANK_MASK = "Interface\\AddOns\\ClearMap\\Media\\blank"
local SQUARE_MASK = "Interface\\Buttons\\WHITE8X8"
local TILE_PATH = "Interface\\AddOns\\ClearMap\\Tiles\\%d\\%d_%d"
local SEA = { 0.28, 0.53, 0.67 } -- the deep water color, shown where no map has tiles

-- The minimap's own shape. Forever's default, replaced whenever Blizzard or a minimap addon sets another mask.
local minimapMask = (GetMinimapShape and GetMinimapShape() == "SQUARE") and SQUARE_MASK or "ui-hud-minimap-frame-generic-mask"
local clip, frame, mask
local textures = {}
local active, settingMask = false, false
-- Outside its own rectangle a mask repeats its edge pixels by default. A square mask is white at the edge,
-- so the tiles would show across the whole screen. Transparent edges keep them inside the shape.
local EDGE = "CLAMPTOBLACKADDITIVE"

local function SetMask(target, path)
    if type(path) == "string" and C_Texture.GetAtlasInfo(path) then
        target:SetAtlas(path, false, nil, nil, EDGE, EDGE)
    else
        target:SetTexture(path, EDGE, EDGE)
    end
end

-- A transparent mask hides Blizzard's terrain but leaves blips, the player arrow and child frames alone.
local function UseOurTerrain(on)
    if on == active then return end
    active = on
    clip:SetShown(on)
    settingMask = true
    Minimap:SetMaskTexture(on and BLANK_MASK or minimapMask)
    settingMask = false
end

-- Installed at load, before minimap addons such as EllesmereUI set their own shape, so none of their masks are missed.
if Minimap then
    hooksecurefunc(Minimap, "SetMaskTexture", function(_, path)
        if settingMask then return end
        minimapMask = path
        if mask then
            SetMask(mask, path)
        end
        if active then
            settingMask = true
            Minimap:SetMaskTexture(BLANK_MASK)
            settingMask = false
        end
    end)
end

local function Texture(i)
    local tex = textures[i]
    if not tex then
        tex = frame:CreateTexture(nil, "ARTWORK")
        tex:AddMaskTexture(mask)
        textures[i] = tex
    end
    return tex
end

-- Position of the player in world yards (x north, y west), from the zone map position.
local function PlayerWorldPosition()
    local mapID = C_Map.GetBestMapForUnit("player")
    local here = mapID and ns.tiles[mapID]
    local pos = here and C_Map.GetPlayerMapPosition(mapID, "player")
    if not pos then return end
    local px, py = pos:GetXY()
    if issecretvalue(px) or issecretvalue(py) then return end
    local b = here.bounds -- min x, min y, max x, max y
    return mapID, here, b[3] - py * (b[3] - b[1]), b[4] - px * (b[4] - b[2])
end

local function Update()
    if not (ns.db.enabled and ns.db.minimap) or C_CVar.GetCVarBool("rotateMinimap") then
        return UseOurTerrain(false)
    end
    local mapID, here, wx, wy = PlayerWorldPosition()
    -- Indoors only the capitals have fitting tiles, since theirs are drawn from the floors of their buildings.
    local indoors = IsIndoors()
    if not mapID or (indoors and not here.indoor) then
        return UseOurTerrain(false)
    end
    -- Minimap addons move, rescale and re-level the minimap, so follow it every frame.
    local level = math.max(0, Minimap:GetFrameLevel() - 1)
    if clip:GetFrameLevel() ~= level or frame:GetFrameLevel() ~= level then
        clip:SetFrameLevel(level)
        frame:SetFrameLevel(level) -- a child defaults to one above its parent, which would be the minimap's own level
    end
    -- How far the minimap sees, in yards from its center. The game reports it for the current zoom, the indoor view
    -- and the minimap's size, so blips and tiles move together. HereBeDragons uses the same call.
    local half = C_Minimap.GetViewRadius()
    local k = half and half > 0 and frame:GetWidth() / (2 * half) or 0 -- our own units, which differ from the minimap's when it is scaled
    if k <= 0 then
        return UseOurTerrain(false)
    end
    local used = 0

    local function Draw(id, grid, sublevel)
        local b = grid.bounds
        local th, tw = (b[3] - b[1]) / grid.rows, (b[4] - b[2]) / grid.cols
        for row = 0, grid.rows - 1 do
            local top = b[3] - row * th
            if top > wx - half and top - th < wx + half then
                for col = 0, grid.cols - 1 do
                    local left = b[4] - col * tw
                    if left > wy - half and left - tw < wy + half then
                        used = used + 1
                        local tex = Texture(used)
                        local path = TILE_PATH:format(id, row, col)
                        if tex.path ~= path then
                            tex:SetTexture(path, nil, nil, "TRILINEAR")
                            tex.path = path
                        end
                        tex:SetDrawLayer("ARTWORK", sublevel)
                        tex:ClearAllPoints()
                        -- Screen right is east (world y falling), screen up is north (world x rising).
                        tex:SetPoint("TOPLEFT", frame, "CENTER", (wy - left) * k, (top - wx) * k)
                        tex:SetSize(tw * k, th * k)
                        tex:Show()
                    end
                end
            end
        end
    end

    -- Neighbor zones fill the view near borders. The current zone is drawn on top of them.
    for id, grid in pairs(ns.tiles) do
        if id ~= mapID and grid.map == here.map then
            Draw(id, grid, 0)
        end
    end
    Draw(mapID, here, 1)
    for i = used + 1, #textures do
        textures[i]:Hide()
    end
    UseOurTerrain(true)
end

function ns.SetupMinimap()
    if not Minimap then return end
    -- A child of the minimap itself, one level below it: it follows every reparent, rescale and fade that minimap
    -- addons apply, while the minimap's terrain, blips and child frames stay on top. EllesmereUI, for example,
    -- moves the minimap out of MinimapCluster and fades the cluster to 0.
    -- The tiles are far larger than the minimap, so they sit inside a frame that clips to the minimap's rectangle.
    -- The mask then cuts the round or cropped shape inside that rectangle.
    local level = math.max(0, Minimap:GetFrameLevel() - 1)
    clip = CreateFrame("Frame", nil, Minimap)
    clip:SetAllPoints(Minimap)
    clip:SetFrameLevel(level)
    clip:SetClipsChildren(true)
    clip:EnableMouse(false)
    clip:Hide()
    frame = CreateFrame("Frame", nil, clip)
    frame:SetAllPoints(clip)
    frame:SetFrameLevel(level)
    frame:EnableMouse(false)
    mask = frame:CreateMaskTexture()
    mask:SetAllPoints(frame)
    SetMask(mask, minimapMask)
    local sea = frame:CreateTexture(nil, "BACKGROUND")
    sea:SetAllPoints()
    sea:SetColorTexture(unpack(SEA))
    sea:AddMaskTexture(mask)

    local driver = CreateFrame("Frame")
    driver:SetScript("OnUpdate", Update)
end
