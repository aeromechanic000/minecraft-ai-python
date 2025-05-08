
from model import *
from world import *
from utils import *

def get_entity_position(entity) : 
    pos = None
    if entity is not None : 
        pos = entity.position
    return pos

def get_nearest_blocks(agent, block_names = None, max_distance = 64, count = 16) :
    block_ids = []
    if block_names is None or not isinstance(block_names, list) : 
        block_ids = get_all_block_ids(ignore = get_empty_block_names())
    else : 
        for block_name in block_names :
            block_id = get_block_id(block_name)
            if block_id is not None : 
                block_ids.append(block_id)
    blocks = []
    positions = agent.bot.findBlocks({"matching" : block_ids, "maxDistance" : max_distance, "count" : count})
    agent_pos = get_entity_position(agent.bot.entity)
    if agent_pos is not None : 
        for i in range(positions.length) : 
            block = agent.bot.blockAt(positions[i])
            dist = positions[i].distanceTo(agent_pos)
            blocks.append({"block" : block, "distance" : dist})
    blocks = sorted(blocks, key = functools.cmp_to_key(lambda a, b : a["distance"] - b["distance"]))
    return [block["block"] for block in blocks]

def get_nearest_block(agent, block_name, max_distance = 64) :
    blocks = get_nearest_blocks(agent, block_names = [block_name], max_distance = max_distance, count = 1)
    if len(blocks) > 0 :
        return blocks[0]
    return None 

def get_nearest_item(agent, distance = 1) : 
    entity = None 
    agent_pos = get_entity_position(agent.bot.entity)
    if agent_pos is not None : 
        entity = agent.bot.nearestEntity(lambda et : et.name == 'item' and et.position is not None and agent_pos.distanceTo(et.position) < distance)
    return entity

def search_block(agent, block_name, range = 64, min_distance = 2) :
    range = min(512, range)
    block = get_nearest_block(agent, block_name, range)
    if block is None :
        agent.bot.chat("I can't find any %s in %s blocks." % (get_block_display_name(get_block_id(block_name)), math.floor(range)))
        return False
    agent.bot.chat("Found %s at %s. I am going there." % (get_block_display_name(get_block_id(block_name)), block.position))
    go_to_position(agent, block.position.x, block.position.y, block.position.z, min_distance)
    return True

def get_nearest_entity_where(agent, predicate, max_distance) : 
    entity = None
    agent_pos = get_entity_position(agent.bot.entity)
    if agent_pos is not None : 
        entity = agent.bot.nearestEntity(lambda et : predicate(et) and et.position is not None and agent_pos.distanceTo(et.position) < max_distance)
    return entity

def get_nearest_entities(agent, max_distance = 32, count = 16) : 
    entities = []
    for entity_id in agent.bot.entities :
        entity = agent.bot.entities[entity_id]
        entity_pos = get_entity_position(entity) 
        agent_pos = get_entity_position(agent.bot.entity)
        if entity_pos is not None and agent_pos is not None :
            distance = entity_pos.distanceTo(agent_pos)
            if distance > max_distance: continue
            entities.append({"entity" : entity, "distance" : distance})
        if len(entities) >= count : 
            break
    entities = sorted(entities, key = functools.cmp_to_key(lambda a, b : a["distance"] - b["distance"]))
    return [entity["entity"] for entity in entities]

def get_nearest_freespace(agent, size = 1, distance = 8) :
    empty_pos = agent.bot.findBlocks({
        "matching" : lambda block : block is not None and block.name in get_empty_block_names(),
        "maxDistance" : distance,
        "count" : 1000,
    })
    for i in range(len(empty_pos)) :
        empty = True
        for x in range(size) :
            for z in range(size) : 
                top = agent.bot.blockAt(empty_pos[i].offset(x, 0, z))
                bottom = agent.bot.blockAt(empty_pos[i].offset(x, -1, z))
                if top is None or top.name not in get_empty_block_names() or bottom is None or bottom.drops.length < 1 or not bottom.diggable :
                    empty = False
                    break
            if empty is None :
                break
        if empty == True :
            return empty_pos[i]
    return None

def search_entity(agent, entity_name, range = 64, min_distance = 2) :
    entity = get_nearest_entity_where(agent, lambda et : et.name == entity_name, range)
    if entity is None :
        agent.bot.chat("I can't find any %s in %s blocks." % (get_entity_display_name(get_entity_id(entity_name)), math.floor(range)))
        return False
    agent_pos = get_entity_position(agent.bot.entity)
    entity_pos = get_entity_position(entity)
    if agent_pos is not None and entity_pos is not None :
        distance = agent_pos.distanceTo(entity_pos)
        agent.bot.chat("Found %s %s blocks away. I am going there." % (get_entity_display_name(get_entity_id(entity_name)), math.floor(distance)))
        go_to_position(agent, entity.position.x, entity.position.y, entity.position.z, min_distance)
    return True

def go_to_position(agent, x, y, z, closeness = 0) : 
    agent.bot.pathfinder.setMovements(pathfinder.Movements(agent.bot))
    agent.bot.pathfinder.setGoal(pathfinder.goals.GoalNear(x, y, z, closeness)) 

def chat(agent, player_name, message) : 
    if player_name == "all" or agent.bot.players[player_name] is not None : 
        message = "@%s %s" % (player_name, message)
        agent.bot.chat(message)
    else : 
        agent.bot.chat(message)

def go_to_player(agent, player_name, closeness = 1) : 
    player = agent.bot.players[player_name]
    player_pos = get_entity_position(player.entity)
    if player_pos is not None :  
        go_to_position(agent, player_pos.x, player_pos.y, player_pos.z, closeness)
        chat(agent, player_name, "I am moving to you.")
    else : 
        chat(agent, player_name, "I can't find where you are.")

def move_away(agent, distance) : 
    agent_pos = get_entity_position(agent.bot.entity)
    if agent_pos is not None :
        vector = get_random_vector(distance)
        go_to_position(agent, agent_pos.x + vector[0], agent_pos.y, agent_pos.z + vector[1], 0) 

def break_block_at(agent, x, y, z) : 
    if x is None or y is None or z is None : 
        return False
    block = agent.bot.blockAt(vec3.Vec3(x, y, z))
    if block is not None and block.name not in get_empty_block_names() and block.name != "water" and block.name != "lava" :
        if agent.bot.modes is not None and agent.bot.modes.isOn("cheat") :
            msg = "/setblock %d %d %d air" % (math.floor(x), math.floor(y), math.floor(z))
            agent.bot.chat(msg)
            return True
        agent_pos = get_entity_position(agent.bot.entity)
        if agent_pos is not None and agent_pos.distanceTo(block.position) > 4.5 :
            pos = block.position
            movements = pathfinder.Movements(agent.bot)
            movements.canPlaceOn = False
            movements.allow1by1towers = False
            agent.bot.pathfinder.setMovements(movements)
            agent.bot.pathfinder.setGoal(pathfinder.goals.GoalNear(pos.x, pos.y, pos.z, 4))

        if agent.bot.game is not None and agent.bot.game.gameMode != "creative" :
            agent.bot.tool.equipForBlock(block)
            item_id = agent.bot.heldItem.type if agent.bot.heldItem is not None else None 
            if not block.canHarvest(item_id) :
                agent.bot.chat("I Don't have right tools to break %s." % block.displayName)
                return False
        agent.bot.dig(block, True)
    else :
        return False
    return True

def get_an_item_in_hotbar(agent, item_name) :
    items = list(filter(lambda slot : slot is not None and slot.name == item_name, agent.bot.inventory.slots))
    item  = items[0] if len(items) > 0 else None
    return item

def get_an_item_in_inventory(agent, item_name) :
    items = list(filter(lambda item : item.name == item_name, agent.bot.inventory.items()))
    item  = items[0] if len(items) > 0 else None
    return item

def get_inventory_stacks(agent) :
    inventory = []
    for item in agent.bot.inventory.items() :
        if item is not None : 
            inventory.append(item)
    return inventory

def get_inventory_counts(agent) :
    inventory = {}
    for item in agent.bot.inventory.items() :
        if item is not None :
            if item.name not in inventory.keys() :
                inventory[item.name] = 0
            inventory[item.name] += item.count
    return inventory

def get_hotbar_counts(agent) :
    hotbar = {}
    for item in agent.bot.inventory.slots :
        if item is not None :
            if item.name not in hotbar.keys() :
                hotbar[item.name] = 0
            hotbar[item.name] += item.count
    return hotbar

def get_item_counts(agent) :
    inventory = get_inventory_counts(agent)
    hotbar = get_hotbar_counts(agent)
    inventory.update(hotbar)
    return inventory

def equip_item(agent, item_name) :
    item = get_an_item_in_hotbar(agent, item_name)
    if item is None : 
        agent.bot.chat("I don't have any %s to equip." % get_item_display_name(get_item_id(item_name)))
        return False

    if "legging" in item_name : 
        agent.bot.equip(item, 'legs')
    elif "boots" in item_name : 
        agent.bot.equip(item, 'feet')
    elif "helmet" in item_name :
        agent.bot.equip(item, 'head')
    elif "chestplate" in item_name or "elytra" in item_name :
        agent.bot.equip(item, 'torso')
    elif "shield" in item_name :
        agent.bot.equip(item, 'off-hand')
    else :
        agent.bot.equip(item, 'hand')

    agent.bot.chat("I am equipped %s." % item_name)
    return True

def drop_item(agent, item_name, num = 1) :
    dropped = 0
    while True :
        item = get_an_item_in_inventory(agent, item_name)
        if item is None :
            break
        to_drop = item.count if num < 0 else min(num - dropped, item.count)
        agent.bot.toss(item.type, None, to_drop)
        dropped += to_drop
        if num >= 0 and dropped >= num :
            break

    if dropped < 1 :
        agent.bot.chat("I don't have any %s to drop." % get_item_display_name(get_item_id(item_name)))
        return False

    agent.bot.chat("I dropped %d %s." % (dropped, get_item_display_name(get_item_id(item_name))))
    return True

def fight(agent, entity_name, kill = False) :
    if agent.bot.modes is not None : 
        agent.bot.modes.pause('cowardice')
        if entity_name in ["drowned", "cod", "salmon", "tropical_fish", "squid"] :
            agent.bot.modes.pause('self_preservation') 
    entities = list(filter(lambda et: et.name == entity_name, get_nearest_entities(agent, 32)))
    entity = entities[0] if len(entities) > 0 else None 
    if entity is not None :
        return attack_entity(agent, entity, kill)
    else :
        agent.bot.chat("I can't find any %s to attack." % get_entity_display_name(get_entity_id(entity_name)))
        return False

def held_bow(agent) :
    item = agent.bot.heldItem
    has_arrow = False
    for key, value in get_inventory_counts(agent).items() :
        if "arrow" in key and value > 0 : 
            has_arrow = True
    return item is not None and "bow" in item.name and has_arrow

def fight_entity(agent, entity) :
    item = agent.bot.heldItem
    agent_pos = get_entity_position(agent.bot.entity)
    entity_pos = get_entity_position(entity)
    if item is not None and "crossbow" not in item.name :
        if agent_pos is not None and entity_pos is not None and agent_pos.distanceTo(entity_pos) > 12 :
            go_to_position(agent, entity_pos.x, entity_pos.y + 1, entity_pos.z, 10)
        agent.bot.activateItem()
        time.sleep(0.8)
        agent.bot.lookAt(entity_pos)
        time.sleep(0.2)
        agent.bot.deactivateItem()
    else :
        if agent_pos is not None and entity_pos is not None and agent_pos.distanceTo(entity_pos) > 12 :
            go_to_position(agent, entity_pos.x, entity_pos.y + 1, entity_pos.z, 10)
        agent.bot.activateItem()
        time.sleep(1)
        agent.bot.lookAt(entity_pos)
        time.sleep(2)
        agent.bot.deactivateItem()

def attack_entity(agent, entity, kill = False) : 
    entity_pos = get_entity_position(entity)
    if entity_pos is not None : 
        if agent.bot.usingHeldItem :
            agent.bot.deactivateItem()
            time.sleep(0.3)
        if held_bow(agent) :
            if kill == False :
                fight_entity(agent, entity)
                agent.bot.chat("I attacked %s." % entity.name)
            else :
                while entity in get_nearest_entities(agent, 32) and held_bow(agent) : 
                    time.sleep(1)
                    fight_entity(agent, entity)
                agent.bot.chat("I killed %s." % entity.name)
            equip_highest_attack(agent)
            if kill == False :
                agent_pos = get_entity_position(agent.bot.entity)
                if agent_pos is not None and agent_pos.distanceTo(entity_pos) > 5 :
                    go_to_position(agent, entity_pos.x, entity_pos.y, entity_pos.z)
                agent.bot.attack(entity)
                agent.bot.chat("I attacked %s." % entity.name)
            else :
                agent.bot.pvp.attack(entity)
                while entity in get_nearest_entities(agent, 24) :
                    time.sleep(1.0)
                    if agent.bot.interrupt_code :
                        agent.bot.pvp.stop()
                        return False
                agent.bot.chat("I killed %s." % entity.name)
                pickup_nearby_items(agent)
        return True
    return False

def pickup_nearby_items(agent, max_distance = 8, num = 8) : 
    if agent.bot.game is not None and agent.bot.game.gameMode != "creative" :
        nearest_item = get_nearest_item(agent, distance = max_distance)
        prev_item = nearest_item
        init_counts = sum([value for value in get_item_counts(agent).values()])
        picked_up = 0
        while nearest_item and picked_up < num :
            agent.bot.pathfinder.setMovements(pathfinder.Movements(agent.bot))
            agent.bot.pathfinder.setGoal(pathfinder.goals.GoalFollow(nearest_item, 0.8), False)
            time.sleep(0.5)
            prev_item = nearest_item
            nearest_item = get_nearest_item(agent, distance = max_distance)
            if prev_item == nearest_item :
                break
            counts = sum([value for value in get_item_counts(agent).values()])
            picked_up = counts - init_counts 
        agent.bot.chat("I picked up %d items" % picked_up)
    return True

def equip_highest_attack(agent) :
    weapons = list(filter(lambda item : "sword" in item.name or "axe" in item.name, agent.bot.inventory.items()))
    if len(weapons) < 1 : 
        weapons = list(filter(lambda item : "pickaxe" in item.name or "shovel" in item.name, agent.bot.inventory.items()))
    if len(weapons) > 0 : 
        weapons = sorted(weapons, key = functools.cmp_to_key(lambda a, b : a.attackDamage < b.attackDamage))
        weapon = weapons[0]
        if weapon is not None : 
            agent.bot.equip(weapon, "hand")

def craft(agent, item_name, num = 1) :
    placed_table = False
    if len(get_item_crafting_recipes(item_name)) < 1 : 
        agent.bot.chat("I don't have crafting recipe for %s." % item_name)
        return False

    recipes = agent.bot.recipesFor(get_item_id(item_name), None, 1, None) 
    crafting_table = None
    crafting_table_range = 32

    if recipes is None or len(recipes) < 1 : 
        recipes = agent.bot.recipesFor(get_item_id(item_name), None, 1, True)
        if recipes is None or len(recipes) < 1 : 
            agent.bot.chat("I don't have enough resources to craft %s." % item_name)
            return False

        crafting_table = get_nearest_block(agent, 'crafting_table', crafting_table_range)
        if crafting_table is None : 
            has_table = get_inventory_counts(agent)["crafting_table"] > 0
            if has_table == True :
                pos = get_nearest_freespace(agent, 1, 6)
                if pos is not None :
                    place_block("crafting_table", pos.x, pos.y, pos.z)
                    crafting_table = get_nearest_block(agent, "crafting_table", crafting_table_range)
                    if crafting_table is not None :
                        recipes = agent.bot.recipesFor(agent, get_item_id(item_name), None, 1, crafting_table)
                        placed_table = True
                agent.bot.chat("There is no space to place the crafting table.")
                return False
            else :
                agent.bot.chat("I don't have any crafting table.")
                return False
        else :
            recipes = agent.bot.recipesFor(get_item_id(item_name), None, 1, crafting_table)

    if recipes is None or len(recipes) < 1 :
        return False 
    
    if crafting_table is not None : 
        agent_pos = get_entity_position(agent.bot.entity)
        crafting_table_pos = crafting_table.position 
        if crafting_table_pos is not None and agent_pos is not None and agent_pos.distanceTo(crafting_table_pos) > 4 : 
            go_to_position(agent, crafting_table_pos.x, crafting_table_pos.y, crafting_table_pos.z, 4)

    recipe = recipes[0]
    inventory = get_inventory_counts(agent)
    required_ingredients = ingredients_from_prismarine_recipe(recipe)
    craft_limit = calculate_limiting_resource(inventory, required_ingredients)
    
    agent.bot.craft(recipe, min(craft_limit["num"], num), crafting_table)
    if craft_limit["num"] < num : 
        agent.bot.chat("I don't have enough %s to craft %s %s, crafted %s." % (craft_limit["limiting_resource"], num, item_name, craft_limit["num"]))
    else :
        agent.bot.chat("I have crafted %s %s." % (num, item_name))

    if placed_table :
        collect_blocks('crafting_table', 1)

    # agent.bot.armorManager.equipAll(); 
    return True

def collect_blocks(agent, block_name, num, exclude = None) : 
    if agent.bot.game is not None and agent.bot.game.gameMode == "creative" :
        if agent.bot.modes is not None and agent.bot.modes.isOn("cheat") :
            agent.bot.chat("/give %s %s" % (agent.bot.username, block_name))
            agent.bot.chat("This is creative mode and I got %s." % get_block_display_name(get_block_id(block_name)))
        else :
            agent.bot.chat("Now we are in creative mode, don't need to collect any blocks.")
        return 1 

    block_names = [block_name]
    if block_name in ["coal", "diamond", "emerald", "iron", "gold", "lapis_lazuli", "redstone", ] : 
        block_names.append("%s_ore" % block_name)
    if block_name.endswith("ore") :
        block_names.append("deepslate_%s" % block_name)
    if block_name == "dirt" : 
        block_names.append("grass_block")

    init_block_count = get_item_counts(agent).get(block_name, 0)
    collected, action_num = 0, 0
    while collected < num :
        action_num += 1
        blocks = get_nearest_blocks(agent, block_names = block_names, max_distance = 512, count = 16)
        if exclude is not None and isinstance(exclude, list) : 
            blocks = list(filter(lambda block : all([block.position.x != position.x or block.position.y != position.y or block.position.z != position.z for position in exclude]), blocks))
        movements = pathfinder.Movements(agent.bot)
        movements.dontMineUnderFallingBlock = False
        blocks = list(filter(lambda block: movements.safeToBreak(block), blocks))
        if len(blocks) < 1 : 
            if collected < 1 :  
                agent.bot.chat("I don't find any %s nearby to collect." % get_block_display_name(get_block_id(block_name)))
            else :
                agent.bot.chat("Can't find more %s nearby to collect." % get_block_display_name(get_block_id(block_name)))
            break

        block = blocks[0]
        agent.bot.tool.equipForBlock(block)
        item_id = agent.bot.heldItem if agent.bot.heldItem is not None else None 
        if not block.canHarvest(item_id) : 
            agent.bot.chat("I dont't have right tools to harvest %s." % get_block_display_name(get_block_id(block_name)))
            break

        if must_collect_manually(block_name) :
            go_to_position(agent, block.position.x, block.position.y, block.position.z, 2)
            time.sleep(1)
            agent.bot.dig(block)
            pickup_nearby_items(agent)
        else :
            agent.bot.collectBlock.collect(block)
        block_count = get_item_counts(agent).get(block_name, 0)
        collected = block_count - init_block_count
        auto_light(agent)

        if agent.bot.interrupt_code :
            break;  

    agent.bot.chat("I have collected %d %s." % (collected, get_block_display_name(get_block_id(block_name))))
    return collected > 0

def should_place_torch(agent) : 
    if agent.bot.modes is not None and agent.bot.modes.isOn('torch_placing') or agent.bot.interrupt_code :
        return False
    agent_pos = get_entity_position(agent.bot.entity)
    if agent_pos is not None : 
        nearest_torch = get_nearest_block(agent, 'torch', 6)
        if nearest_torch is None :
            nearest_torch = get_nearest_block(agent, 'wall_torch', 6)
        if nearest_torch is None : 
            block = agent.bot.blockAt(agent_pos)
            if block is None :
                return False
            else :
                has_torch = any([item.name == "torch" for item in agent.bot.inventory.items()])
                return has_torch and block.name == 'air'
    return False

def auto_light(agent) : 
    agent_pos = get_entity_position(agent.bot.entity)
    if should_place_torch(agent) and agent_pos is not None :
        place_block(agent, 'torch', agent_pos.x, agent_pos.y, agent_pos.z, 'bottom', True)
        return True
    return False

def place_block(agent, block_name, x, y, z, place_on = 'bottom', dont_cheat = False) :
    if get_block_id(block_name) is None and block_name != 'air' :
        agent.bot.chat("%s is invalid block name." % block_name, print = False)
        return False

    target_dest = [math.floor(x), math.floor(y), math.floor(z)]
    if block_name in get_empty_block_names() :
        break_block_at(agent, *target_dest)

    if agent.bot.modes is not None and agent.bot.modes.isOn('cheat') and not dont_cheat :
        if agent.bot.restrict_to_inventory :
            block = get_an_item_in_inventory(agent, block_name)
            if block is None :
                return False

        face = "east"
        if place_on == "north" : 
            face = "south"
        elif place_on == "south" :
            face = "north"
        elif place_on == "east" : 
            face = "west"

        if "torch" in block_name and place_on != "bottom" :
            block_name = block_name.replace('torch', 'wall_torch')
            if place_on != "side" and place_on != "top" :
                block_name += "[facing=%s]" % face

        if "botton" in block_name or block_name == "lever" :
            if place_on == "top" :
                block_name += "[face=ceiling]"
            elif place_on == "bottom" :
                block_name += "[face=floor]"
            else :
                blockType += "[facing=%s]" % face

        if block_name == "ladder" or block_name == "repeater" or block_name == "comparator" :
            block_name += "[facing=%s]" % face

        if "stairs" in block_name :
            block_name += "[facing=%s]" % face

        msg = "/setblock %d %d %d %s" % (math.floor(x), math.floor(y), math.floor(z), block_name)
        agent.bot.chat(msg)

        if "door" in block_name :
            msg = "/setblock %d %d %d %s [half=upper]" % (math.floor(x), math.floor(y + 1), math.floor(z), block_name)
            agent.bot.chat(msg)

        if "bed" in block_name :
            msg = "/setblock %d %d %d %s [part=head]" % (math.floor(x), math.floor(y), math.floor(z - 1), block_name)
            agent.bot.chat(msg)

        return True
    
    item_name = block_name
    if item_name == "redstone_wire" : 
        item_name = "redstone"

    block = get_an_item_in_inventory(agent, item_name) 

    if block is None and agent.bot.game.gameMode == 'creative' and not agent.bot.restrict_to_inventory :
        agent.bot.creative.setInventorySlot(36, make_item(item_name, 1)) 
        block = get_an_item_in_inventory(agent, item_name) 

    if block is None :
        add_log(title = agent.pack_message("Place block."), content = "Have no %s to place." % block_name, print = False)
        return False

    target_block = agent.bot.blockAt(vec3.Vec3(*target_dest))
    if target_block is not None : 
        if target_block.name == block_name :
            return False

        if target_block.name not in get_empty_block_names() :
            removed = break_block_at(agent, *target_dest)
            if removed == False :
                return False
            time.sleep(0.2)

    build_off_block, face_vec = None, None 
    dir_map = {
        "top" : [0, 1, 0], "bottom" : [0, -1, 0],
        "north" : [0, 0, -1], "south" : [0, 0, 1],
        "east" : [1, 0, 0], "west" : [-1, 0, 0],
    }

    dirs = []
    if place_on == "side" :
        dirs.append(dir_map["north"], dir_map["south"], dir_map["east"], dir_map["west"]);
    elif place_on in dir_map.keys() :
        dirs.append(dir_map[place_on])
    else :
        dirs.append(dir_map["bottom"])
    
    for d in dir_map.values() : 
        if d not in dirs : 
            dirs.append(d)

    for d in dirs :
        b = agent.bot.blockAt(vec3.Vec3(target_dest[0] + d[0], target_dest[1] + d[1], target_dest[2] + d[2]))
        if b is not None and b.name not in get_empty_block_names() and all([n not in b.name for n in get_cant_build_off_block_names()]) :
            build_off_block = b
            face_vec = [-d[0], -d[1], -d[2]] 
            break

    if build_off_block is None : 
        agent.bot.chat("I Can't place %s at %s. Nothing to place on." % (block_name, target_dest))
        return False

    agent_pos = get_entity_position(agent.bot.entity)
    if agent_pos is not None and agent_pos.distanceTo(vec3.Vec3(*target_dest)) > 3 :
        go_to_position(agent, target_dest[0], target_dest[1], target_dest[2], 2)
    
    agent.bot.equip(block, 'hand')
    agent.bot.lookAt(build_off_block.position)
    agent.bot.placeBlock(build_off_block, vec3.Vec3(*face_vec))
    return True

def test(agent) : 
    agent.bot.chat("Okay, I will do some tests.")
    # if (agent.bot and agent.bot.entity and agent.bot.entity.position) : 
        # pos = agent.bot.entity.position 
        # place_block(agent, "stone", pos.x - 1, pos.y, pos.z - 1)

def new_action(agent, task) :
    prompt = '''
You are a helpful AI agent working in a Minecraft environment. Your task is to write a custom Python function that performs a new action which cannot be achieved using existing predefined actions.

## Requirements

### Task 
%s

Given the above task description, you should:

1. Write a new Python function named `generated_action` to complete the task.
2. The function must be valid, executable, and focused on achieving the goal clearly and efficiently.

## Function Signature

The function **must be defined as**:
```
def generated_action(agent):
    ...
```

### Parameter Details:

* The `agent` parameter is the AI character instance in the Minecraft world.
* You can use `agent.bot` to access the underlying **mineflayer bot API** to interact with the environment.
* You may also use other properties of `agent` (like internal memory or helper functions), if applicable.
* No additional parameters are allowed — **`agent` is the only argument.**

## Security and Code Requirements
Follow these rules strictly:
1. The function **must be named** `generated_action` and take **exactly one parameter named `agent1**.
2. The function should be **self-contained** and **safe to execute**, without importing dangerous modules (e.g., `os`, `subprocess`, `socket`, etc.).
3. Avoid using `eval`, `exec`, or any dynamic code execution tools.
4. Do **not** perform file I/O, networking, or system-level operations.
5. You may use predefined utility functions or variables if they exist in the agent's environment. If they are referenced, provide clear comments.
6. Do not use any modules or functions outside the Minecraft AI environment.
7. You should prefer using standard Python syntax and logic.
8. Handle errors gracefully (e.g. use `try/except` when accessing dynamic entities).
9. If the task is vague or cannot be safely implemented, return a code stub with a `TODO` and comment explaining the issue instead of guessing.

## Coding Guide
1. **Handle asynchronous behavior carefully**:
   If you call any asynchronous method from `agent.bot`, remember to allow time for it to complete. You can use `time.sleep(0.005)` (i.e., 5 milliseconds) to yield briefly after such operations.
2. **Check preconditions before performing actions**:
   Before executing a task (e.g., placing a block), verify that the bot has the necessary resources or conditions are met. For instance, make sure the bot has the required block in inventory before placing it.
3. **Always provide feedback via chat**:
   When a task is successfully completed, use `agent.bot.chat()` to inform the player. If the bot cannot complete the task due to an error or missing requirements, report that as well — this helps maintain transparency and traceability of actions.
4. **Keep the function concise and focused**:
   The function should focus on a **single logical step** within a task. If the task is complex, implement just the next actionable step and allow the planner to generate the follow-up in future iterations.
5. **Avoid external dependencies or side effects**:
   Use only the APIs and resources available through `agent` and `agent.bot`. Do not import external libraries or access files, network resources, or system-level features.

## Availabel API for `agent.bot`
The `agent.bot` object provides a wide range of APIs that allow the bot to perceive and interact with the Minecraft world. These APIs are wrappers around the `mineflayer` client functions. Some of the most commonly used methods include:

### Movement & Navigation
  * `bot.pathfinder.setGoal(goal)` : Move toward a specified goal (e.g., position, entity).
  * `bot.lookAt(position)` : Turn the bot's view toward a specific position.
  * `bot.jump()` : Make the bot jump.

### Inventory & Items
  * `bot.inventory.items()` : Get a list of current items.
  * `bot.equip(item, destination)` : Equip an item to a destination slot (e.g., hand, off-hand).
  * `bot.toss(itemType, metadata, count)` : Drop items.
  * `bot.craft(recipe, count, craftingTable)` : Craft items if recipe and materials are available.
  * `bot.mineBlock(block)` : Mine a block.

### Block & Environment Interaction
  * `bot.placeBlock(referenceBlock, faceVector)` : Place a block relative to another.
  * `bot.dig(block)` : Dig/break a block.
  * `bot.findBlock(options)` : Find a block nearby matching certain criteria.
  * `bot.chat(message)` : Send a message to the in-game chat.

### Entity Interaction
  * `bot.entities` : Dictionary of all known entities (players, mobs, etc.).
  * `bot.attack(entity)` : Attack a nearby entity.
  * `bot.useOn(entity)` : Use the current item on an entity (e.g., feed, shear).

### Sensing & Utility
  * `bot.findEntity(options)` : Find nearest matching entity.
  * `bot.nearestPlayer()` : Get the nearest player entity.
  * `bot.entity.position` : Get bot's current position.

## Output Format
The result must be formatted as a **JSON dictionary** and enclosed in **triple backticks (` ``` ` )**, without any other text.
- Keys:
  - `"code"`: A JSON string containing the full source code of the generated function (named `generated_action`).
- Do **not** use triple backticks inside the code string.
- The function should be fully indented and executable as a standalone Python snippet.

## Example Output
```
{
  "code": "def generated_action(agent):\\n    player_pos = agent.bot.entity.position\\n    target_pos = player_pos.offset(2, 0, 0)\\n    agent.bot.placeBlock(target_pos, 'oak_planks')"
}
```
''' % task 
    llm_result = call_llm_api(agent.configs["provider"], agent.configs["model"], prompt, max_tokens = agent.configs.get("max_tokens", 4096))
    add_log(title = agent.pack_message("Get LLM response:"), content = str(llm_result), label = "coding")
    if llm_result["status"] > 0 :
        add_log(title = agent.pack_message("Error in calling LLM: %s" % llm_result["error"]), label = "warning")
    else :
        _, data = split_content_and_json(llm_result["message"])
        add_log(title = agent.pack_message("Get data:"), content = str(data), label = "coding")
        code = data.get("code", None) 
        try :
            exec(code)
            result = generated_action(agent)
        except Exception as e :
            add_log(title = agent.pack_message("Exception happen when executing generated action."), content = "Exception: %s" % e, label = "warning")

def validate_param(value, _type, domain) :
    valid_value = None
    if value is not None :
        try : 
            if _type in ["string", "BlockName", "ItemName"] : 
                valid_value = str(value)
            if _type == "bool" : 
                valid_value = bool(value)
            elif _type == "float" : 
                valid_value = float(value)
                valid_value = min(max(domain[0], valid_value), domain[1])
            elif _type == "int" : 
                valid_value = int(value)
                valid_value = min(max(domain[0], valid_value), domain[1])
        except : 
            valid_value = None
    return valid_value

def get_primary_actions() : 
    return [
        {
            "name" : "chat", 
            "desc": "Chat with others.",
            "params": {
                "player_name": {"type" : "string", "desc" : "The name of the player to mention in the chat.", "domain" : "either the name of any player in the game, or 'all' to mention all the players"},
                "message": {"type" : "string", "desc" : "The message to send.", "domain" : "any valid text"},
            },
            "perform" : chat, 
        },
        {
            "name" : "go_to_player", 
            "desc": "Go to the given player.",
            "params": {
                "player_name": {"type" : "string", "desc" : "The name of the player to go to.", "domain" : "any valid value"},
                "closeness": {"type" : "float", "desc" : "How close to get to the player. If no special reason, closeness should be set to 1.", "domain" : [0, math.inf]},
            },
            "perform" : go_to_player, 
        },
        {   
            "name" : "collect_blocks",
            "desc" : "Collect the nearest blocks of a given type.",
            "params" : {
                "block_name" : {"type": "BlockName", "desc": "The block name to collect.", "domain" : "The block names in Minecraft."},
                "num" : {"type": "int", "desc" : "The number of blocks to collect.", "domain" : [1, 16]},
            },
            "perform" : collect_blocks, 
        },
        {
            "name" : "equip_item",
            "desc" : "Equip the given item.",
            "params" : {
                "item_name": { "type" : "ItemName", "desc" : "The name of the item to equip.", "domain" : "The item names in Minecraft."}, 
            },
            "perform" : equip_item,
        },
        {
            "name" : "drop_item",
            "desc" : "Drop the given item from the inventory.",
            "params" : {
                "item_name" : {"type" : "ItemName", "desc" : "The name of the item to drop.", "domain" : "The item names in Minecraft."},
                "num" : {"type" : "int", "desc" : "The number of items to drop.", "domain" : [1, 16]}
            },
            "perform" : drop_item,
        },
        {
            "name" : "fight",
            "desc" : 'Attack or kill the nearest entity of a given type.',
            "params": {
                "entity_name": { "type" : "string", "desc" : "The type of entity to attack.", "domain" : "The entity names in Minecraft."},
                "kill" : {"type" : "bool", "desc" : "Indicate if you want to kill the entity", "domain" : [True, False]},
            },
            "perform" : fight,
        },
        {
            "name" : "craft",
            "desc" : "Craft the given recipe a given number of times.",
            "params" : {
                "recipe_name": {"type" : "ItemName", "desc" : "The name of the output item to craft.", "domain" : "The item names in Minecraft."},
                "num" : {"type" : "int", "desc" : "The number of times to craft the recipe. This is NOT the number of output items, as it may craft many more items depending on the recipe.", "domain" : [1, 4]},
            },
            "perform" : craft,
        },
        {
            "name": "new_action",
            "desc": "Dynamically write and execute a Python function to perform a task that cannot be achieved by existing predefined actions. This is a fallback mechanism for handling novel or complex tasks.",
            "params": {
                "task": {
                    "type": "string", 
                    "desc": "A clear and complete description of the task to be implemented in Python. The description should specify what needs to be done, any relevant context, and expected behavior.",
                    "domain": "A natural language description of the custom task.",
                },
            },
            "perform" : new_action,
        },
        # {
        #     "name" : "test", 
        #     "desc": "Do some test.",
        #     "params": {},
        #     "perform" : test, 
        # },
    ]