--[[
    MainGame_Arrival.lua  (v2)
    LocalScript inside ReplicatedFirst   ── MAIN GAME

    v2 — ARRIVAL SWITCH
    When the screen lifts you are looking down on your spot from high
    above, desaturated, and the camera drops toward your character in
    hard steps — whoosh, land, hold — then swoops down behind them into
    the normal camera, like a GTA character switch. It runs on the first
    spawn of a visit, whether that is your saved spot or your block.
    Tune it in SWITCH below. Controls and the HUD are off while it runs
    and come back on the moment it ends (or if anything interrupts it).

    Keeps the "CONNECTING TO SERVER" screen up from the moment the player
    lands until their character has actually been built and dropped in,
    so nobody sees the default avatar, a T-posing rig, or the body being
    scaled and dressed.

    • Arriving from the lobby, it takes over the exact screen the lobby
      handed to the teleport (TeleportService:SetTeleportGui), so there
      is no flicker between the two places.
    • Joining the main game directly (or testing it in Studio), it builds
      the same screen itself.
    • It lifts once the server has finished spawning the character
      (MainGame_Server sets the "SpawnReady" attribute on it), or once a
      default Roblox avatar has loaded instead, or after TIMEOUT seconds
      whatever happens — it can never trap anyone on a black screen.

    Must be in ReplicatedFirst: that is the only place a script runs early
    enough to take the screen over before the game appears.
]]

local ReplicatedFirst = game:GetService("ReplicatedFirst")
local TeleportService = game:GetService("TeleportService")
local TweenService    = game:GetService("TweenService")
local Players         = game:GetService("Players")
local RunService      = game:GetService("RunService")
local Lighting        = game:GetService("Lighting")
local StarterGui      = game:GetService("StarterGui")
local SoundService    = game:GetService("SoundService")

local CONFIG = {
	TITLE       = "CONNECTING TO SERVER",   -- keep in step with LOADING_TITLE in CharCreation_Client
	MIN_SHOW    = 1.0,    -- seconds the screen stays up at the least, so it never just blinks
	SLOW_AFTER  = 15,     -- seconds before the status says it is taking a while
	TIMEOUT     = 30,     -- seconds before it lifts no matter what
	FADE        = 0.6,    -- fade-out length in seconds
}

-- The GTA-style drop onto your character. Heights are studs above them.
local SWITCH = {
	ENABLED       = true,
	HEIGHTS       = { 360, 140, 48 },  -- the aerial stops, highest first (2–5 of them)
	PAN_IN        = 140,   -- studs the first shot slides across before settling over you (0 = off)
	FIRST_HOLD    = 1.3,   -- seconds on the highest shot (the screen fades in during it)
	DROP_TIME     = 0.42,  -- seconds per drop between stops
	HOLD_TIME     = 0.5,   -- seconds held at each lower stop
	FINAL_TIME    = 1.2,   -- seconds for the swoop into the normal camera
	TURN_PER_STOP = 14,    -- degrees the shot turns on each drop
	DRIFT         = 4,     -- degrees per second the shot keeps turning while held
	LEAN          = 0.18,  -- how far off straight-down the aerial shots look (0 = straight down)
	FOV_PUNCH     = 14,    -- extra field of view at the fastest point of a drop
	BLUR_MAX      = 18,    -- blur at the fastest point of a drop
	LAND_SHAKE    = 0.6,   -- degrees of jolt when a drop lands
	AERIAL_SATURATION = -0.5,                      -- colour drained from the sky shots
	AERIAL_TINT   = Color3.fromRGB(214, 224, 240), -- a cool tint on the sky shots
	FINAL_PITCH   = -14,   -- degrees the normal camera ends up looking down
	FINAL_DISTANCE = nil,  -- studs behind the character (nil = Roblox's default zoom)
	HIDE_HUD      = true,  -- hide your ScreenGuis and the chat / backpack / player list
	LOCK_CONTROLS = true,  -- no walking off mid-switch
	WHOOSH_SOUND  = "",    -- "rbxassetid://…", played as each drop starts (optional)
	LAND_SOUND    = "",    -- played as each drop lands (optional)
	SOUND_VOLUME  = 0.6,
}

local RED   = Color3.fromRGB(190, 20, 20)
local CREAM = Color3.fromRGB(220, 212, 198)
local MUTED = Color3.fromRGB(110, 108, 102)

local player    = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")
local shownAt   = os.clock()

-- ─── THE SCREEN ──────────────────────────────────────────────────────────────
-- Same layout and names as buildLoadingScreen() in CharCreation_Client.
local function buildScreen()
	local g = Instance.new("ScreenGui")
	g.Name = "ConnectingScreen"; g.IgnoreGuiInset = true; g.DisplayOrder = 1000

	local bg = Instance.new("Frame"); bg.Name = "Background"; bg.Size = UDim2.fromScale(1, 1)
	bg.BackgroundColor3 = Color3.new(0, 0, 0); bg.BorderSizePixel = 0; bg.Parent = g

	local tag = Instance.new("TextLabel"); tag.Name = "Tag"; tag.AnchorPoint = Vector2.new(0.5, 0.5)
	tag.Position = UDim2.fromScale(0.5, 0.46); tag.Size = UDim2.new(0.8, 0, 0, 16)
	tag.BackgroundTransparency = 1; tag.Text = "// THE BLOCK"
	tag.TextColor3 = RED; tag.Font = Enum.Font.RobotoMono; tag.TextSize = 12; tag.Parent = bg

	local title = Instance.new("TextLabel"); title.Name = "Title"; title.AnchorPoint = Vector2.new(0.5, 0.5)
	title.Position = UDim2.fromScale(0.5, 0.52); title.Size = UDim2.new(0.8, 0, 0, 30)
	title.BackgroundTransparency = 1; title.Text = CONFIG.TITLE
	title.TextColor3 = CREAM; title.Font = Enum.Font.GothamBold; title.TextSize = 24; title.Parent = bg

	local status = Instance.new("TextLabel"); status.Name = "Status"; status.AnchorPoint = Vector2.new(0.5, 0.5)
	status.Position = UDim2.fromScale(0.5, 0.58); status.Size = UDim2.new(0.9, 0, 0, 16)
	status.BackgroundTransparency = 1; status.Text = ""
	status.TextColor3 = MUTED; status.Font = Enum.Font.RobotoMono; status.TextSize = 10; status.Parent = bg
	return g
end

-- The lobby's screen if we came through a teleport, a fresh one otherwise.
local okArrive, arriving = pcall(function() return TeleportService:GetArrivingTeleportGui() end)
local screen = (okArrive and typeof(arriving) == "Instance" and arriving:IsA("ScreenGui"))
	and arriving or buildScreen()
screen.ResetOnSpawn   = false        -- the character spawning must not wipe it
screen.IgnoreGuiInset = true
screen.DisplayOrder   = 1000
screen.Parent         = playerGui

local title  = screen:FindFirstChild("Title", true)
local status = screen:FindFirstChild("Status", true)
if title and title:IsA("TextLabel") then title.Text = CONFIG.TITLE end

-- Ours is up; Roblox's own loading screen can go.
pcall(function() ReplicatedFirst:RemoveDefaultLoadingScreen() end)

-- ─── STATUS LINE ─────────────────────────────────────────────────────────────
local done = false
local function setStatus(text)
	if status and status:IsA("TextLabel") then status.Text = text end
end

-- A slow breathe on the status line, so a long wait never looks frozen.
task.spawn(function()
	if not (status and status:IsA("TextLabel")) then return end
	local info = TweenInfo.new(0.9, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut)
	while not done and status.Parent do
		TweenService:Create(status, info, { TextTransparency = 0.55 }):Play()
		task.wait(0.9)
		if done then break end
		TweenService:Create(status, info, { TextTransparency = 0 }):Play()
		task.wait(0.9)
	end
end)

-- ─── WHEN IS THE CHARACTER READY? ────────────────────────────────────────────
-- MainGame_Server builds the body with its root anchored, scales and dresses
-- it, then unanchors it and sets SpawnReady. A default Roblox avatar (no
-- saved character) is never anchored, so an unanchored root counts as well.
local function characterReady(char)
	if not char or not char.Parent then return false end
	if char:GetAttribute("SpawnReady") then return true end
	local root = char:FindFirstChild("HumanoidRootPart")
	if not root or not root:IsA("BasePart") then return false end
	-- Our rigs carry the save's archetype; until SpawnReady they are still
	-- being built, whatever their root says.
	if char:GetAttribute("CharArchetype") ~= nil then return false end
	return not root.Anchored
end

-- ─── FADE OUT ────────────────────────────────────────────────────────────────
local function lift()
	if done then return end
	done = true
	local info = TweenInfo.new(CONFIG.FADE, Enum.EasingStyle.Sine, Enum.EasingDirection.Out)
	for _, d in ipairs(screen:GetDescendants()) do
		if d:IsA("TextLabel") or d:IsA("TextButton") then
			TweenService:Create(d, info, { TextTransparency = 1, TextStrokeTransparency = 1 }):Play()
		end
		if d:IsA("GuiObject") then
			TweenService:Create(d, info, { BackgroundTransparency = 1 }):Play()
		end
		if d:IsA("ImageLabel") or d:IsA("ImageButton") then
			TweenService:Create(d, info, { ImageTransparency = 1 }):Play()
		end
	end
	task.delay(CONFIG.FADE + 0.05, function() screen:Destroy() end)
end

-- ╔════════════════════════════════════════════════════════════════════════╗
-- ║  ARRIVAL SWITCH                                                        ║
-- ╚════════════════════════════════════════════════════════════════════════╝
local camera = workspace.CurrentCamera   -- re-read when the switch starts

local function ease(a, style, dir)
	return TweenService:GetValue(a, style, dir or Enum.EasingDirection.InOut)
end

-- Where Roblox's own camera looks on a Humanoid: the root, raised to head
-- height. Ending the switch on exactly this point makes the hand-back to the
-- normal camera seamless instead of a snap.
local function subjectFocus(hum, root)
	local offset
	if hum.RigType == Enum.HumanoidRigType.R15 then
		if hum.AutomaticScalingEnabled then
			offset = Vector3.new(0, 1.5 + (root.Size.Y - 2) * 0.5, 0)
		else
			offset = Vector3.new(0, 2, 0)
		end
	else
		offset = Vector3.new(0, 1.5, 0)
	end
	return root.Position + root.CFrame:VectorToWorldSpace(offset + hum.CameraOffset)
end

local function flatHeading(root)
	local v = root.CFrame.LookVector
	local flat = Vector3.new(v.X, 0, v.Z)
	if flat.Magnitude < 1e-3 then return Vector3.new(0, 0, -1) end
	return flat.Unit
end

local function rotateY(v, deg)
	return CFrame.Angles(0, math.rad(deg), 0):VectorToWorldSpace(v)
end

-- One aerial shot: `height` above the focus, turned `turn` degrees, leaning
-- back a little so the frame reads as a city and not a map, shifted by `pan`.
local function aerialShot(focus, heading, height, turn, pan)
	local h      = rotateY(heading, turn)
	local target = focus + pan
	local pos    = target + Vector3.new(0, height, 0) - h * (height * SWITCH.LEAN)
	return CFrame.lookAt(pos, target, h)       -- top of the screen = the way you face
end

-- The shot Roblox's default camera would take: behind the character, pitched
-- down a touch, at its normal zoom.
local function gameplayShot(hum, root)
	local focus = subjectFocus(hum, root)
	local dist  = SWITCH.FINAL_DISTANCE
		or math.clamp(12.5, player.CameraMinZoomDistance, player.CameraMaxZoomDistance)
	local look  = (CFrame.lookAt(Vector3.zero, flatHeading(root))
		* CFrame.Angles(math.rad(SWITCH.FINAL_PITCH), 0, 0)).LookVector
	local pos   = focus - look * dist
	return CFrame.lookAt(pos, pos + look)
end

local function playSound(id)
	if not id or id == "" then return end
	local s = Instance.new("Sound")
	s.SoundId, s.Volume = id, SWITCH.SOUND_VOLUME
	s.Parent = SoundService
	s:Play()
	s.Ended:Connect(function() s:Destroy() end)
	task.delay(10, function() if s.Parent then s:Destroy() end end)
end

-- ─── HUD AND CONTROLS ────────────────────────────────────────────────────────
local hiddenGuis, hiddenCore, guiConn = {}, {}, nil
local hudHidden = false   -- a deferred hide must never land after the HUD is back
local CORE_TYPES = {
	Enum.CoreGuiType.Chat, Enum.CoreGuiType.Backpack, Enum.CoreGuiType.PlayerList,
	Enum.CoreGuiType.Health, Enum.CoreGuiType.EmotesMenu,
}

local function hideHud()
	if not SWITCH.HIDE_HUD then return end
	hudHidden = true
	local function hide(g)
		if hudHidden and g:IsA("ScreenGui") and g ~= screen and g.Enabled then
			g.Enabled = false
			local entry = { gui = g }
			-- If game code turns it on during the switch, that is its call: stop
			-- managing it, and don't touch it at the end.
			entry.conn = g:GetPropertyChangedSignal("Enabled"):Connect(function()
				if g.Enabled then
					entry.released = true
					entry.conn:Disconnect()
				end
			end)
			table.insert(hiddenGuis, entry)
		end
	end
	for _, g in ipairs(playerGui:GetChildren()) do hide(g) end
	-- Anything that loads mid-switch. Checked a frame later, so a script that
	-- parents a gui and then switches it off itself is left switched off.
	guiConn = playerGui.ChildAdded:Connect(function(g)
		task.defer(function()
			if g.Parent == playerGui then hide(g) end
		end)
	end)
	for _, t in ipairs(CORE_TYPES) do
		local ok, on = pcall(function() return StarterGui:GetCoreGuiEnabled(t) end)
		if ok and on and pcall(function() StarterGui:SetCoreGuiEnabled(t, false) end) then
			table.insert(hiddenCore, t)
		end
	end
end

local function showHud()
	hudHidden = false
	if guiConn then guiConn:Disconnect(); guiConn = nil end
	for _, entry in ipairs(hiddenGuis) do
		if entry.conn then entry.conn:Disconnect() end
		if not entry.released and entry.gui.Parent then entry.gui.Enabled = true end
	end
	table.clear(hiddenGuis)
	for _, t in ipairs(hiddenCore) do
		pcall(function() StarterGui:SetCoreGuiEnabled(t, true) end)
	end
	table.clear(hiddenCore)
end

local controls = nil
local function setControls(enabled)
	if not SWITCH.LOCK_CONTROLS then return end
	if not controls then
		local ok, mod = pcall(function()
			local ps = player:WaitForChild("PlayerScripts", 5)
			local pm = ps and ps:WaitForChild("PlayerModule", 5)
			return pm and require(pm)
		end)
		if ok and mod then
			local okC, c = pcall(function() return mod:GetControls() end)
			if okC then controls = c end
		end
	end
	if controls then
		pcall(function()
			if enabled then controls:Enable() else controls:Disable() end
		end)
	end
end

-- ─── THE SWITCH ──────────────────────────────────────────────────────────────
-- Runs with the loading screen still up for its first frame, so the very
-- first thing the player sees is the sky shot.
local function runSwitch(char)
	local hum  = char:FindFirstChildWhichIsA("Humanoid")
	local root = char:FindFirstChild("HumanoidRootPart")
	camera = workspace.CurrentCamera
	if not (hum and root and camera) then lift(); return end

	local heights = SWITCH.HEIGHTS
	local n       = #heights
	local baseFov = camera.FieldOfView

	local blur = Instance.new("BlurEffect")
	blur.Name, blur.Size = "ArrivalBlur", 2
	blur.Parent = Lighting
	local grade = Instance.new("ColorCorrectionEffect")
	grade.Name = "ArrivalGrade"
	grade.Saturation, grade.TintColor = SWITCH.AERIAL_SATURATION, SWITCH.AERIAL_TINT
	grade.Parent = Lighting

	local finished = false
	local function finish()
		if finished then return end
		finished = true
		-- Hand back to the normal camera from exactly where it would be.
		pcall(function()
			if hum.Parent then
				camera.CameraSubject = hum
				if root.Parent then camera.CFrame = gameplayShot(hum, root) end
			end
		end)
		camera.FieldOfView = baseFov
		camera.CameraType  = Enum.CameraType.Custom
		blur:Destroy(); grade:Destroy()
		showHud()
		setControls(true)
		lift()                                        -- in case it never lifted
	end

	-- Stops if the character dies, is replaced or is removed mid-switch.
	local function stillHere()
		return char.Parent ~= nil and player.Character == char
			and hum.Parent ~= nil and hum.Health > 0 and root.Parent ~= nil
	end

	local ok, err = pcall(function()
		hideHud()
		setControls(false)

		local focus   = subjectFocus(hum, root)
		local heading = flatHeading(root)
		-- Start turned by exactly what the drops and drift will undo, so the
		-- last aerial shot already faces the way the character does.
		local turn    = SWITCH.TURN_PER_STOP * (n - 1)
			+ SWITCH.DRIFT * (SWITCH.FIRST_HOLD + SWITCH.HOLD_TIME * (n - 1))
		local pan0    = (SWITCH.PAN_IN > 0)
			and rotateY(heading, 90) * SWITCH.PAN_IN or Vector3.zero

		camera.CameraType  = Enum.CameraType.Scriptable
		camera.CFrame      = aerialShot(focus, heading, heights[1], turn, pan0)
		RunService.RenderStepped:Wait()

		-- Every frame of the switch goes through here: shot, jolt, lens.
		local shakeAt = -1
		local function draw(cf, fov)
			local jolt = CFrame.new()
			if shakeAt >= 0 then
				local t = os.clock() - shakeAt
				local amp = SWITCH.LAND_SHAKE * math.exp(-t * 12)
				if amp > 0.01 then
					jolt = CFrame.Angles(math.rad(amp * math.sin(t * 55)),
						math.rad(amp * 0.6 * math.cos(t * 47)), 0)
				end
			end
			camera.CFrame = cf * jolt
			camera.FieldOfView = fov or baseFov
		end

		-- Run `step(alpha, dt)` over `duration` seconds, one call per frame.
		local function over(duration, step)
			local t0, last = os.clock(), os.clock()
			while true do
				if not stillHere() then return false end
				local now = os.clock()
				local a = (duration > 0) and math.clamp((now - t0) / duration, 0, 1) or 1
				step(a, now - last)
				last = now
				if a >= 1 then return true end
				RunService.RenderStepped:Wait()
			end
		end

		-- 1. The sky shot. The screen fades in on it while it slides over you.
		lift()
		if not over(SWITCH.FIRST_HOLD, function(a, dt)
				turn = turn - SWITCH.DRIFT * dt
				local e = ease(a, Enum.EasingStyle.Sine, Enum.EasingDirection.Out)
				draw(aerialShot(focus, heading, heights[1], turn, pan0 * (1 - e)))
			end) then return end

		-- 2. Drop, land, hold — down through each stop.
		for i = 2, n do
			local fromH, toH = heights[i - 1], heights[i]
			local fromTurn, toTurn = turn, turn - SWITCH.TURN_PER_STOP
			playSound(SWITCH.WHOOSH_SOUND)
			if not over(SWITCH.DROP_TIME, function(a)
					local e     = ease(a, Enum.EasingStyle.Quint)
					local speed = math.sin(math.pi * a)          -- 0 → 1 → 0 across the drop
					turn = fromTurn + (toTurn - fromTurn) * e
					draw(aerialShot(focus, heading, fromH + (toH - fromH) * e, turn, Vector3.zero),
						baseFov + SWITCH.FOV_PUNCH * speed)
					blur.Size = 2 + SWITCH.BLUR_MAX * speed
				end) then return end
			playSound(SWITCH.LAND_SOUND)
			shakeAt = os.clock()
			blur.Size = 2
			if not over(SWITCH.HOLD_TIME, function(_, dt)
					turn = turn - SWITCH.DRIFT * dt
					draw(aerialShot(focus, heading, toH, turn, Vector3.zero))
				end) then return end
		end

		-- 3. Swoop down behind the character; colour comes back on the way.
		local startCf = camera.CFrame
		shakeAt = -1
		playSound(SWITCH.WHOOSH_SOUND)
		if not over(SWITCH.FINAL_TIME, function(a)
				local e = ease(a, Enum.EasingStyle.Cubic)
				draw(startCf:Lerp(gameplayShot(hum, root), e))
				grade.Saturation = SWITCH.AERIAL_SATURATION * (1 - e)
				grade.TintColor  = SWITCH.AERIAL_TINT:Lerp(Color3.new(1, 1, 1), e)
				blur.Size        = 2 * (1 - e)
			end) then return end
	end)
	if not ok then warn("[Arrival] Switch interrupted: " .. tostring(err)) end
	finish()
end

-- ─── WAIT ────────────────────────────────────────────────────────────────────
task.spawn(function()
	setStatus("LOADING THE BLOCK...")
	if not game:IsLoaded() then
		game.Loaded:Wait()
	end

	setStatus("BUILDING YOUR CHARACTER...")
	local slowShown = false
	while not done do
		local waited = os.clock() - shownAt
		local char = player.Character
		if characterReady(char) and waited >= CONFIG.MIN_SHOW then
			-- One more beat so the first frame you see has the body settled.
			task.wait(0.25)
			if SWITCH.ENABLED and #SWITCH.HEIGHTS > 0 and player.Character == char then
				runSwitch(char)
			else
				lift()
			end
			break
		end
		if waited >= CONFIG.TIMEOUT then
			warn("[Arrival] Character was not ready after " .. CONFIG.TIMEOUT ..
				"s — lifting the loading screen anyway. Check MainGame_Server's Output.")
			lift()
			break
		end
		if not slowShown and waited >= CONFIG.SLOW_AFTER then
			slowShown = true
			setStatus("TAKING LONGER THAN USUAL...")
		end
		task.wait(0.1)
	end
end)
