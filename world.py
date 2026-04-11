
import math, time, functools

from javascript import require, On

from utils import *

mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')
pathfinder_plugin = pathfinder.pathfinder  # The actual plugin to load
minecraft_data = require('minecraft-data')
pvp = require('mineflayer-pvp')
pvp_plugin = pvp.plugin  # The actual plugin to load
prismarine_items = require('prismarine-item')
collect_block = require('mineflayer-collectblock')
collect_block_plugin = collect_block.plugin  # The actual plugin to load
auto_eat = require('mineflayer-auto-eat')
auto_eat_plugin = auto_eat.plugin  # The actual plugin to load (or auto_eat.loader in some versions)
armor_manager = require('mineflayer-armor-manager')
vec3 = require('vec3')

mcdata = minecraft_data("1.21.1")
prismarine_item = prismarine_items("1.21.1")

def get_entity_names() : 
    return [
        # "area_effect_cloud", "axolotl", "block_display", "blaze", 
        # "command_block_minecart", 
        # "arrow", "armor_stand", "boat", "chest_boat", "chest_minecart",
        "alley", "cod", "dolphin", "bat", "bee", 
        "camel", "cat", "cave_spider", "chicken", "egg",
        # "cow", "donkey", "dragon_fireball"
        # "creeper", "dragon_fireball", "elder_guardian",
    ] 

def get_entity_id(entity_name) :
    entity_id = None
    entity = mcdata.entitiesByName[entity_name]
    if entity is not None :
        entity_id = entity.id
    return entity_id

def get_entity_name(entity_id) :
    entity_name = None
    entity = mcdata.entities[entity_id]
    if entity is not None :
        entity_name = entity.name
    return entity_name 

def get_entity_display_name(entity_id) :
    entity_display_name = None
    entity = mcdata.entities[entity_id]
    if entity is not None :
        entity_display_name = entity.displayName
    return entity_display_name 

def get_block_names(ignore = None) : 
    names = [block.name for block in get_all_blocks(ignore)]
    return names

def get_all_blocks(ignore = None) :
    if ignore is None or not isinstance(ignore, list) :
        ignore = []
    blocks = []
    for key in mcdata.blocks :
        block = mcdata.blocks[key]
        if block.name not in ignore :
            blocks.append(block)
    return blocks

def get_empty_block_names() : 
    return ["air", "water", "lava", "grass", "short_grass", "tall_grass", "snow", "dead_bush", "fern"] 

def get_door_types() : 
    return [
        "oak_door", "spruce_door", "birch_door", "jungle_door", "acacia_door", 
        "dark_oak_door", "mangrove_door", "cherry_door", "bamboo_door", 
        "crimson_door", "warped_door", 
    ]

def get_wool_colors() :
    return [ 
        "white", "orange", "magenta", "light_blue", "yellow",
        "lime", "pink", "gray", "light_gray", "cyan",
        "purple", "blue", "brown", "green", "red",
        "black",
    ]

def get_wood_types() : 
    return ["oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry"]

def get_wood_block_shapes() : 
    return [
        'log', 'planks',
        'sign', 'boat', 'fence_gate',
        'door', 'fence',
        'slab', 'stairs',
        'button', 'pressure_plate', 'trapdoor'
    ]

def get_cant_build_off_block_names() : 
    return ["bed", "_table", "furnace", "chest"] 

def get_block_id(block_name) :
    block_id = None
    block = mcdata.blocksByName[block_name]
    if block is not None :
        block_id = block.id
    return block_id

def get_block_ids_by_keyword(keyword) :
    """Find all block IDs whose name contains the given keyword (substring match). Returns a list of block IDs."""
    block_ids = []
    for key in mcdata.blocks :
        block = mcdata.blocks[key]
        if keyword in block.name :
            block_ids.append(block.id)
    return block_ids

def get_entity_ids_by_keyword(keyword) :
    """Find all entity IDs whose name contains the given keyword (substring match). Returns a list of entity IDs."""
    entity_ids = []
    for key in mcdata.entities :
        entity = mcdata.entities[key]
        if keyword in entity.name :
            entity_ids.append(entity.id)
    return entity_ids

def get_block_name(block_id) :
    block_name = None
    block = mcdata.blocks[block_id]
    if block is not None :
        block_name = block.name
    return block_name 

def get_block_display_name(block_id) :
    block_display_name = None
    block = mcdata.blocks[block_id]
    if block is not None :
        block_display_name = block.displayName
    return block_display_name 

def get_display_name_of_block(block_name) :
    display_name = get_block_display_name(get_block_id(block_name))
    display_name = display_name if display_name is not None else block_name
    return display_name 

def get_item_names() : 
    return get_block_names() + [
        "wooden_sword", "stone_sword", "iron_sword", 
        "wooden_shovel", "stone_shovel", "iron_shovel", 
        "wooden_axe", "stone_axe", "iron_axe",
        "wooden_pickaxe", "stone_pickaxe", "iron_pickaxe",
    ]

def get_item_id(item_name) :
    item_id = None
    item = mcdata.itemsByName[item_name]
    if item is not None :
        item_id = item.id
    return item_id

# Generic name aliases that map to multiple specific Minecraft items.
# The resolve function picks the best match based on inventory contents.
ITEM_ALIASES = {
    "planks": ["oak_planks", "spruce_planks", "birch_planks", "jungle_planks", "acacia_planks", "dark_oak_planks", "mangrove_planks", "cherry_planks", "bamboo_planks", "crimson_planks", "warped_planks"],
    "wood_planks": ["oak_planks", "spruce_planks", "birch_planks", "jungle_planks", "acacia_planks", "dark_oak_planks", "mangrove_planks", "cherry_planks", "bamboo_planks", "crimson_planks", "warped_planks"],
    "log": ["oak_log", "spruce_log", "birch_log", "jungle_log", "acacia_log", "dark_oak_log", "mangrove_log", "cherry_log", "bamboo_block", "crimson_stem", "warped_stem"],
    "wood": ["oak_log", "spruce_log", "birch_log", "jungle_log", "acacia_log", "dark_oak_log", "mangrove_log", "cherry_log", "bamboo_block", "crimson_stem", "warped_stem"],
    "wood_log": ["oak_log", "spruce_log", "birch_log", "jungle_log", "acacia_log", "dark_oak_log", "mangrove_log", "cherry_log", "bamboo_block", "crimson_stem", "warped_stem"],
    "boat": ["oak_boat", "spruce_boat", "birch_boat", "jungle_boat", "acacia_boat", "dark_oak_boat", "mangrove_boat", "cherry_boat", "bamboo_raft"],
    "chest_boat": ["oak_chest_boat", "spruce_chest_boat", "birch_chest_boat", "jungle_chest_boat", "acacia_chest_boat", "dark_oak_chest_boat", "mangrove_chest_boat", "cherry_chest_boat", "bamboo_chest_raft"],
    "coal": ["coal", "charcoal"],
    "stripped_log": ["stripped_oak_log", "stripped_spruce_log", "stripped_birch_log", "stripped_jungle_log", "stripped_acacia_log", "stripped_dark_oak_log", "stripped_mangrove_log", "stripped_cherry_log", "stripped_crimson_stem", "stripped_warped_stem"],
    "stripped_wood": ["stripped_oak_wood", "stripped_spruce_wood", "stripped_birch_wood", "stripped_jungle_wood", "stripped_acacia_wood", "stripped_dark_oak_wood", "stripped_mangrove_wood", "stripped_cherry_wood", "stripped_crimson_hyphae", "stripped_warped_hyphae"],
    "wood_slab": ["oak_slab", "spruce_slab", "birch_slab", "jungle_slab", "acacia_slab", "dark_oak_slab", "mangrove_slab", "cherry_slab", "bamboo_slab", "crimson_slab", "warped_slab"],
    "wood_stairs": ["oak_stairs", "spruce_stairs", "birch_stairs", "jungle_stairs", "acacia_stairs", "dark_oak_stairs", "mangrove_stairs", "cherry_stairs", "bamboo_stairs", "crimson_stairs", "warped_stairs"],
    "wood_fence": ["oak_fence", "spruce_fence", "birch_fence", "jungle_fence", "acacia_fence", "dark_oak_fence", "mangrove_fence", "cherry_fence", "bamboo_fence", "crimson_fence", "warped_fence"],
    "wood_door": ["oak_door", "spruce_door", "birch_door", "jungle_door", "acacia_door", "dark_oak_door", "mangrove_door", "cherry_door", "bamboo_door", "crimson_door", "warped_door"],
    "wood_trapdoor": ["oak_trapdoor", "spruce_trapdoor", "birch_trapdoor", "jungle_trapdoor", "acacia_trapdoor", "dark_oak_trapdoor", "mangrove_trapdoor", "cherry_trapdoor", "bamboo_trapdoor", "crimson_trapdoor", "warped_trapdoor"],
    "wool": ["white_wool", "orange_wool", "magenta_wool", "light_blue_wool", "yellow_wool", "lime_wool", "pink_wool", "gray_wool", "light_gray_wool", "cyan_wool", "purple_wool", "blue_wool", "brown_wool", "green_wool", "red_wool", "black_wool"],
    "sand": ["sand", "red_sand"],
}

def resolve_item_name(item_name, inventory=None):
    """Resolve a generic item name to a specific Minecraft item name.
    If inventory is provided, prefers items the bot already has materials for.
    Returns the original name if it's already specific or not an alias."""
    # Direct lookup - already a specific name
    if item_name in mcdata.itemsByName:
        return item_name

    # Check if it's a known alias
    candidates = ITEM_ALIASES.get(item_name)
    if not candidates:
        return item_name

    # If we have inventory info, prefer candidates we can actually craft
    if inventory:
        for candidate in candidates:
            if candidate in inventory and inventory[candidate] > 0:
                return candidate

    # Default to first candidate (usually oak)
    for candidate in candidates:
        if candidate in mcdata.itemsByName:
            return candidate

    return item_name

def get_item_name(item_id) :
    item_name = None
    item = mcdata.items[item_id]
    if item is not None :
        item_name = item.name
    return item_name 

def get_item_display_name(item_id) :
    item_display_name = None
    item = mcdata.items[item_id]
    if item is not None :
        item_display_name = item.displayName
    return item_display_name 

def make_item(item_name, amount = 1) :
    return prismarine_item(get_item_id(item_name), amount)

def get_all_block_ids(ignore = None) :
    block_ids = []
    blocks = get_all_blocks(ignore)
    for block in blocks : 
        block_ids.append(block.id)
    return block_ids

def must_collect_manually(block_name) :
    full_names = [
        'wheat', 'carrots', 'potatoes', 'beetroots', 'nether_wart', 'cocoa', 
        'sugar_cane', 'kelp', 'short_grass', 'fern', 'tall_grass', 'bamboo', 
        'poppy', 'dandelion', 'blue_orchid', 'allium', 'azure_bluet', 'oxeye_daisy', 
        'cornflower', 'lilac', 'wither_rose', 'lily_of_the_valley', 'wither_rose', 
        'lever', 'redstone_wire', 'lantern', 
    ]
    partial_names = [
        'sapling', 'torch', 'button', 'carpet', 'pressure_plate', 
        'mushroom', 'tulip', 'bush', 'vines', 'fern',
    ]
    return block_name.lower() in full_names or any([partial_name in block_name.lower() for partial_name in partial_names])
    
def get_top_k_similar_items(target, items, k = 1, threshold = -1) :
    common_letter_counts = []
    for item in items :
        common_letters = set(target).intersection(set(item))
        if len(common_letters) > threshold : 
            count = len(common_letters)
            common_letter_counts.append((item, count))

    common_letter_counts.sort(key=lambda x: x[1], reverse=True)
    top_k_items = [item[0] for item in common_letter_counts[:k]]
    return top_k_items

def get_item_crafting_recipes(item_name) :
    item_id = get_item_id(item_name)
    if item_id not in mcdata.recipes :
        return None

    recipes = []
    for r in mcdata.recipes[item_id] :
        recipe, ingredients = {}, []
        if r.ingredients is not None :
            ingredients = r.ingredients
        elif r.inShape is not None : 
            ingredients = r.inShape.flat()
        for ingredient in ingredients :
            ingredient_name = get_item_name(ingredient)
            if ingredient_name is None :
                continue
            if ingredient_name not in recipe.keys() :
                recipe[ingredient_name] = 0
            recipe[ingredient_name] += 1
        recipes.append([recipe, {"crafted_count" : r.result.count}])

    recipes = sorted(recipes, key = functools.cmp_to_key(recipt_sort_by_common_items)) 
    return recipes

def recipt_sort_by_common_items(a, b) : 
    common_items = ['oak_planks', 'oak_log', 'coal', 'cobblestone']
    common_count_a = 0
    common_count_b = 0
    for key, value in a[0].items() : 
        if key in common_items : 
            common_count_a += value
    for key, value in b[0].items() : 
        if key in common_items : 
            common_count_b += value
    return common_count_b - common_count_a

def ingredients_from_prismarine_recipe(recipe) :
    required_ingredients = {}
    if recipe.inShape is not None :
        for ingredient in recipe.inShape.flat() :
            if ingredient.id < 0 :
                 continue # prismarine-recipe uses id -1 as an empty crafting slot
            ingredient_name = get_item_name(ingredient.id)
            if ingredient_name not in required_ingredients.keys() :
                required_ingredients[ingredient_name] = 0
            required_ingredients[ingredient_name] += ingredient.count

    if recipe.ingredients is not None :
        for ingredient in recipe.ingredients :
            if ingredient.id < 0 :
               continue
            ingredient_name = get_item_name(ingredient.id)
            if ingredient_name not in required_ingredients.keys() :
                required_ingredients[ingredient_name] = 0
            required_ingredients[ingredient_name] -= ingredient.count

    return required_ingredients

def calculate_limiting_resource(available_items, required_items, discrete = True) :
    limiting_resource = None
    num = math.inf 
    for item_name in required_items :
        if available_items[item_name] < required_items[item_name] * num :
            limiting_resource = item_name
            num = available_items[item_name] / required_items[item_name]
    if discrete == True :
        num = math.floor(num)
    return {"num" : num, "limiting_resource" : limiting_resource}

