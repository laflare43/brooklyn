"""
variants.py — MaterialVariants as a .rbxmx (insert into MaterialService) and as a
Luau command-bar script, with optional Roblox asset IDs for the texture maps.
"""
import json
import os

from . import style, textures
from .rbxlib import Scene, to_rbxmx

MAP_KEYS = (("color", "ColorMap"), ("normal", "NormalMap"),
            ("rough", "RoughnessMap"), ("metal", "MetalnessMap"))


def load_ids(path):
    """asset_ids.json: { "brick_color": 123456789, "brick_normal": "rbxassetid://..." }"""
    if not path or not os.path.exists(path):
        return {}
    raw = json.load(open(path))
    out = {}
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        v = str(v).strip()
        if not v or v.startswith("PUT") or v == "0":
            continue
        out[k] = v if v.startswith("rbxassetid://") else "rbxassetid://" + v
    return out


def variant_maps(vname, ids):
    sname = textures.VARIANT_SET[vname]
    maps = {}
    for key, prop in MAP_KEYS:
        url = ids.get("%s_%s" % (sname, key))
        if url:
            maps[prop] = url
    return maps


def build_rbxmx(stud_m, ids):
    scene = Scene()
    roots = []
    for vname, (base, tile_m) in style.VARIANTS.items():
        m = variant_maps(vname, ids)
        roots.append(scene.material_variant(
            vname, base, tile_m / stud_m, color_map=m.get("ColorMap"),
            normal_map=m.get("NormalMap"), roughness_map=m.get("RoughnessMap"),
            metalness_map=m.get("MetalnessMap")))
    return to_rbxmx(roots)


LUAU_HEAD = '''--[[
    FB MaterialVariants setup  (paste into the Studio command bar and press Enter)

    Creates the MaterialVariants the Fiorentino Plaza block uses.  Fill in the
    asset ids below after uploading the PNGs from the textures/ folder
    (Asset Manager > Bulk Import > Images; right-click an image > Copy ID).
    Leave an id as nil to skip that map.  Safe to run again: it replaces
    variants with the same name.
]]
local MaterialService = game:GetService("MaterialService")

local IDS = {
%s}

local VARIANTS = {
%s}

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
'''


def build_luau(stud_m, ids):
    sets = {}
    for vname in style.VARIANTS:
        sets.setdefault(textures.VARIANT_SET[vname], None)
    ids_lines = []
    for sname in sets:
        parts = []
        for key, _ in MAP_KEYS:
            if sname != "gate" and key == "metal":
                continue
            url = ids.get("%s_%s" % (sname, key))
            val = ('"%s"' % url) if url else "nil"
            parts.append("%s = %s" % (key, val))
        ids_lines.append("\t%s = { %s },\n" % (sname, ", ".join(parts)))
    var_lines = []
    for vname, (base, tile_m) in style.VARIANTS.items():
        var_lines.append('\t{ name = "%s", base = "%s", tile = %.3f, set = "%s" },\n'
                         % (vname, base, tile_m / stud_m, textures.VARIANT_SET[vname]))
    return LUAU_HEAD % ("".join(ids_lines), "".join(var_lines))
