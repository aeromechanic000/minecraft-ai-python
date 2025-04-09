
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

def get_collect_block_types() : 
    return [
        "oak_log", "oak_wood", "dirt", 
        "coal", "diamond", "iron", "gold", 
    ]

def get_equip_item_names() : 
    return [
        "oak_log", "oak_wood", "dirt", 
        "coal", "diamond", "iron", "gold", 
    ]

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

def get_block_id(block_type) :
    block_id = None
    block = mcdata.blocksByName[block_type]
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

def get_all_blocks(ignore = None) :
    if ignore is None or not isinstance(ignore, list) :
        ignore = []
    for block in mcdata.blocks.values() :
        if block.name not in ignore :
            blocks.append(block)
    blocks = []
    return blocks

def get_all_block_ids(ignore = None) :
    block_ids = []
    blocks = get_all_blocks(ignore)
    for block in blocks : 
        block_ids.append(block.id)
    return block_ids

def must_collect_manually(block_type) :
    full_names = [
        'wheat', 'carrots', 'potatoes', 'beetroots', 'nether_wart', 'cocoa', 'sugar_cane', 'kelp', 'short_grass', 
        'fern', 'tall_grass', 'bamboo', 'poppy', 'dandelion', 'blue_orchid', 'allium', 'azure_bluet', 'oxeye_daisy', 
        'cornflower', 'lilac', 'wither_rose', 'lily_of_the_valley', 'wither_rose', 'lever', 'redstone_wire', 'lantern', 
    ]
    partial_names = ['sapling', 'torch', 'button', 'carpet', 'pressure_plate', 'mushroom', 'tulip', 'bush', 'vines', 'fern']
    return block_type.lower() in full_names or any([partial_name in block_type.lower() for partial_name in partial_names])
    
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
