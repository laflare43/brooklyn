--[[
    Studio_Setup.luau  —  paste into the Studio COMMAND BAR (View > Command Bar) and press Enter.

    1. Removes the default Baseplate (the block brings its own ground).
    2. Sets up daylight so the materials read properly: Future lighting, a low
       late-morning sun for East New York, soft atmosphere, mild grading.
    3. Turns on StreamingEnabled so only nearby parts load (the block is ~24k parts).

    Safe to run more than once. Every step is wrapped, so a property your Studio
    version doesn't allow is skipped with a warning instead of stopping the script.
]]
local Lighting = game:GetService("Lighting")
local Workspace = game:GetService("Workspace")

local function try(label, fn)
	local ok, err = pcall(fn)
	if not ok then warn("[Studio_Setup] skipped " .. label .. ": " .. tostring(err)) end
end

-- 1. default baseplate
try("baseplate", function()
	local bp = Workspace:FindFirstChild("Baseplate")
	if bp then bp:Destroy() end
end)

-- 2. lighting
try("technology", function() Lighting.Technology = Enum.Technology.Future end)
try("sun", function()
	Lighting.ClockTime = 10.5                 -- late morning
	Lighting.GeographicLatitude = 40.7        -- Brooklyn
	Lighting.Brightness = 3
	Lighting.EnvironmentDiffuseScale = 0.6
	Lighting.EnvironmentSpecularScale = 0.8
	Lighting.GlobalShadows = true
	Lighting.ShadowSoftness = 0.12
	Lighting.Ambient = Color3.fromRGB(70, 74, 84)
	Lighting.OutdoorAmbient = Color3.fromRGB(110, 118, 132)
	Lighting.ColorShift_Top = Color3.fromRGB(255, 244, 226)
	Lighting.ExposureCompensation = 0.1
end)

local function replace(className, name, props)
	local old = Lighting:FindFirstChild(name)
	if old then old:Destroy() end
	local inst = Instance.new(className)
	inst.Name = name
	for k, v in pairs(props) do inst[k] = v end
	inst.Parent = Lighting
	return inst
end

try("atmosphere", function()
	replace("Atmosphere", "FB_Atmosphere", {
		Density = 0.28, Offset = 0.2, Color = Color3.fromRGB(200, 214, 232),
		Decay = Color3.fromRGB(150, 160, 178), Glare = 0.2, Haze = 1.4,
	})
end)
try("grading", function()
	replace("ColorCorrectionEffect", "FB_Grade", {
		Brightness = 0, Contrast = 0.06, Saturation = 0.04, TintColor = Color3.fromRGB(255, 250, 244),
	})
end)
try("bloom", function()
	replace("BloomEffect", "FB_Bloom", { Intensity = 0.25, Size = 22, Threshold = 1.6 })
end)
try("sunrays", function()
	replace("SunRaysEffect", "FB_SunRays", { Intensity = 0.04, Spread = 0.6 })
end)

-- 3. streaming
try("streaming", function()
	Workspace.StreamingEnabled = true
	Workspace.StreamingMinRadius = 128
	Workspace.StreamingTargetRadius = 1024
end)

print("[Studio_Setup] done — now insert the Block_*.rbxmx files and MaterialVariants.rbxmx")
