
from model import *
from world import *
from utils import *

def get_entity_position(entity) : 
    """Return the (x, y, z) position of a given entity; call with get_entity_position(entity), where entity is a valid entity object."""
    pos = None
    if entity is not None : 
        pos = entity.position
    return pos

def get_type_of_generic(agent, block_name) :
    if block_name in get_wood_block_shapes() : 
        type_count = {}
        max_count, max_type = 0, None
        inventory = get_inventory_counts(agent)
        for item, count in inventory.items() : 
            for wood in get_wood_types() : 
                if wood in item :
                    if wood not in type_count.keys() : 
                        type_count[wood] = 0
                    type_count[wood] += count 
                    if type_count[wood] > max_count :
                        max_count = type_count[wood]
                        max_type = wood
        if max_type is not None : 
            return max_type + "_" + block_name

        log_types = [wood + "_log" for wood in get_wood_types()]
        blocks = get_nearest_blocks(agent, log_types, 16, 1)
        if len(blocks) > 0 :
            wood = blocks[0].name.split("_")[0]
            return wood + "_" + block_name
        return "oak_" + block_name

    if block_name == "bed" :
        type_count = {}
        max_count, max_type = 0, None 
        inventory = get_inventory_counts(agent)
        for item, count in inventory.items() : 
            for color in get_wool_colors() : 
                if item == color + "_wool" :
                    if color not in type_count.keys() :
                        type_count[color] = 0
                    type_count[color] += count
                    if type_count[color] > max_count :
                        max_count = type_count[color]
                        max_type = color

        if max_type is not None : 
            return max_type + "_" + block_name
        return "white_" + block_name

    return block_name

def block_satisfied(target_name, block, relax = 0) :
    if target_name == "dirt" :
        return block.name in ["dirt", "grass_block"]
    elif target_name in get_wood_block_shapes() : 
        return block.name.endswith(target_name)
    elif target_name == "bed" :
        return block.name.endswith("bed")
    elif target_name == "torch" :
        return block.name.includes('torch');
    return block.name == target_name

def item_satisfied(agent, item_name, quantity = 1) : 
    if agent.bot.game is not None and agent.bot.game.gameMode == "creative" :
        quantity = 1
    qualifying = [item_name, ]
    if any(name in item_name for name in ["pickaxe", "axe", "shovel", "hoe", "sword"]) and "_" in item_name:
        material, _type = item_name.split("_")
        if material == "wooden" :
            qualifying.append("stone_" + _type)
            qualifying.append("iron_" + _type)
            qualifying.append("gold_" + _type)
            qualifying.append("diamond_" + _type)
        elif material == "stone" :
            qualifying.append("iron_" + _type)
            qualifying.append("gold_" + _type)
            qualifying.append("diamond_" + _type)
        elif material == "iron" :
            qualifying.append("gold_" + _type)
            qualifying.append("diamond_" + _type)
        elif material == "gold" :
            qualifying.append("diamond_" + _type)
    for item in qualifying :
        if get_inventory_counts(agent).get(item, 0) >= quantity :
            return True
    return False

def get_nearest_blocks(agent, block_names = None, max_distance = 64, count = 16) :
    """Find and return up to 'count' nearest blocks matching 'block_names' within 'max_distance' blocks around the agent; call with get_nearest_blocks(agent, block_names, max_distance, count)."""
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
    """Return the nearest block matching 'block_name' within 'max_distance' blocks of the agent; call with get_nearest_block(agent, block_name, max_distance)."""
    blocks = get_nearest_blocks(agent, block_names = [block_name], max_distance = max_distance, count = 1)
    if len(blocks) > 0 :
        return blocks[0]
    return None 

def get_nearest_item(agent, distance = 1) :
    """Find and return the closest dropped item entity within 'distance' blocks; call with get_nearest_item(agent, distance)."""
    entity = None 
    agent_pos = get_entity_position(agent.bot.entity)
    if agent_pos is not None : 
        entity = agent.bot.nearestEntity(lambda et : et.name == 'item' and et.position is not None and agent_pos.distanceTo(et.position) < distance)
    return entity

def search_block(agent, block_name, range = 64, min_distance = 2) :
    """Search the world for a block named 'block_name' within a given 'range' but at least 'min_distance' away from the agent; call with search_block(agent, block_name, range, min_distance)."""
    range = min(512, range)
    block = get_nearest_block(agent, block_name, range)
    if block is None :
        agent.bot.chat("I can't find any %s in %s blocks." % (get_block_display_name(get_block_id(block_name)), math.floor(range)))
        return False
    agent.bot.chat("Found %s at %s. I am going there." % (get_block_display_name(get_block_id(block_name)), block.position))
    go_to_position(agent, block.position.x, block.position.y, block.position.z, min_distance)
    return True

def get_nearest_entity_where(agent, predicate, max_distance) : 
    """Get nearest entity which satisfies `predicate` validator within 'max_distance' blocks of the agent; call with get_nearest_entity_where(agent, predicate, max_distance)."""
    entity = None
    agent_pos = get_entity_position(agent.bot.entity)
    if agent_pos is not None : 
        entity = agent.bot.nearestEntity(lambda et : predicate(et) and et.position is not None and agent_pos.distanceTo(et.position) < max_distance)
    return entity

def get_nearest_entities(agent, max_distance = 32, count = 16) : 
    """Get up to 'count' nearby entities within 'max_distance' blocks of the agent; call with get_nearest_entities(agent, max_distance, count)."""
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
    """Find the nearest free space of given 'size' within 'distance' blocks for agent to move or act; call with get_nearest_freespace(agent, size, distance).""" 
    empty_positions = agent.bot.findBlocks({
        "matching" : lambda block : block is not None and block.name in get_empty_block_names(),
        "maxDistance" : distance,
        "count" : 1000,
    })
    for pos in empty_positions : 
        empty = True
        for x in range(size) :
            for z in range(size) : 
                top = agent.bot.blockAt(pos.offset(x, 0, z))
                bottom = agent.bot.blockAt(pos.offset(x, -1, z))
                if top is None or top.name not in get_empty_block_names() or bottom is None or sizeof(bottom.drops) < 1 or not bottom.diggable :
                    empty = False
                    break
            if empty is None :
                break
        if empty == True :
            return pos
    return None

def search_entity(agent, entity_name, range = 64, min_distance = 2) :
    """Search for an entity named 'entity_name' within a given 'range' but farther than 'min_distance' from the agent; call with search_entity(agent, entity_name, range, min_distance)."""
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
    """Command the agent to move to (x, y, z) position with a target 'closeness' tolerance; call with go_to_position(agent, x, y, z, closeness)."""
    agent.bot.pathfinder.setMovements(pathfinder.Movements(agent.bot))
    agent.bot.pathfinder.setGoal(pathfinder.goals.GoalNear(x, y, z, closeness)) 
    while agent.bot.pathfinder.isMoving() :
        time.sleep(0.2)

def chat(agent, player_name, message) : 
    """Send a 'message' from the agent to a specified 'player_name' in the game chat; call with chat(agent, player_name, message)."""
    if player_name == "all" or (player_name != agent.bot.username and agent.bot.players[player_name] is not None) : 
        message = "@%s %s" % (player_name, message)
        agent.bot.chat(message)
    else : 
        agent.bot.chat(message)

def go_to_player(agent, player_name, closeness = 1) : 
    """Move the agent to the specified player within a 'closeness' distance; call with go_to_player(agent, player_name, closeness)."""
    player = agent.bot.players[player_name]
    player_pos = get_entity_position(player.entity)
    if player_pos is not None :  
        go_to_position(agent, player_pos.x, player_pos.y, player_pos.z, closeness)
        chat(agent, player_name, "I am moving to you.")
    else : 
        chat(agent, player_name, "I can't find where you are.")

def use_door(agent, door_pos = None) :
    """Let the agent interact with the door at the given position; call with use_door(agent, door_pos)."""
    if door_pos is None :
        for door_type in get_door_types() : 
            door_pos = get_nearest_block(agent, door_type, 16)["position"]
            if door_pos : break
    
    if door_pos is None : 
        return False

    go_to_position(agent, door_pos.x, door_pos.y, door_pos.z, 1)
    
    door_block = agent.bot.blockAt(door_pos)
    agent.bot.lookAt(door_pos)
    if door_block is not None and not door_block._properties.open :
        agent.bot.activateBlock(door_block)
    return True

def move_away(agent, distance) : 
    agent_pos = get_entity_position(agent.bot.entity)
    if agent_pos is not None :
        vector = get_random_vector(distance)
        go_to_position(agent, agent_pos.x + vector[0], agent_pos.y, agent_pos.z + vector[1], 0) 

def break_block_at(agent, x, y, z) : 
    """Break the block located at coordinates (x, y, z); call with break_block_at(agent, x, y, z)."""
    if x is None or y is None or z is None : 
        return False
    block = agent.bot.blockAt(vec3.Vec3(x, y, z))
    if block is not None and block.name not in get_empty_block_names() and block.name != "water" and block.name != "lava" :
        agent_pos = get_entity_position(agent.bot.entity) 
        if agent_pos is not None and agent_pos.distanceTo(vec3.Vec3(x, y, z)) < 2 :
            move_away(agent, 2)
            time.sleep(0.2)

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
    """Return an item matching 'item_name' from the agent's hotbar if available; call with get_an_item_in_hotbar(agent, item_name)."""
    items = list(filter(lambda slot : slot is not None and slot.name == item_name, agent.bot.inventory.slots))
    item  = items[0] if len(items) > 0 else None
    return item

def get_an_item_in_inventory(agent, item_name) :
    """Return an item matching 'item_name' from the agent's inventory if available; call with get_an_item_in_inventory(agent, item_name)."""
    items = list(filter(lambda item : item.name == item_name, agent.bot.inventory.items()))
    item  = items[0] if len(items) > 0 else None
    return item

def get_inventory_stacks(agent) :
    """Return all item stacks currently in the agent’s inventory; call with get_inventory_stacks(agent)."""
    inventory = []
    for item in agent.bot.inventory.items() :
        if item is not None : 
            inventory.append(item)
    return inventory

def get_inventory_counts(agent) :
    """Return a dictionary mapping item names to total counts in inventory; call with get_inventory_counts(agent)."""
    inventory = {}
    for item in agent.bot.inventory.items() :
        if item is not None :
            if item.name not in inventory.keys() :
                inventory[item.name] = 0
            inventory[item.name] += item.count
    return inventory

def get_hotbar_counts(agent) :
    """Return a dictionary mapping item names to counts in the agent’s hotbar; call with get_hotbar_counts(agent)."""
    hotbar = {}
    for item in agent.bot.inventory.slots :
        if item is not None :
            if item.name not in hotbar.keys() :
                hotbar[item.name] = 0
            hotbar[item.name] += item.count
    return hotbar

def get_item_counts(agent) :
    """Get a total item count from both inventory and hotbar; call with get_item_counts(agent)."""
    inventory = get_inventory_counts(agent)
    hotbar = get_hotbar_counts(agent)
    inventory.update(hotbar)
    return inventory

def equip_item(agent, item_name) :
    """Equip the agent with the specified 'item_name' from inventory if found; call with equip_item(agent, item_name)."""
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
    """Drop 'num' items matching 'item_name' from the agent's inventory; call with drop_item(agent, item_name, num)."""
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
    """Command the agent to attack an entity named 'entity_name'; 'kill' determines whether to fight until it's defeated; call with fight(agent, entity_name, kill)."""
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
    """Return `True` if the bot is holding a bow in hand; call with held_bow(agent)."""
    item = agent.bot.heldItem
    has_arrow = False
    for key, value in get_inventory_counts(agent).items() :
        if "arrow" in key and value > 0 : 
            has_arrow = True
    return item is not None and "bow" in item.name and has_arrow

def get_elevation(agent, entity) :
    elevation = 0
    agent_pos = get_entity_position(agent.bot.entity)
    entity_pos = get_entity_position(entity)
    if agent_pos is not None and entity_pos is not None :
        elevation = 1 + agent_pos.distanceTo(entity_pos) // 10 
    return elevation

def fight_entity(agent, entity) :
    """Fight the entity if the bot is holding a 'bow' or a 'crossbow'; call with fight_entity(agent, entity)."""
    item = agent.bot.heldItem
    agent_pos = get_entity_position(agent.bot.entity)
    entity_pos = get_entity_position(entity)
    if item is not None and "crossbow" not in item.name :
        if agent_pos is not None and entity_pos is not None and agent_pos.distanceTo(entity_pos) > 12 :
            go_to_position(agent, entity_pos.x, entity_pos.y, entity_pos.z, 10)
        agent.bot.activateItem()
        time.sleep(0.8)
        agent.bot.lookAt(entity_pos.offset(0, get_elevation(agent, entity), 0))
        time.sleep(0.2)
        agent.bot.deactivateItem()
    else :
        if agent_pos is not None and entity_pos is not None and agent_pos.distanceTo(entity_pos) > 12 :
            go_to_position(agent, entity_pos.x, entity_pos.y, entity_pos.z, 10)
        agent.bot.activateItem()
        time.sleep(1)
        agent.bot.lookAt(entity_pos.offset(0, get_elevation(agent, entity), 0))
        time.sleep(2)
        agent.bot.deactivateItem()

def attack_entity(agent, entity, kill = False) : 
    """Attack the entity, and kill it if `kill` is `True`; call with attack_entity(agent, entity, kill)."""
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
    """Pick up `num` items within distance of `max_distance`; call with pickup_nearby_items(agent, max_distance, num)."""
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
    """Equip with most powerful weapon in the inventory; call with equip_highest_attack(agent)."""
    weapons = list(filter(lambda item : "sword" in item.name or "axe" in item.name, agent.bot.inventory.items()))
    if len(weapons) < 1 : 
        weapons = list(filter(lambda item : "pickaxe" in item.name or "shovel" in item.name, agent.bot.inventory.items()))
    if len(weapons) > 0 : 
        weapons = sorted(weapons, key = functools.cmp_to_key(lambda a, b : a.attackDamage < b.attackDamage))
        weapon = weapons[0]
        if weapon is not None : 
            agent.bot.equip(weapon, "hand")

def craft(agent, item_name, num = 1) :
    """Craft 'num' items of 'item_name' if materials and recipe are available; call with craft(agent, item_name, num)."""
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
    """Collect 'num' blocks of type 'block_name', excluding blocks in the 'exclude' list; call with collect_blocks(agent, block_name, num, exclude)."""
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
    """Check if a torch should be placed to light the place around the bot; call with should_place_torch(agent)."""
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
    """Check if a torch should be placed, and place one if the answer is positive; call with auto_light(agent)."""
    agent_pos = get_entity_position(agent.bot.entity)
    if should_place_torch(agent) and agent_pos is not None :
        place_block(agent, 'torch', agent_pos.x, agent_pos.y, agent_pos.z, 'bottom', True)
        return True
    return False

def place_block(agent, block_name, x, y, z, place_on = 'bottom', dont_cheat = False) :
    """Place a 'block_name' at (x, y, z), optionally aligning with 'place_on' surface; 'dont_cheat' controls whether block must come from inventory; call with place_block(agent, block_name, x, y, z, place_on, dont_cheat)."""
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

    agent_pos = get_entity_position(agent.bot.entity) 
    if agent_pos is not None and agent_pos.distanceTo(vec3.Vec3(*target_dest)) < 2 :
        print("#", target_block.name)
        move_away(agent, 2)
        time.sleep(0.2)

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
