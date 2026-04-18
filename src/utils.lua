
Utils = { }

function Utils.getCardData(card)
    local _card = { }

    _card.label = card.label
    _card.name = card.config.card and card.config.card.name or nil
    _card.suit = card.config.card and card.config.card.suit or nil
    _card.value = card.config.card and card.config.card.value or nil
    _card.card_key = card.config.card_key or nil

    -- Enhancement (Wild, Bonus, Mult, Glass, Steel, Stone, Gold, Lucky)
    if card.ability and card.ability.name then
        _card.enhancement = card.ability.name
    end

    -- Edition (foil, holographic, polychrome, negative)
    if card.edition then
        for k, v in pairs(card.edition) do
            if v == true then
                _card.edition = k
                break
            end
        end
    end

    -- Seal (Gold, Red, Blue, Purple)
    if card.seal then
        _card.seal = card.seal
    end

    -- Permanent bonus chips from enhancement
    if card.ability and card.ability.perma_bonus then
        _card.bonus_chips = card.ability.perma_bonus
    end

    return _card
end

function Utils.getJokerData(card)
    local _joker = { }

    _joker.label = card.label
    _joker.key = card.config.center and card.config.center.key or nil
    _joker.name = card.config.center and card.config.center.name or nil
    _joker.sell_cost = card.sell_cost or 0
    _joker.eternal = card.ability and card.ability.eternal or false
    _joker.perishable = card.ability and card.ability.perishable or false
    _joker.rental = card.ability and card.ability.rental or false

    -- Edition
    if card.edition then
        for k, v in pairs(card.edition) do
            if v == true then
                _joker.edition = k
                break
            end
        end
    end

    -- Extra joker-specific state (e.g. mult counters, chip counters)
    if card.ability then
        if card.ability.mult and card.ability.mult ~= 0 then
            _joker.extra_mult = card.ability.mult
        end
        if card.ability.chips and card.ability.chips ~= 0 then
            _joker.extra_chips = card.ability.chips
        end
        if card.ability.extra then
            _joker.extra = card.ability.extra
        end
    end

    return _joker
end

function Utils.getDeckData()
    local _deck = { }

    if G and G.deck and G.deck.cards then
        for i = 1, #G.deck.cards do
            _deck[i] = Utils.getCardData(G.deck.cards[i])
        end
    end

    return _deck
end

function Utils.getHandData()
    local _hand = { }

    if G and G.hand and G.hand.cards then
        for i = 1, #G.hand.cards do
            _hand[i] = Utils.getCardData(G.hand.cards[i])
        end
    end

    return _hand
end

function Utils.getJokersData()
    local _jokers = { }

    if G and G.jokers and G.jokers.cards then
        for i = 1, #G.jokers.cards do
            _jokers[i] = Utils.getJokerData(G.jokers.cards[i])
        end
    end

    return _jokers
end

function Utils.getConsumablesData()
    local _consumables = { }

    if G and G.consumeables and G.consumeables.cards then
        for i = 1, #G.consumeables.cards do
            local _card = Utils.getCardData(G.consumeables.cards[i])
            _card.key = G.consumeables.cards[i].config.center and G.consumeables.cards[i].config.center.key or nil
            _card.consumable_name = G.consumeables.cards[i].config.center and G.consumeables.cards[i].config.center.name or nil
            _consumables[i] = _card
        end
    end

    return _consumables
end

function Utils.getBlindData()
    local _blinds = { }

    if G and G.GAME then
        _blinds.ondeck = G.GAME.blind_on_deck

        if G.GAME.blind then
            _blinds.chips_needed = G.GAME.blind.chips
            _blinds.name        = G.GAME.blind.name
            _blinds.boss        = G.GAME.blind.boss or false
        end
    end

    return _blinds
end

function Utils.getAnteData()
    local _ante = { }
    _ante.ante   = G and G.GAME and G.GAME.round_resets and G.GAME.round_resets.ante or nil
    _ante.blinds = Utils.getBlindData()
    return _ante
end

function Utils.getBackData()
    local _back = { }

    if G and G.GAME and G.GAME.selected_back then
        _back.key  = G.GAME.selected_back.key
        _back.name = G.GAME.selected_back.name
    end

    return _back
end

function Utils.getShopData()
    local _shop = { }
    if not G or not G.shop then return _shop end

    _shop.reroll_cost = G.GAME.current_round.reroll_cost
    _shop.cards       = { }
    _shop.boosters    = { }
    _shop.vouchers    = { }

    for i = 1, #G.shop_jokers.cards do
        local _card = Utils.getJokerData(G.shop_jokers.cards[i])
        _card.cost = G.shop_jokers.cards[i].cost
        _shop.cards[i] = _card
    end

    for i = 1, #G.shop_booster.cards do
        local _card = { }
        _card.key  = G.shop_booster.cards[i].config.center and G.shop_booster.cards[i].config.center.key or nil
        _card.name = G.shop_booster.cards[i].config.center and G.shop_booster.cards[i].config.center.name or nil
        _card.cost = G.shop_booster.cards[i].cost
        _shop.boosters[i] = _card
    end

    for i = 1, #G.shop_vouchers.cards do
        local _card = { }
        _card.key  = G.shop_vouchers.cards[i].config.center and G.shop_vouchers.cards[i].config.center.key or nil
        _card.name = G.shop_vouchers.cards[i].config.center and G.shop_vouchers.cards[i].config.center.name or nil
        _card.cost = G.shop_vouchers.cards[i].cost
        _shop.vouchers[i] = _card
    end

    return _shop
end

function Utils.getGameData()
    local _game = { }

    if G and G.STATE then
        _game.state               = G.STATE
        _game.num_hands_played    = G.GAME.hands_played
        _game.num_skips           = G.GAME.skips
        _game.round               = G.GAME.round
        _game.discount_percent    = G.GAME.discount_percent
        _game.interest_cap        = G.GAME.interest_cap
        _game.inflation           = G.GAME.inflation
        _game.dollars             = G.GAME.dollars
        _game.max_jokers          = G.GAME.max_jokers
        _game.bankrupt_at         = G.GAME.bankrupt_at
        _game.seed                = G.GAME.pseudorandom and tostring(G.GAME.pseudorandom.seed) or nil
    end

    return _game
end

function Utils.getHandScoreData()
    local _handscores = { }

    if G and G.GAME and G.GAME.hands then
        for k, v in pairs(G.GAME.hands) do
            _handscores[k] = {
                level  = v.level,
                chips  = v.chips,
                mult   = v.mult,
                order  = v.order,
            }
        end
    end

    return _handscores
end

function Utils.getTagsData()
    local _tags = { }

    if G and G.GAME and G.GAME.tags then
        for i = 1, #G.GAME.tags do
            _tags[i] = {
                key  = G.GAME.tags[i].key,
                name = G.GAME.tags[i].name,
            }
        end
    end

    return _tags
end

function Utils.getRoundData()
    local _current_round = { }

    if G and G.GAME and G.GAME.current_round then
        _current_round.discards_left = G.GAME.current_round.discards_left
        _current_round.hands_left    = G.GAME.current_round.hands_left
        _current_round.reroll_cost   = G.GAME.current_round.reroll_cost
    end

    return _current_round
end

function Utils.getGamestate()
    local _gamestate = { }

    _gamestate = Utils.getGameData()

    _gamestate.deckback     = Utils.getBackData()
    _gamestate.deck         = Utils.getDeckData()
    _gamestate.hand         = Utils.getHandData()
    _gamestate.jokers       = Utils.getJokersData()
    _gamestate.consumables  = Utils.getConsumablesData()
    _gamestate.ante         = Utils.getAnteData()
    _gamestate.shop         = Utils.getShopData()
    _gamestate.handscores   = Utils.getHandScoreData()
    _gamestate.tags         = Utils.getTagsData()
    _gamestate.current_round = Utils.getRoundData()

    return _gamestate
end

function Utils.parseaction(data)
    -- Protocol is ACTION|arg1|arg2
    action = data:match("^([%a%u_]*)")
    params = data:match("|(.*)")

    if action then
        local _action = Bot.ACTIONS[action]

        if not _action then
            return nil
        end

        local _actiontable = { }
        _actiontable[1] = _action

        if params then
            local _i = 2
            for _arg in params:gmatch("[%w%s,]+") do
                local _splitstring = { }
                local _j = 1
                for _str in _arg:gmatch('([^,]+)') do
                    _splitstring[_j] = tonumber(_str) or _str
                    _j = _j + 1
                end
                _actiontable[_i] = _splitstring
                _i = _i + 1
            end
        end

        return _actiontable
    end
end

Utils.ERROR = {
    NOERROR = 1,
    NUMPARAMS = 2,
    MSGFORMAT = 3,
    INVALIDACTION = 4,
}

function Utils.validateAction(action)
    if action and #action > 1 and #action > Bot.ACTIONPARAMS[action[1]].num_args then
        return Utils.ERROR.NUMPARAMS
    elseif not action then
        return Utils.ERROR.MSGFORMAT
    else
        if not Bot.ACTIONPARAMS[action[1]].isvalid(action) then
            return Utils.ERROR.INVALIDACTION
        end
    end

    return Utils.ERROR.NOERROR
end

function Utils.isTableUnique(table)
    if table == nil then return true end

    local _seen = { }
    for i = 1, #table do
        if _seen[table[i]] then return false end
        _seen[table[i]] = table[i]
    end

    return true
end

function Utils.isTableInRange(table, min, max)
    if table == nil then return true end

    for i = 1, #table do
        if table[i] < min or table[i] > max then return false end
    end
    return true
end

return Utils
