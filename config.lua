local SPEED_PROFILES = {
    fast = {
        dt = 8.0/60.0,
        uncap_fps = true,
        instant_move = true,
        disable_vsync = true,
        frame_ratio = 100,
        disable_card_eval_status_text = true,
    },
    watch = {
        dt = false,
        uncap_fps = false,
        instant_move = false,
        disable_vsync = false,
        frame_ratio = 1,
        disable_card_eval_status_text = false,
    },
}

local speed = arg[2] or "watch"
local profile = SPEED_PROFILES[speed] or SPEED_PROFILES["fast"]

BALATRO_BOT_CONFIG = {
    enabled = true, -- Disables ALL mod functionality if false
    port = '12345', -- Port for the bot to listen on, overwritten by arg[1]
    dt = profile.dt,
    uncap_fps = profile.uncap_fps,
    instant_move = profile.instant_move,
    disable_vsync = profile.disable_vsync,
    frame_ratio = profile.frame_ratio,
    disable_card_eval_status_text = profile.disable_card_eval_status_text,
}

return BALATRO_BOT_CONFIG