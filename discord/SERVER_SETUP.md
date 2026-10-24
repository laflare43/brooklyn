# Discord server setup — "THE BLOCK" (Brooklyn roleplay)

Rename "THE BLOCK" to your game's real name wherever it appears. The six neighborhoods come
from your character-creation lobby (Brownsville Houses, Unity Plaza Houses, Tilden Houses,
Marcus Garvey Village, VanD, Genesis Homes), so players can pick the one their character is from.

Total setup time: about 30–45 minutes. Follow the numbered order at the bottom.

---

## 1. Create the server

1. Discord → **+** (Add a Server) → **Create My Own** → **For a club or community**.
2. Name: `THE BLOCK` (or your game name). Upload an icon (the red/black look of your loading screen works well).
3. **Server Settings → Enable Community** (it asks for a rules channel and an updates channel; use the ones below).
4. **Server Settings → Safety Setup**
   - Verification level: **Medium** (account older than 5 minutes and a verified email). Raise it to **High** if you get raids.
   - Explicit media content filter: **Scan media content from all members**.
   - Require **2FA for moderator actions** (turn it on once your staff are in).
5. **Server Settings → Roles → @everyone**: turn **off** Mention @everyone/@here/All Roles, Create Invite, Embed Links and Attach Files for now. Verified members get those back (see roles).

---

## 2. Roles (top to bottom — order matters in Discord)

| Role | Colour | Who | Key permissions |
|---|---|---|---|
| **Founder** | gold | you | Administrator |
| **Admin** | red | trusted leads | Manage Server/Roles/Channels, Kick, Ban, Manage Messages, Mention Everyone |
| **Developer** | blue | scripters/builders | View all dev + staff channels, Manage Messages in dev/bug channels |
| **Moderator** | green | moderators | Kick, Ban, Timeout, Manage Messages, View Audit Log, Move Members |
| **Support** | teal | helpers | Timeout, Manage Messages in #help and ticket channels |
| **Bots** | grey | bots | only what each bot needs |
| **Content Creator** | purple | streamers/YouTubers (approve by hand) | Embed Links, Attach Files, post in #media |
| **Server Booster** | pink | automatic | cosmetic |
| **Brownsville Houses** | #b91c1c | neighborhood pick | cosmetic + view its channel |
| **Unity Plaza Houses** | #1d4ed8 | neighborhood pick | cosmetic + view its channel |
| **Tilden Houses** | #15803d | neighborhood pick | cosmetic + view its channel |
| **Marcus Garvey Village** | #a16207 | neighborhood pick | cosmetic + view its channel |
| **VanD** | #7e22ce | neighborhood pick | cosmetic + view its channel |
| **Genesis Homes** | #0e7490 | neighborhood pick | cosmetic + view its channel |
| **Verified** | white | linked Roblox account | View most channels, Send Messages, Embed Links, Attach Files, Add Reactions, Use External Emoji, Connect/Speak |
| **Muted** | dark grey | punishments | deny Send Messages, Add Reactions, Speak in every category |

Ping roles (members opt in through Onboarding, no permissions): `Updates`, `Events`, `Giveaways`, `Looking for RP`.

---

## 3. Categories and channels

`🔒` = read-only for everyone (staff only can post). `✅` = Verified members only. `👮` = staff only.

### 📌 START HERE
| Channel | Visible to | Purpose |
|---|---|---|
| 🔒 `#welcome` | everyone | what the game is, how to join, links to the Roblox page |
| 🔒 `#rules` | everyone | the rules (draft in section 5) — set as the Community rules channel |
| 🔒 `#verify` | everyone | link your Roblox account (section 6) |
| 🔒 `#get-roles` | ✅ | pick neighborhood and ping roles (Onboarding does this too) |
| 🔒 `#faq` | everyone | how to play, how to report, how to apply for staff |

### 📣 NEWS
| Channel | Purpose |
|---|---|
| 🔒 `#announcements` | big news (set as the Community updates channel) |
| 🔒 `#update-log` | patch notes for each game update |
| 🔒 `#server-status` | maintenance, outages, restarts |
| 🔒 `#polls` | community votes |
| 🔒 `#events` | scheduled RP events, giveaways |

### 💬 COMMUNITY (✅)
| Channel | Purpose |
|---|---|
| `#general` | main chat (slowmode 5 s) |
| `#introductions` | say hi |
| `#media` | screenshots and clips (Content Creator + Verified, embeds on) |
| `#memes` | memes, keep it clean |
| `#off-topic` | everything else |
| `#suggestions` | forum channel; tags: Gameplay, Map, Jobs, Vehicles, Other |

### 🎭 ROLEPLAY (✅)
| Channel | Purpose |
|---|---|
| `#character-creations` | forum channel; players post their character (name, age, neighborhood, background) |
| `#rp-stories` | forum channel for ongoing storylines |
| `#looking-for-rp` | find people to RP with (ping `Looking for RP`) |
| `#brownsville-houses` | only that role (and staff) can see it |
| `#unity-plaza-houses` | only that role |
| `#tilden-houses` | only that role |
| `#marcus-garvey-village` | only that role |
| `#vand` | only that role |
| `#genesis-homes` | only that role |

### 🎮 IN-GAME (✅)
| Channel | Purpose |
|---|---|
| `#game-chat` | talk about the game while playing |
| `#lfg` | get a group, share a private server code (never post your Roblox cookie or password) |
| `#clips` | game clips |

### 🛟 SUPPORT
| Channel | Purpose |
|---|---|
| `#help` | ✅ questions; Support answers |
| `#bug-reports` | ✅ forum channel; tags: Map, Character Creator, Teleport, Crash, Other; template: what happened, what you expected, steps, screenshot |
| `#player-reports` | ✅ post-only form (a ticket bot is better; see section 6) |
| `#ban-appeals` | ✅ ticket-based, only the author and staff see each appeal |

### 🔊 VOICE (✅)
`Lounge`, `Roleplay 1`, `Roleplay 2`, `Roleplay 3`, `AFK` (idle timeout 15 min). Optionally one Stage channel for events.

### 👮 STAFF (private; Founder, Admin, Moderator, Developer, Support)
`#staff-chat`, `#staff-announcements`, `#mod-log`, `#automod-alerts`, `#reports-review`,
`#dev-chat` (Developer + Admin only), `#bug-triage` (Developer only), `#staff-voice`.

---

## 4. Onboarding (Server Settings → Onboarding)

Default channels to show new members: `#welcome`, `#rules`, `#verify`, `#general`.

**Question 1 — "Which neighborhood is your character from?"** (single choice)
Brownsville Houses · Unity Plaza Houses · Tilden Houses · Marcus Garvey Village · VanD · Genesis Homes · I don't have a character yet
(each answer assigns the matching role; the last answer assigns nothing and points to `#faq`)

**Question 2 — "What do you want to be pinged for?"** (multiple choice)
Game updates → `Updates` · Events → `Events` · Giveaways → `Giveaways` · Looking for RP → `Looking for RP`

---

## 5. Rules (paste into `#rules`; edit to taste)

1. **Respect everyone.** No harassment, hate speech, slurs, or targeted insults. Roleplay is fiction; do not use it as cover to attack real people.
2. **No NSFW, gore or shock content.** Many players are teenagers. Keep it clean.
3. **No threats, doxxing, or sharing personal information** (yours or anyone's).
4. **Keep roleplay in character channels and out of real life.** Do not use the game to glorify real gangs, real crimes, or real victims.
5. **No Fail RP and respect the New Life Rule.** If your character dies or is arrested, your next life does not remember it.
6. **No exploiting, cheating, or bug abuse.** Report bugs in `#bug-reports`; do not share exploits.
7. **No scams, trading for real money, account selling, or asking for passwords or cookies.**
8. **No spam, mass pings, or advertising** (other servers, games, social media) without staff permission.
9. **Use the right channel.** Reports go in `#player-reports`; do not call people out publicly.
10. **Follow Discord's Terms and Community Guidelines and Roblox's Terms of Use.** You must be 13 or older to use Discord.
11. **Staff decisions can be appealed once** in `#ban-appeals`. Arguing with staff in public channels is not an appeal.

Punishment ladder (put this in `#faq` or `#staff-chat`): warning → 1-hour timeout → 24-hour timeout → 7-day timeout → ban. Skip steps for threats, doxxing, NSFW, or raids.

---

## 6. Bots and AutoMod

**AutoMod (built into Discord; Server Settings → AutoMod)**
- Block commonly flagged words (turn on all three keyword presets: Profanity, Sexual Content, Slurs).
- Block mention spam (limit: 5 mentions per message).
- Block spam content.
- Send alerts to `#automod-alerts`.

**Roblox verification (links a member's Discord to their Roblox account)**
Add a Roblox-verification bot such as **Bloxlink** or **RoVer**, set the verified role to `Verified`, and send members to `#verify`. Both are free for basic use.

**Logging and moderation**
A moderation bot such as **Carl-bot** or **Dyno** covers logging (join/leave, message edits and deletes, bans) into `#mod-log`, plus reaction roles if you want them as well as Onboarding.

**Tickets** (for `#player-reports` and `#ban-appeals`)
A ticket bot such as **Ticket Tool** or **Tickets v2** that opens a private channel per report. Only the reporter and staff can see it.

I can't tell you which bots are best for you long term. Check each one's current permissions before inviting it: give a bot only what it needs, and never give a bot Administrator.

**Welcome message** (paste into `#welcome`)
> Welcome to **THE BLOCK** — a Brooklyn roleplay game set in East New York.
> 1. Read `#rules`
> 2. Link your Roblox account in `#verify`
> 3. Pick your neighborhood in `#get-roles`
> 4. Say hi in `#introductions`
> Game link: *(paste your Roblox game link)*

---

## 7. Setup order (checklist)

1. Create the server, name it, set the icon.
2. Create the roles (section 2), drag them into the order shown, and set the permissions.
3. Create the categories and channels (section 3); set each category's permissions first, then override per channel.
4. Create `#rules` and `#announcements`, then enable Community.
5. Turn on the Safety settings and AutoMod.
6. Add the verification bot and the moderation and ticket bots; test with a second account (alt account in an incognito window).
7. Set up Onboarding (section 4).
8. Post the rules, FAQ, and welcome message.
9. Invite staff, give them roles, then turn on 2FA-for-moderation.
10. Test everything as a brand-new account before you share the invite link. Check that a new member sees only the START HERE channels until verified.

---

## 8. Safety notes

- Roblox games draw a lot of younger players. Keep NSFW off, keep staff and minors out of private DMs for moderation (use tickets), and never ask a member for personal information.
- Read Discord's current moderation guidance for community servers (the "Discord Moderator Academy" and Safety Center pages); I'm summarising from memory and the policies change.
