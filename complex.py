
from skills import *
from utils import *

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





