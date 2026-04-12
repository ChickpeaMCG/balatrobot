--- STEAMODDED HEADER
--- MOD_NAME: Balatrobot
--- MOD_ID: Balatrobot-v0.3
--- MOD_AUTHOR: [Besteon]
--- MOD_DESCRIPTION: A botting API for Balatro

local mod_path = SMODS.current_mod.path

-- Load the mod configuration
assert(load(NFS.read(mod_path .. "config.lua")))()
if not BALATRO_BOT_CONFIG.enabled then
	return
end

-- External libraries
assert(load(NFS.read(mod_path .. "lib/list.lua")))()
assert(load(NFS.read(mod_path .. "lib/hook.lua")))()
assert(load(NFS.read(mod_path .. "lib/bitser.lua")))()
assert(load(NFS.read(mod_path .. "lib/sock.lua")))()
assert(load(NFS.read(mod_path .. "lib/json.lua")))()

-- Mod specific files
assert(load(NFS.read(mod_path .. "src/utils.lua")))()
assert(load(NFS.read(mod_path .. "src/bot.lua")))()
assert(load(NFS.read(mod_path .. "src/middleware.lua")))()
assert(load(NFS.read(mod_path .. "src/botlogger.lua")))()
assert(load(NFS.read(mod_path .. "src/api.lua")))()

sendDebugMessage("Balatrobot v0.3 loaded")

Middleware.hookbalatro()

Botlogger.path = mod_path
Botlogger.init()
BalatrobotAPI.init()
