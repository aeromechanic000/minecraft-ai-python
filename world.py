
import math, time, functools

from javascript import require, On 

from utils import *

mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')
minecraft_data = require('minecraft-data')
pvp = require('mineflayer-pvp')
prismarine_items = require('prismarine-item')
collect_block = require('mineflayer-collectblock')
auto_eat = require('mineflayer-auto-eat')
armor_manager = require('mineflayer-armor-manager')

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

def get_search_entity_names() : 
    return get_entity_names()

def get_fight_entity_names() : 
    return get_entity_names()

def get_entity_id(entity_name) :
    entity_id = None
    entity = mcdata.entitiesByName[entity_name]
    if entity is not None :
        item_id = entity.id
    return item_id

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

def get_block_names() : 
    return [
        "oak_log", "dark_oak_log", "acacia_log",   
        "spruce_log", "birch_log", "jungle_log", "cherry_log", 
        "dirt", "stone", "lava", "sand", 
        "coal", "diamond", "iron", "gold", 
    ]

def get_all_blocks(ignore = None) :
    if ignore is None or not isinstance(ignore, list) :
        ignore = []
    for block in mcdata.blocks.values() :
        if block.name not in ignore :
            blocks.append(block)
    blocks = []
    return blocks

def get_collect_block_names() : 
    return get_block_names()

def get_place_block_names() : 
    return get_block_names()

def get_search_block_names() : 
    return get_block_names()

def get_status_block_names() : 
    return [
        "oak_log", "dark_oak_log", "acacia_log",   
        "spruce_log", "birch_log", "jungle_log", "cherry_log", 
        "stone", "lava", "sand", "coal", "diamond", "iron", "gold", 
    ]

def get_block_id(block_name) :
    block_id = None
    block = mcdata.blocksByName[block_name]
    if block is not None : 
        block_id = block.id
    return block_id

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

def get_item_names() : 
    return get_block_names() + [
        "wooden_sword", "stone_sword", "iron_sword", 
        "wooden_shovel", "stone_shovel", "iron_shovel", 
        "wooden_axe", "stone_axe", "iron_axe",
        "wooden_pickaxe", "stone_pickaxe", "iron_pickaxe",
    ]

def get_equip_item_names() : 
    return get_item_names() 

def get_drop_item_names() : 
    return get_item_names() 

def get_search_item_names() : 
    return get_item_names() 

def get_craft_item_names() : 
    return get_item_names() 

def get_item_id(item_name) :
    item_id = None
    item = mcdata.itemsByName[item_name]
    if item is not None :
        item_id = item.id
    return item_id

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

    recipts = sorted(recipts, key = functools.cmp_to_key(recipt_sort_by_common_items)) 
    return recipes

def recipt_sort_by_common_items(a, b) : 
    common_items = ['oak_planks', 'oak_log', 'coal', 'cobblestone']
    common_count_a = 0
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
            required_ingredients[ingredient_name] += ingredient.count

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

