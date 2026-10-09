--[[
    FB MaterialVariants setup  (paste into the Studio command bar and press Enter)

    Creates the MaterialVariants the Fiorentino Plaza block uses.  Fill in the
    asset ids below after uploading the PNGs from the textures/ folder
    (Asset Manager > Bulk Import > Images; right-click an image > Copy ID).
    Leave an id as nil to skip that map.  Safe to run again: it replaces
    variants with the same name.
]]
local MaterialService = game:GetService("MaterialService")

local IDS = {
	brick = { color = nil, normal = nil, rough = nil },
	sidewalk = { color = nil, normal = nil, rough = nil },
	trim = { color = nil, normal = nil, rough = nil },
	asphalt = { color = nil, normal = nil, rough = nil },
	granite = { color = nil, normal = nil, rough = nil },
	gravel = { color = nil, normal = nil, rough = nil },
	gate = { color = nil, normal = nil, rough = nil, metal = nil },
}

local VARIANTS = {
	{ name = "FB_BrickProject", base = "Brick", tile = 4.000, set = "brick" },
	{ name = "FB_BrickRow", base = "Brick", tile = 4.000, set = "brick" },
	{ name = "FB_SidewalkConcrete", base = "Concrete", tile = 5.000, set = "sidewalk" },
	{ name = "FB_ConcreteTrim", base = "Concrete", tile = 5.000, set = "trim" },
	{ name = "FB_AsphaltRoad", base = "Asphalt", tile = 13.333, set = "asphalt" },
	{ name = "FB_GraniteCurb", base = "Granite", tile = 5.000, set = "granite" },
	{ name = "FB_RoofGravel", base = "Concrete", tile = 6.667, set = "gravel" },
	{ name = "FB_RollGate", base = "Metal", tile = 2.000, set = "gate" },
}

local function content(id)
	if id == nil then return "" end
	if type(id) == "number" then return "rbxassetid://" .. id end
	return id
end

for _, v in ipairs(VARIANTS) do
	local old = MaterialService:FindFirstChild(v.name)
	if old then old:Destroy() end
	local mv = Instance.new("MaterialVariant")
	mv.Name = v.name
	mv.BaseMaterial = Enum.Material[v.base]
	mv.StudsPerTile = v.tile
	local s = IDS[v.set] or {}
	mv.ColorMap = content(s.color)
	mv.NormalMap = content(s.normal)
	mv.RoughnessMap = content(s.rough)
	if s.metal then mv.MetalnessMap = content(s.metal) end
	mv.Parent = MaterialService
end
print("FB MaterialVariants ready: " .. #VARIANTS)
