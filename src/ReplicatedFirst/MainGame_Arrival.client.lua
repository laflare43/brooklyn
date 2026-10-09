--[[
    MainGame_Arrival.lua  (v1)
    LocalScript inside ReplicatedFirst   ── MAIN GAME

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

local CONFIG = {
	TITLE       = "CONNECTING TO SERVER",   -- keep in step with LOADING_TITLE in CharCreation_Client
	MIN_SHOW    = 1.0,    -- seconds the screen stays up at the least, so it never just blinks
	SLOW_AFTER  = 15,     -- seconds before the status says it is taking a while
	TIMEOUT     = 30,     -- seconds before it lifts no matter what
	FADE        = 0.6,    -- fade-out length in seconds
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
		if characterReady(player.Character) and waited >= CONFIG.MIN_SHOW then
			-- One more beat so the first frame you see has the body settled.
			task.wait(0.25)
			lift()
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
