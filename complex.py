
from skills import *
from utils import *
from knowledge import get_breeding_food

def walk_around(agent, num = 1) : 
    """Move for `num` times with a randomly selected direction and distance."""
    pos = get_entity_position(agent)
    if pos is not None : 
        for i in range(num) : 
            offset = get_random_vector(random.randint(1, 3))
            go_to_position(pos.x + offset[0], pos.y, pos.z + offset[1])
            time.sleep(0.5)
    else : 
        chat(agent, None, "I can't finish the action.")

def collect_and_place(agent, block_name, offset_x = 0, offset_y = 0, offset_z = 0):
    """Collect one block of the specified type and place it at the given coordinates."""
    found = collect_blocks(agent, block_name, 1)
    if not found :
        chat(agent, None, f"Couldn't find any {block_name} to collect.")
        return
    time.sleep(1)
    pos = get_entity_position(agent)
    if pos is not None :
        success = place_block(agent, block_name, pos.x + offset_x, pos.y + offset_y, pos.z + offset_z, place_on="bottom")
        if not success:
            chat(agent, None, f"Failed to place the {block_name} block.")
    else : 
        chat(agent, None, "I can't finish the action.")

def fetch_nearest_item(agent) :
    """Find the nearest dropped item and move to its location to pick it up."""
    item = get_nearest_item(agent, 10)
    if item:
        go_to_position(agent, item["x"], item["y"], item["z"], 1)
        chat(agent, None, f"Going to pick up {item['name']}.")
    else:
        chat(agent, None, "No item nearby.")

def attack_nearest_enemy(agent) :
    """Locate the nearest hostile entity within range and engage in combat."""
    entities = get_nearest_entities(agent, 10, 5)
    for entity in entities:
        if entity["is_hostile"]:
            chat(agent, None, f"Attacking {entity['name']}!")
            fight(agent, entity["name"], kill=True)
            return
    chat(agent, None, "No hostile entity found.")

def prepare_tool(agent, item_name):
    """Equip the specified item if available, or attempt to craft and then equip it."""
    item = get_an_item_in_inventory(agent, item_name)
    if item:
        equip_item(agent, item_name)
    else:
        crafted = craft(agent, item_name, 1)
        time.sleep(5)
        if crafted:
            equip_item(agent, item_name)
        else:
            chat(agent, None, f"Cannot craft or equip {item_name}.")

def scan_for_block(agent, block_name = "diamond_ore"):
    """Search for a specific block type within a defined area and report its location."""
    result = search_block(agent, block_name, range= 20, min_distance=2)
    if result:
        chat(agent, None, f"Found {block_name} at {result['x']}, {result['y']}, {result['z']}.")
    else:
        chat(agent, None, f"No {block_name} found nearby.")

def approach_player(agent, player_name):
    """Move toward the specified player within a given closeness range."""
    chat(agent, None, f"Looking for {player_name}...")
    success = go_to_player(agent, player_name, closeness=2)
    if not success:
        chat(agent, None, f"Could not find or reach {player_name}.")

def clean_inventory(agent, item_name="cobblestone", amount = 5):
    """Drop a specified number of items from the inventory."""
    success = drop_item(agent, item_name, amount)
    if success:
        chat(agent, None, f"Dropped {amount} of {item_name}.")
    else:
        chat(agent, None, f"Failed to drop {item_name}.")

def breed_animals(agent, entity_name) :
    """Find two adult animals of the same species and breed them by feeding each one the correct food."""
    food_name = get_breeding_food(entity_name, get_inventory_counts(agent))
    if food_name is None :
        agent.bot.chat("I don't know what food %s eats." % entity_name)
        return False

    food_item = get_an_item_in_inventory(agent, food_name)
    if food_item is None or food_item.count < 2 :
        agent.bot.chat("I need at least 2 %s to breed %s, but I don't have enough." % (food_name, entity_name))
        return False

    entities = list(filter(lambda et : entity_name in et.name, get_nearest_entities(agent, 32)))
    adults = [et for et in entities if not getattr(et, 'isBaby', False)]

    if len(adults) < 2 :
        agent.bot.chat("I need at least 2 adult %s nearby to breed, but I only found %d." % (entity_name, len(adults)))
        return False

    agent.bot.chat("Breeding %s with %s." % (entity_name, food_name))
    fed = 0
    for i in range(2) :
        entity = adults[i]
        food_item = get_an_item_in_inventory(agent, food_name)
        if food_item is None :
            agent.bot.chat("I ran out of %s." % food_name)
            break

        agent.bot.equip(food_item, 'hand')
        time.sleep(0.3)

        entity_pos = get_entity_position(entity)
        if entity_pos is None :
            agent.bot.chat("I lost sight of %s #%d." % (entity_name, i + 1))
            break

        agent_pos = get_entity_position(agent.bot.entity)
        if agent_pos is not None and agent_pos.distanceTo(entity_pos) > 3 :
            go_to_position(agent, entity_pos.x, entity_pos.y, entity_pos.z, 2)

        entity_pos = get_entity_position(entity)
        if entity_pos is None :
            agent.bot.chat("I lost sight of %s #%d." % (entity_name, i + 1))
            break

        agent.bot.lookAt(entity_pos.offset(0, entity.height / 2, 0))
        time.sleep(0.2)
        agent.bot.activateEntity(entity)
        fed += 1
        agent.bot.chat("Fed %s #%d with %s." % (entity_name, i + 1, food_name))
        time.sleep(1)

    if fed == 2 :
        agent.bot.chat("Both %s are now in love mode! A baby should appear soon." % entity_name)
        return True
    else :
        agent.bot.chat("Only fed %d out of 2 %s." % (fed, entity_name))
        return False





