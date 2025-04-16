
import math, time, functools 
from javascript import require, On 

from model import *
from world import *
from utils import *
 
def get_actions(action_names = None) : 
    availabel_actions = [
        {
            "name" : "go_to_player", 
            "desc": "Go to the given player.",
            "params": {
                "player_name": {"type" : "string", "desc" : "The name of the player to go to.", "domain" : "any valid value"},
                "closeness": {"type" : "float", "desc" : "How close to get to the player. If no special reason, closeness should be set to 1.", "domain" : [0, math.inf]},
            },
            "perform" : "go_to_player", 
        },
        {
            "name" : "move_away", 
            "desc": "Move away from the current location in any direction by a given distance.",
            "params": {
                "distance": {"type" : "float", "desc" : "The distance to move away.", "domain": [20, math.inf]},
            },
            "perform" : "move_away", 
        },
        {
            "name" : "drop",
            "desc" : "Drop the given item from the inventory.",
            "params" : {
                "item_name" : {"type" : "ItemName", "desc" : "The name of the item to drop.", "domain" : get_drop_item_names()},
                "num" : {"type" : "int", "desc" : "The number of items to drop.", "domain" : [1, 16]}
            },
            "perform" : "drop",
        },
        {
            "name" : "pick",
            "desc" : "Pick up the nearby items.",
            "params" : {
                "max_distance": {"type" : "float", "desc" : "The maximum distance of items to pick up.", "domain": [1, 16]},
                "num" : {"type" : "int", "desc" : "The number of items to pick up.", "domain" : [1, 16]}
            },
            "perform" : "pickup_nearby_items",
        },
        {
            "name" : "collect_blocks",
            "desc" : "Collect the nearest blocks of a given type.",
            "params" : {
                "block_name" : {"type": "BlockName", "desc": "The block name to collect.", "domain" : get_collect_block_names()},
                "num" : {"type": "int", "desc" : "The number of blocks to collect.", "domain" : [1, 16]}
            },
            "perform" : "collect_blocks", 
        },
        {
            "name" : "place_block",
            "desc" : "Place a block on a specified position (which should be next to some existing blocks).",
            "params" : {
                "block_name" : {"type": "BlockName", "desc": "The block name to collect.", "domain" : get_place_block_names()},
                "x" : {"type": "float", "desc": "value of x-coordinate of the position to place the block.", "domain" : [-math.inf, math.inf]},
                "y" : {"type": "float", "desc": "value of y-coordinate of the position to place the block.", "domain" : [-math.inf, math.inf]},
                "z" : {"type": "float", "desc": "value of z-coordinate of the position to place the block.", "domain" : [-math.inf, math.inf]},
            },
            "perform" : "place_block", 
        },
        {
            "name" : "equip",
            "desc" : "Equip the given item.",
            "params" : {
                "item_name": { "type" : "ItemName", "desc" : "The name of the item to equip.", "domain" : get_equip_item_names()}, 
            },
            "perform" : "equip",
        },
        {
            "name" : "fight",
            "desc" : 'Attack and kill the nearest entity of a given type.',
            "params": {
                "entity_name": { "type" : "string", "desc" : "The type of entity to attack.", "domain" : get_fight_entity_names()}
            },
            "perform" : "fight",
        },
        {
            "name" : "craft",
            "desc" : "Craft the given recipe a given number of times.",
            "params" : {
                "recipe_name": {"type" : "ItemName", "desc" : "The name of the output item to craft.", "domain" : get_craft_item_names()},
                "num" : {"type" : "int", "desc" : "The number of times to craft the recipe. This is NOT the number of output items, as it may craft many more items depending on the recipe.", "domain" : [1, 4]}
            },
            "perform" : "craft",
        },
        {
            "name" : "chat", 
            "desc": "Chat with others.",
            "params": {
                "player_name": {"type" : "string", "desc" : "The name of the player to mention in the chat.", "domain" : "either the name of any player in the game, or 'all' to mention all the players"},
                "message": {"type" : "string", "desc" : "The message to send.", "domain" : "any valid text"},
            },
            "perform" : "chat", 
        },
    ]
    actions = []
    for action in availabel_actions : 
        if not isinstance(action_names, list) or action["name"] in action_names :
            actions.append(action) 
    return actions

def validate_param(value, _type, domain) :
    valid_value = None
    if value is not None :
        try : 
            if _type == "string" : 
                valid_value = str(value)
            elif _type == "float" : 
                valid_value = float(value)
                valid_value = min(max(domain[0], valid_value), domain[1])
            elif _type == "int" : 
                valid_value = int(value)
                valid_value = min(max(domain[0], valid_value), domain[1])
            elif _type == "BlockName" : 
                valid_value = str(value)
                block_names = get_block_names()
                if valid_value not in block_names : 
                    top_k_items = get_top_k_similar_items(valid_value, block_names, k = 1, threshold = max(2, len(valid_value) / 2))
                    valid_value = top_k_items[0] if len(top_k_items) > 0 else None
            elif _type == "ItemName" : 
                valid_value = str(value)
                item_names = get_item_names()
                if valid_value not in item_names : 
                    top_k_items = get_top_k_similar_items(valid_value, item_names, k = 1, threshold = max(2, len(valid_value) / 2))
                    valid_value = top_k_items[0] if len(top_k_items) > 0 else None
        except : 
            valid_value = None
    return valid_value

class Agent(object) : 
    def __init__(self, configs, mcp_manager) :
        add_log(title = "Agent Created.", content = "Agent has been created with configs: %s" % configs, label = "header")
        self.configs, self.mcp_manager = configs, mcp_manager
        bot_configs = self.configs.copy()
        bot_configs.update({
            "host" : self.mcp_manager.configs["host"],
            "port" : self.mcp_manager.configs["port"],
            "version" : self.mcp_manager.configs["minecraft_version"],
        })
        self.bot = mineflayer.createBot(bot_configs)
        self.bot.loadPlugin(pathfinder.pathfinder)
        self.bot.loadPlugin(pvp.plugin)
        self.bot.loadPlugin(collect_block.plugin)
        self.bot.loadPlugin(auto_eat.loader)
        self.bot.loadPlugin(armor_manager) 

        @On(self.bot, 'resourcePack')
        def handle_resource_pack(*args) :
            self.bot.acceptResourcePack()

        @On(self.bot, 'spawn')
        def handle_spawn(*args) :
            self.plan_thread, self.act_thread = None, None
            self.status_summary, self.recent_actions = "", [] 
            self.messages, self.actions = [], []
            self.plan_running, self.act_running = False, False
            add_log(title = self.pack_message("I spawned."), label = "success")
            self.movements = pathfinder.Movements(self.bot)
            viewer_port = self.configs.get("viewer_port", None)
            viewer_first_person = self.configs.get("viewer_first_person", False)
            viewer_distance = self.configs.get("viewer_distance", 6)
            if viewer_port is not None : 
                require('canvas')
                viewer = require('prismarine-viewer')
                viewer["mineflayer"](self.bot, {"port": viewer_port, "firstPerson" : viewer_first_person, "viewDistance" : viewer_distance})
            self.action_perform = {}

            def Action(name = None) :
                def decorator(func):
                    nonlocal name
                    name = name if name is not None else func.__name__
                    self.action_perform[name] = func
                    return func
                return decorator

            @On(self.bot, "end")
            def handle_end(*args):
                self.bot.quit()
                add_log(title = self.pack_message("Bot end."), label = "execute")
                self.stop()
                self.mcp_manager.stop()

            @On(self.bot, 'chat')
            def handle_msg(this, sender, message, *args):
                message = message.strip()
                if sender is not None and all([not message.startswith(msg) for msg in self.mcp_manager.configs.get("ignored_messages", [])]) :
                    if sender == self.bot.username : 
                        if random.random() < self.configs.get("reflection", 0.0) : 
                            self.push_msg({"sender" : sender, "message" : message, "type" : "whisper"})
                    elif sender not in self.configs.get("ignored_senders", []) :
                        if "@%s" % self.bot.username in message or "@all" in message or "@All" in message or "@ALL" in message : 
                            self.push_msg({"sender" : sender, "message" : message, "type" : "whisper"})
                        else : 
                            self.push_msg({"sender" : sender, "message" : message, "type" : "update"})
                    else : 
                        add_log(title = self.pack_message("Ignored message."), content = "{\"sender\" : \"%s\", \"message\" : \"%s\"}" % (sender, message), print = False)
                
                if self.plan_running == False : 
                    while len(self.messages) > 0 and any([message["type"] == "whisper" for message in self.messages]) :
                        self.plan_running = True
                        messages = self.messages.copy()
                        self.messages.clear()
                        add_log(title = self.pack_message("Process messages."), content = str(messages), label = "execute")
                        prompt = self.build_plan_prompt(
                            get_status_info(self.configs.get("status_blocks_range", 8), self.configs.get("status_entities_range", 8)), 
                            get_messages_info(messages), 
                        )
                        llm_result = call_llm_api(self.configs["provider"], self.configs["model"], prompt, max_tokens = self.configs.get("max_tokens", 4096))
                        if llm_result["status"] > 0 :
                            add_log(title = self.pack_message("Error in calling LLM to get plan: %s" % llm_result["error"]))
                        else :
                            add_log(title = self.pack_message("LLM response to get plan: %s" % llm_result), print = False)
                            _, data = split_content_and_json(llm_result["message"])
                            add_log(title = self.pack_message("Got plan data: %s" % data), print = False)
                            self.update_status(data)
                            action = self.mcp_manager.extract_action(data)
                            if action is not None : 
                                self.push_action(action)
                            if self.act_running == False : 
                                actions = []
                                while len(self.actions) > 0 : 
                                    self.act_running = True
                                    actions += self.actions.copy()
                                    self.actions.clear()
                                    add_log(title = self.pack_message("Got actions."), content = str(actions), label = "execute")
                                    while len(actions) > 0 : 
                                        action = actions.pop(0) 
                                        add_log(title = self.pack_message("Perfom action."), content = str(action), label = "execute")
                                        try : 
                                            perform = self.action_perform.get(action["perform"], invalid_perform) 
                                            perform(**action["params"])
                                            if perform is not invalid_perform : 
                                                self.recent_actions.append(action["name"])
                                                while len(self.recent_actions) > self.mcp_manager.configs.get("action_history_limit", 5) : 
                                                    self.recent_actions.pop(0)
                                            else : 
                                                add_log(title = self.pack_message("Invalid perform."), label = "warning")
                                                add_log(title = self.pack_message("Invalid perform"), content = "Name of perform: %s" % action["perform"], print = False)
                                        except Exception as e : 
                                            add_log(title = self.pack_message("Exception in performing action."), label = "error")
                                            add_log(title = self.pack_message("Act."), content = "Exception: %s" % e, label = "error", print = False)
                                self.act_running = False 
                    self.plan_running = False 

            def invalid_perform(**args) : 
                print("Invalid perform.")
            
            def get_messages_info(messages) : 
                messages_info = ""
                for message in messages : 
                    messages_info += "'%s' said: %s\n" % (message["sender"], message["message"])
                return messages_info

            def get_status_info(blocks_range = 8, entities_range = 8) : 
                status = "- Agent's Name: %s\n- Status Summary: %s " % (self.bot.username, self.status_summary)
                status = "\n- Agent's Status of Health (from 0 to 20, where 0 for death and 20 for completely healthy): %s" % self.bot.health 
                status = "\n- Agent's Degree Of Hungry (from 0 to 20, where 0 for hungry and 20 for full): %s" % self.bot.food
                if self.bot.entity is not None and self.bot.entity.position is not None : 
                    pos = self.bot.entity.position
                    status = "\n- Agent's Position: x: %s, y: %s, z: %s" % (math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
                add_log(title = self.pack_message("Get status."), content = "Got agent primary status: %s" % status, print = False)
                if blocks_range > 0 :
                    blocks, blocks_info = get_nearest_blocks(block_names = get_status_block_names(), max_distance = blocks_range, count = 8), ""
                    for block in blocks : 
                        pos = block.position
                        if pos is not None :
                            blocks_info += "%s (at x: %s, y: %s, z: %s);" % (block.name,  math.floor(pos.x), math.floor(pos.y), math.floor(pos.z)) 
                    if len(blocks_info.strip()) > 0 : 
                        status += "\n- Blocks Nearby: %s" % blocks_info
                    add_log(title = self.pack_message("Get status."), content = "Got blocks info: %s" % blocks_info, print = False)
                if entities_range > 0 :
                    entities, entities_info = get_nearest_entities(max_distance = entities_range, count = 8), "" 
                    for entity in entities : 
                        pos = entity.position
                        if pos is not None :
                            entities_info += "%s (at x: %s, y: %s, z: %s);" % (entity.name,  math.floor(pos.x), math.floor(pos.y), math.floor(pos.z)) 
                    if len(entities_info.strip()) > 0 : 
                        status += "\n- Entities Nearby: %s" % entities_info
                    add_log(title = self.pack_message("Get status."), content = "Got entities info: %s" % entities_info, print = False)
                items_in_inventory, items_info = get_item_counts(), "" 
                for key, value in items_in_inventory.items() : 
                    items_info += "%s %s;" % (value, key)
                if len(items_info.strip()) > 0 : 
                    status += "\n- Items in Inventory: %s" % items_info
                add_log(title = self.pack_message("Get status."), content = "Got inventory items info: %s" % items_info, print = False)
                if len(self.recent_actions) > 0 : 
                    recent_actions_desc = self.mcp_manager.get_actions_desc(self.recent_actions)
                    if len(recent_actions_desc.strip()) > 0 : 
                        status += "\n- Recent Actions: \n%s" % recent_actions_desc
                    add_log(title = self.pack_message("Get status."), content = "Got recent actions info: %s" % recent_actions_desc, print = False)
                return status

            def get_an_item_in_hotbar(item_name) :
                items = list(filter(lambda slot : slot is not None and slot.name == item_name, self.bot.inventory.slots))
                item  = items[0] if len(items) > 0 else None
                return item

            def get_an_item_in_inventory(item_name) :
                items = list(filter(lambda item : item.name == item_name, self.bot.inventory.items()))
                item  = items[0] if len(items) > 0 else None
                return item

            @Action()
            def go_to_position(x, y, z, closeness = 0) : 
                try : 
                    self.bot.pathfinder.setMovements(pathfinder.Movements(self.bot))
                    self.bot.pathfinder.goto(pathfinder.goals.GoalNear(x, y, z, closeness)) 
                except Exception as e : 
                    add_log(title = self.pack_message("Go to Position."), content = "Exception: %s" % e, label = "warning")

            def go_to_nearest_block(block_name,  min_distance = 2, range = 64) :
                range = min(512, range)
                block = get_nearest_block(block_name, range)
                if block is None :
                    self.bot.chat("I can't find any any %s in %s blocks." % (get_block_display_name(get_block_id(block_name)), math.floor(range)))
                    add_log(title = self.pack_message("Go to Nearest Block."), content = "Can't find any any %s in %s blocks." % (get_block_display_name(get_block_id(block_name)), range), print = False)
                    return False

                self.bot.chat("Found %s at %s. I am going there." % (get_block_display_name(get_block_id(block_name)), block.position))
                add_log(title = self.pack_message("Go to Nearest Block."), content = "Found %s at %s." % (get_block_display_name(get_block_id(block_name)), block.position), print = False)
                go_to_position(block.position.x, block.position.y, block.position.z, min_distance)
                return True
            
            @Action()
            def chat(player_name, message) : 
                if player_name == "all" or self.bot.players[player_name] is not None : 
                    message = "@%s %s" % (player_name, message)
                    self.bot.chat(message)
                else : 
                    self.bot.chat(message)

            @Action()
            def go_to_player(player_name, closeness = 1) : 
                for t in range(self.mcp_manager.configs.get("action_retry_num", 1)) :
                    if self.act_running == False :
                        add_log(title = self.pack_message("Stop action befor the %d-th try." % (t + 1)))
                    else : 
                        add_log(title = self.pack_message("Try for the %d-th time." % (t + 1)))
                    player = self.bot.players[player_name]
                    if player is not None and player.entity is not None :  
                        pos = player.entity.position
                        go_to_position(pos.x, pos.y, pos.z, closeness)
                        self.bot.chat("I am here.")
                        break
                    else :
                        add_log(title = self.pack_message("Failed to get player's position."), label = "warning") 

            @Action()
            def move_away(distance) : 
                for t in range(self.mcp_manager.configs.get("action_retry_num", 1)) :
                    if self.act_running == False :
                        add_log(title = self.pack_message("Stop action befor the %d-th try." % (t + 1)))
                    else :
                        add_log(title = self.pack_message("Try for the %d-th time." % (t + 1)))
                    if self.bot.entity is not None :
                        pos = self.bot.entity.position
                        vector = get_random_vector(distance)
                        go_to_position(pos.x + vector[0], pos.y, pos.z + vector[1], 0) 
                        self.bot.chat("I moved to a new location.")
                        break
                    else : 
                        add_log(title = self.pack_message("Failed to get bot's position."), label = "warning")

            @Action()
            def collect_blocks(block_name, num, exclude = None) : 
                block_names = [block_name]
                if block_name in ["coal", "diamond", "emerald", "iron", "gold", "lapis_lazuli", "redstone", ] : 
                    block_names.append("%s_ore" % block_name)
                if block_name.endswith("ore") :
                    block_names.append("deepslate_%s" % block_name)
                if block_name == "dirt" : 
                    block_names.append("grass_block")
                init_block_count = get_item_counts().get(block_name, 0)
                collected, action_num = 0, 0
                while self.act_running == True and collected < num and action_num < self.mcp_manager.configs.get("action_repeat_num_limit", 32) :   
                    action_num += 1
                    blocks = get_nearest_blocks(block_names = block_names, max_distance = 512, count = 16)
                    if exclude is not None and isinstance(exclude, list) : 
                        blocks = list(filter(lambda block : all([block.position.x != position.x or block.position.y != position.y or block.position.z != position.z for position in exclude]), blocks))
                    movements = pathfinder.Movements(self.bot)
                    movements.dontMineUnderFallingBlock = False
                    blocks = list(filter(lambda block: movements.safeToBreak(block), blocks))
                    if len(blocks) < 1 : 
                        if collected < 1 :  
                            self.bot.chat("I don't find any %s nearby to collect." % get_block_display_name(get_block_id(block_name)))
                            add_log(title = self.pack_message("Collect Blocks"), content = "Don't find any %s nearby." % get_block_display_name(get_block_id(block_name)), print = False)
                        else :
                            self.bot.chat("Can't find more %s nearby to collect." % get_block_display_name(get_block_id(block_name)))
                            add_log(title = self.pack_message("Collect Blocks"), content = "Can't find more %s nearby." % get_block_display_name(get_block_id(block_name)), print = False)
                        break

                    block = blocks[0]
                    self.bot.tool.equipForBlock(block)
                    item_id = self.bot.heldItem if self.bot.heldItem is not None else None 
                    if not block.canHarvest(item_id) : 
                        self.bot.chat("I dont't have right tools to harvest %s." % get_block_display_name(get_block_id(block_name)))
                        break

                    try :
                        if must_collect_manually(block_name) :
                            add_log(title = self.pack_message("Collect Blocks"), content = "%s must be collected manually." % get_block_display_name(get_block_id(block_name)), print = False)
                            go_to_position(block.position.x, block.position.y, block.position.z, 2)
                            self.bot.dig(block)
                            pickup_nearby_items()
                        else :
                            self.bot.collectBlock.collect(block)
                        block_count = get_item_counts().get(block_name, 0)
                        collected = block_count - init_block_count
                        self.auto_light()
                    except Exception as e :
                        add_log(title = self.pack_message("Collect Blocks"), content = "Exception in collecting %s." % get_block_display_name(get_block_id(block_name)), label = "warning")
                        add_log(title = self.pack_message("Collect Blocks"), content = "Exception in collecting %s: %s" % (get_block_display_name(get_block_id(block_name)), e), label = "warning", print = False)

                    if self.bot.interrupt_code :
                        break;  

                self.bot.chat("I have collected %d %s." % (collected, get_block_display_name(get_block_id(block_name))))
                return collected > 0
            
            def get_nearest_blocks(block_names = None, max_distance = 64, count = 16) :
                block_ids = []
                if block_names is None or not isinstance(block_names, list) : 
                    block_ids = get_all_block_ids(['air'])
                else : 
                    for block_name in block_names :
                        block_id = get_block_id(block_name)
                        if block_id is not None : 
                            block_ids.append(block_id)
                positions = self.bot.findBlocks({"matching" : block_ids, "maxDistance" : max_distance, "count" : count})
                blocks = []
                for i in range(positions.length) : 
                    try : 
                        block = self.bot.blockAt(positions[i])
                        dist = positions[i].distanceTo(self.bot.entity.position)
                        blocks.append({"block" : block, "distance" : dist})
                    except Exception as e : 
                        add_log(title = self.pack_message("get_nearest_blocks"), content = "Exception: %s" % e, print = False)
                blocks = sorted(blocks, key = functools.cmp_to_key(lambda a, b : a["distance"] - b["distance"]))
                return [block["block"] for block in blocks]
        
            def get_nearest_block(block_name, max_distance = 64) :
                blocks = get_nearest_blocks(block_names = [block_name], max_distance = max_distance, count = 1)
                if len(blocks) > 0 :
                    return blocks[0]
                return None 
        
            def get_nearest_item(distance = 1) : 
                entity = None 
                try : 
                    entity = self.bot.nearestEntity(lambda entity : entity.name == 'item' and self.bot.entity.position.distanceTo(entity.position) < distance)
                except Exception as e : 
                    entity = None
                    add_log(title = self.pack_message("get_nearest_item"), content = "Exception: %s" % e, print = False)
                return entity

            @Action("pick")
            def pickup_nearby_items(self, max_distance = 8, num = 8) : 
                nearest_item = get_nearest_item(distance = max_distance)
                prev_item = nearest_item
                picked_up = 0
                while nearest_item and picked_up < num :
                    try : 
                        self.bot.pathfinder.setMovements(pathfinder.Movements(self.bot))
                        self.bot.pathfinder.goto(pathfinder.goals.GoalFollow(nearest_item, 0.8), True)
                        time.sleep(0.2)
                        prev_item = nearest_item
                        nearest_item = get_nearest_item(distance = max_distance)
                        if prev_item == nearest_item :
                            break
                        picked_up += 1
                    except Exception as e : 
                        add_log(title = self.pack_message("pickup_nearby_items"), content = "Exception: %s" % e, label = "warning", print = False)
                self.bot.chat("I picked up %d items" % picked_up)
                return True

            def should_place_torch() : 
                if self.bot.modes is not None and self.bot.modes.isOn('torch_placing') or self.bot.interrupt_code :
                    return False
                pos = self.bot.entity.position
                nearest_torch = get_nearest_block('torch', 6)
                if nearest_torch is None :
                    nearest_torch = get_nearest_block('wall_torch', 6)
                if nearest_torch is None : 
                    block = self.bot.blockAt(pos)
                    if block is None :
                        return False
                    else :
                        has_torch = any([item.name == "torch" for item in self.bot.inventory.items()])
                        return has_torch and block.name == 'air'
                return False

            def auto_light() : 
                if should_place_torch() :
                    try : 
                        pos = self.bot.entity.position
                        place_block('torch', pos.x, pos.y, pos.z, 'bottom', True)
                    except Exception as e : 
                        return False
                return False
            
            def break_block_at(x, y, z) : 
                if x is None or y is None or z is None : 
                    return False

                block = self.bot.blockAt(Vec3([x, y, z]))
                if block.name != "air" and block.name != "water" and block.name != "lava" :
                    if self.bot.modes.isOn("cheat") :
                        msg = "/setblock %d %d %d air" % (math.floor(x), math.floor(y), math.floor(z))
                        self.bot.chat(msg)
                        add_log(title = self.pack_message("Break block."), content = "Used /setblock to break block at ($d, %d, %d)." % (math.floor(x), math.floor(y), math.floor(z)), print = False)
                        return True

                    if self.bot.entity.position.distanceTo(block.position) > 4.5 :
                        pos = block.position
                        movements = pathfinder.Movements(self.bot)
                        movements.canPlaceOn = False
                        movements.allow1by1towers = False
                        self.bot.pathfinder.setMovements(movements)
                        self.bot.pathfinder.goto(pathfinder.goals.GoalNear(pos.x, pos.y, pos.z, 4))

                    if self.bot.game.gameMode != "creative" :
                        self.bot.tool.equipForBlock(block)
                        item_id = self.bot.heldItem.type if self.bot.heldItem is not None else None 
                        if not block.canHarvest(item_id) :
                            self.bot.chat("I Don't have right tools to break %s." % block.displayName)
                            return False

                    self.bot.dig(block, True)
                    add_log(title = self.pack_message("Break block."), content = "Broke %s at (%s, %s, %s)." % (block.displayName, x, y, z), print = False)
                else :
                    add_log(title = self.pack_message("Break block."), content = "Skipping %s at (%s, %s, %s)." % (block.displayName, x, y, z), print = False)
                    return False
                return True

            @Action()
            def place_block(block_name, x, y, z, place_on = 'bottom', dont_cheat = False) :
                if get_block_id(block_name) is None and block_name != 'air' :
                    self.bot.chat("%s is invalid block name." % block_name, print = False)
                    add_log(title = self.pack_message("Place block."), content = "Invalid block name to place: %s" % block_name, print = False)
                    return False

                target_dest = [math.floor(x), math.floor(y), math.floor(z)]
                if block_name == 'air' :
                    add_log(title = self.pack_message("Place block."), content = "Placing air (removing block) at: %s" % target_dest, print = False)
                    break_block_at(x, y, z)

                if self.bot.modes is not None and self.bot.modes.isOn('cheat') and not dont_cheat :
                    if self.bot.restrict_to_inventory :
                        block = get_an_item_in_inventory(block_name)
                        if block is None :
                            add_log(title = self.pack_message("Place block."), content = "Cannot place %s. Restricted to the current inventory." % block_name, label = "warning")
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
                    self.bot.chat(msg)

                    if "door" in block_name :
                        msg = "/setblock %d %d %d %s [half=upper]" % (math.floor(x), math.floor(y + 1), math.floor(z), block_name)
                        self.bot.chat(msg)

                    if "bed" in block_name :
                        msg = "/setblock %d %d %d %s [part=head]" % (math.floor(x), math.floor(y), math.floor(z - 1), block_name)
                        self.bot.chat(msg)

                    add_log(title = self.pack_message("Place block."), content = "Used /setblock to place block %s at %s." % (block_name, target_dest), print = False)
                    return True
                
                item_name = block_name
                if item_name == "redstone_wire" : 
                    item_name = "redstone"

                block = get_an_item_in_inventory(item_name) 

                if block is None and self.bot.game.gameMode == 'creative' and not self.bot.restrict_to_inventory :
                    self.bot.creative.setInventorySlot(36, make_item(item_name, 1)) 
                    block = get_an_item_in_inventory(item_name) 

                if block is None :
                    add_log(title = self.pack_message("Place block."), content = "Have no %s to place." % block_name, print = False)
                    return False

                target_block = self.bot.blockAt(Vec3(target_dest))
                if target_block is not None : 
                    if target_block.name == block_name :
                        add_log(title = self.pack_message("Place block."), content = "%s already at %s." % (block_name, target_block.position), print = False)
                        return False

                    if target_block.name not in get_empty_blocks() :
                        add_log(title = self.pack_message("Place block."), content = "%s in the way at %s." % (block_name, target_block.position), print = False)
                        removed = break_block_at(x, y, z)
                        if removed == False :
                            add_log(title = self.pack_message("Place block."), content = "Cannot place %s at %s (block in the way)." % (block_name, target_block.position), print = False)
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
                    add_log(title = self.pack_message("Place block."), content = "Unknown place_on value: %s. Defaulting to bottom." % place_on, print = False)
                
                for d in dir_map.values() : 
                    if d not in dirs : 
                        dirs.append(d)

                for d in dirs :
                    b = self.bot.blockAt(Vec3([target_dest[0] + d[0], target_dest[1] + d[1], target_dest[2] + d[2]]), True)
                    if b is not None and b.name not in get_empty_blocks() :
                        build_off_block = b
                        face_vec = [-d[0], -d[1], -d[2]] 
                        break

                if build_off_block is None : 
                    self.bot.chat("I Can't place %s at %s. Nothing to place on." % (block_name, target_dest))
                    add_log(title = self.pack_message("Place block."), content = "Cannot place %s at %s (nothing to place on)." % (block_name, target_dest), print = False)
                    return False

                if self.bot.entity is not None and self.bot.entity.position.distanceTo(Vec3(target_dest)) > 3 :
                    go_to_position(target_dest[0], target_dest[1], target_dest[2], 2)
                
                self.bot.equip(block, 'hand')
                self.bot.lookAt(build_off_block.position)

                try :
                    print(build_off_block, face_vec)
                    self.bot.placeBlock(build_off_block, face_vec)
                    add_log(title = self.pack_message("Place block."), content = "Placed %s at %s." % (block_name, target_dest), print = False)
                    return True
                except Exception as e :
                    add_log(title = self.pack_message("Place block."), content = "Execption in calling bot.placeBlock.", label = "warning")
                    add_log(title = self.pack_message("Place block."), content = "Execption: %s" % e, print = False)
                    return False

            @Action()
            def equip(item_name) :
                item = get_an_item_in_hotbar(item_name)
                if item is None : 
                    self.bot.chat("I don't have any %s to equip." % get_item_display_name(get_item_id(item_name)))
                    return False

                if "legging" in item_name : 
                    self.bot.equip(item, 'legs')
                elif "boots" in item_name : 
                    self.bot.equip(item, 'feet')
                elif "helmet" in item_name :
                    self.bot.equip(item, 'head')
                elif "chestplate" in item_name or "elytra" in item_name :
                    self.bot.equip(item, 'torso')
                elif "shield" in item_name :
                    self.bot.equip(item, 'off-hand')
                else :
                    self.bot.equip(item, 'hand')

                self.bot.chat("I am equipped %s." % item_name)
                return True

            @Action()
            def drop(item_name, num = -1) :
                dropped = 0
                while True :
                    item = get_an_item_in_inventory(item_name)
                    if item is None :
                        break
                    to_drop = item.count if num < 0 else min(num - dropped, item.count)
                    self.bot.toss(item.type, None, to_drop)
                    dropped += to_drop
                    if num >= 0 and dropped >= num :
                        break

                if dropped < 1 :
                    self.bot.chat("I don't have any %s to drop." % get_item_display_name(get_item_id(item_name)))
                    add_log(title = self.pack_message("Drop Item."), content = "Don't have any %s to drop." % get_item_display_name(get_item_id(item_name)), print = False)
                    return False

                self.bot.chat("I dropped %d %s." % (dropped, get_item_display_name(get_item_id(item_name))))
                add_log(title = self.pack_message("Drop Item."), content = "Dropped %d %s." % (dropped, get_item_display_name(get_item_id(item_name))), print = False)
                return True 
            
            def search_block(block_name, range = 64, min_distance = 2) :
                range = min(512, range)
                block = get_nearest_block(block_name, range)
                if block is None :
                    self.bot.chat("I can't find any %s in %s blocks." % (get_block_display_name(get_block_id(block_name)), math.floor(range)))
                    add_log(title = self.pack_message("Search Block."), content = "Can't find any %s in %s blocks." % (get_block_display_name(get_block_id(block_name)), range), print = False)
                    return False
                self.bot.chat("Found %s at %s. I am going there." % (get_block_display_name(get_block_id(block_name)), block.position))
                add_log(title = self.pack_message("Search Block."), content = "Found %s at %s." % (get_block_display_name(get_block_id(block_name)), block.position), print = False)
                go_to_position(block.position.x, block.position.y, block.position.z, min_distance)
                return True

            def get_nearest_entity_where(predicate, max_distance) : 
                entity = self.bot.nearestEntity(lambda entity : predicate(entity) and self.bot.entity.position.distanceTo(entity.position) < max_distance)
                return entity
            
            def get_nearest_entities(max_distance = 32, count = 16) : 
                entities = []
                for entity_id in self.bot.entities :
                    entity = self.bot.entities[entity_id]
                    try : 
                        if entity is not None and entity.position is not None and self.bot.entity is not None :
                            distance = entity.position.distanceTo(self.bot.entity.position)
                            if distance > max_distance: continue
                            entities.append({"entity" : entity, "distance" : distance})
                        else :
                            add_log(title = self.pack_message("Get Nearby Entities."), content = "Get invalid entities.", print = False)
                    except Exception as e : 
                        add_log(title = self.pack_message("Get Nearby Entities."), content = "Exception: %s" % e, print = False)
                    if len(entities) >= count : 
                        break
                entities = sorted(entities, key = functools.cmp_to_key(lambda a, b : a["distance"] - b["distance"]))
                return [entity["entity"] for entity in entities]

            def get_nearest_freespace(size = 1, distance = 8) :
                empty_pos = self.bot.findBlocks({
                    "matching" : lambda block : block is not None and block.name == "air",
                    "maxDistance" : distance,
                    "count" : 1000,
                })
                for i in range(len(empty_pos)) :
                    empty = True
                    for x in range(size) :
                        for z in range(size) : 
                            top = self.bot.blockAt(empty_pos[i].offset(x, 0, z))
                            bottom = self.bot.blockAt(empty_pos[i].offset(x, -1, z))
                            if top is None or top.name != "air" or bottom is None or bottom.drops.length < 1 or not bottom.diggable :
                                empty = False
                                break
                        if empty is None :
                            break
                    if empty == True :
                        return empty_pos[i]
                return None

            def search_entity(entity_name, range = 64, min_distance = 2) :
                entity = get_nearest_entity_where(lambda entity : entity.name == entity_name, range)
                if entity is None :
                    self.bot.chat("I can't find any %s in %s blocks." % (get_entity_display_name(get_entity_id(entity_name)), math.floor(range)))
                    add_log(title = self.pack_message("Search Entity."), content = "Can't find any %s in %s blocks." % (get_entity_display_name(get_entity_id(entity_name)), range), print = False)
                    return False
                distance = self.bot.entity.position.distanceTo(entity.position)
                self.bot.chat("Found %s %s blocks away. I am going there." % (get_entity_display_name(get_entity_id(entity_name)), math.floor(distance)))
                add_log(title = self.pack_message("Search Entity."), content = "Found %s at %s." % (get_entity_display_name(get_entity_id(entity_name)), entity.position), print = False)
                go_to_position(entity.position.x, entity.position.y, entity.position.z, min_distance)
                return True
            
            @Action()
            def fight(self, entity_name, kill = True) :
                if self.bot.modes is not None : 
                    self.bot.modes.pause('cowardice')
                    if entity_name in ["drowned", "cod", "salmon", "tropical_fish", "squid"] :
                        self.bot.modes.pause('self_preservation') 
                entities = list(filter(lambda entity: entity.name == entity_name, get_nearest_entities(32)))
                entity = entities[0] if len(entities) > 0 else None 
                if entity is not None :
                    return attack_entity(entity, kill)
                else :
                    self.bot.chat("I can't find any %s to attack." % get_entity_display_name(get_entity_id(entity_name)))
                    add_log(title = self.pack_message("Fight."), content = "Could not find any %s to attack." % get_entity_display_name(get_entity_id(entity_name)), print = False)
                    return False
            
            def attack_entity(entity, kill = True) : 
                pos = entity.position
                equip_highest_attack()
                if kill == False :
                    if self.bot.entity.position.distanceTo(pos) > 5 :
                        go_to_position(pos.x, pos.y, pos.z)
                    self.bot.attack(entity)
                    return True
                else :
                    self.bot.pvp.attack(entity)
                    while entity in get_nearest_entities(24) :
                        time.sleep(1.0)
                        if self.bot.interrupt_code :
                            self.bot.pvp.stop()
                            return False
                    self.bot.chat("I killed %s." % entity.name)
                    add_log(title = self.pack_message("Attack Entity."), content = "Killed %s." % entity.name, print = False)
                    pickup_nearby_items()
                    return True

            def equip_highest_attack() :
                weapons = list(filter(lambda item : "sword" in item.name or "axe" in item.name, self.bot.inventory.items()))
                if len(weapons) < 1 : 
                    weapons = list(filter(lambda item : "pickaxe" in item.name or "shovel" in item.name, self.bot.inventory.items()))
                if len(weapons) < 1 : 
                    return
                weapons = sorted(weapons, key = functools.cmp_to_key(lambda a, b : a.attackDamage < b.attackDamage))
                weapon = weapons[0]
                if weapon is not None : 
                    self.bot.equip(weapon, "hand")
            
            @Action()
            def craft(self, item_name, num = 1) :
                placed_table = False
                if len(get_item_crafting_recipes(item_name)) < 1 : 
                    self.bot.chat("I don't have crafting recipe for %s." % item_name)
                    add_log(title = self.pack_message("Craft."), content = "There is no crafting recipe for %s." % item_name, print = False)
                    return False

                recipes = self.bot.recipesFor(get_item_id(item_name), None, 1, None) 
                crafting_table = None
                crafting_table_range = 32

                if recipes is None or len(recipes) < 1 : 
                    recipes = self.bot.recipesFor(get_item_id(item_name), None, 1, True)
                    if recipes is None or len(recipes) < 1 : 
                        self.bot.chat("I don't have enough resources to craft %s." % item_name)
                        add_log(title = self.pack_message("Craft."), content = "There is not enough resources for crafting %s." % item_name, print = False)
                        return False

                    crafting_table = get_nearest_block('crafting_table', crafting_table_range)
                    if crafting_table is None : 
                        has_table = get_inventory_counts()["crafting_table"] > 0
                        if has_table == True :
                            pos = get_nearest_freespace(1, 6)
                            if pos is not None :
                                place_block("crafting_table", pos.x, pos.y, pos.z)
                                crafting_table = get_nearest_block("crafting_table", crafting_table_range)
                                if crafting_table is not None :
                                    recipes = self.bot.recipesFor(get_item_id(item_name), None, 1, crafting_table)
                                    placed_table = True
                            self.bot.chat("There is no space to place the crafting table.")
                            add_log(title = self.pack_message("Craft."), content = "No space to place the crafting table.", print = False)
                            return False
                        else :
                            self.bot.chat("I don't have any crafting table.")
                            add_log(title = self.pack_message("Craft."), content = "Have none of crafting tables.", print = False)
                            return False
                    else :
                        recipes = self.bot.recipesFor(get_item_id(item_name), None, 1, crafting_table)

                if recipes is None or len(recipes) < 1 :
                    return False 
                
                if crafting_table and self.bot.entity.position.distanceTo(crafting_table.position) > 4 : 
                    go_to_nearest_block('crafting_table', 4, crafting_table_range)

                recipe = recipes[0]
                inventory = get_inventory_counts()
                required_ingredients = ingredients_from_prismarine_recipe(recipe)
                craft_limit = calculate_limiting_resource(inventory, required_ingredients)
                
                self.bot.craft(recipe, min(craft_limit["num"], num), crafting_table)
                if craft_limit["num"] < num : 
                    self.bot.chat("I don't have enough %s to craft %s %s, crafted %s." % (craft_limit["limiting_resource"], num, item_name, craft_limit["num"]))
                    add_log(title = self.pack_message("Craft."), content = "Don't have enough %s to craft %s %s, crafted %s." % (craft_limit["limiting_resource"], num, item_name, craft_limit["num"]), print = False)
                else :
                    self.bot.chat("I have crafted %s %s." % (num, item_name))
                    add_log(title = self.pack_message("Craft."), content = "I have crafted %s %s." % (num, item_name), print = False)

                if placed_table :
                    collect_blocks('crafting_table', 1)

                self.bot.armorManager.equipAll(); 
                return True
            
            def get_inventory_stacks() :
                inventory = []
                for item in self.bot.inventory.items() :
                    if item is not None : 
                        inventory.append(item)
                return inventory

            def get_inventory_counts() :
                inventory = {}
                for item in self.bot.inventory.items() :
                    if item is not None :
                        if item.name not in inventory.keys() :
                            inventory[item.name] = 0
                        inventory[item.name] += item.count
                return inventory

            def get_hotbar_counts() :
                hotbar = {}
                for item in self.bot.inventory.slots :
                    if item is not None :
                        if item.name not in hotbar.keys() :
                            hotbar[item.name] = 0
                        hotbar[item.name] += item.count
                return hotbar

            def get_item_counts() :
                inventory = get_inventory_counts()
                hotbar = get_hotbar_counts()
                inventory.update(hotbar)
                return inventory

    def stop(self) :
        self.act_running, self.plan_running = False, False
        add_log(title = self.pack_message("Stop."), label = "success")

    def push_msg(self, msg) : 
        self.messages.append(msg)

    def push_action(self, action) : 
        self.actions.append(action)

    def build_plan_prompt(self, status, messages) :
        prompt = '''
You are a useful AI assistant in planning the actions for Minecraft bot. Given the status of the agent, you should evaluate the target of the agent and the current situations, and generate following contents: 
1. If applicable, update the status summary according to the current status and latest messages, the summary should include the key information that is necessary or useful to describe the overall situation of the agent, especially the underlying goal for action and the performed actions, and outcomes;
2. If applicable, indicate the next action (selected from the 'Available Actions') for the agent to execute, and provide the values for the parameters following the detailed description in 'Available Actions' of the selected action;
3. If an action is necessary, you should prefer the actions other than 'chat' to make sure you finish the task before sending messages to the others. In other words, 'chat' is only required if it is the last thing or the only thing you can do to respond to the others.  

## Agent's Status
%s

## Agent's Personality
%s

## Latest Messages
%s

## Available Actions 
%s

## Output Format
The result should be formatted in **JSON** dictionary and enclosed in **triple backticks (` ``` ` )**  without labels like 'json', 'css', or 'data'.
- **Do not** generate redundant content other than the result in JSON format.
- **Do not** use triple backticks anywhere else in your answer.
- The JSON must include the following keys and values accordingly :
    - 'status' : An updated version of the status summary of the agent. If no update is needed, set value to null.
    - 'action' : An JSON dictionary to specify the next action for the agent to execute. If no action is needed, set value to null. Otherwise, the dicionary should includes following keys and values : 
        - 'name' : a JSON string of the action name which is listed in the 'Available Actions'
        - 'params' : a JSON dictionary where keys are the names of the parameters as described in the 'Available Actions' for the selecte action; and the associated value should follow the 'type' and 'domain' constrains in the description. 

Following is an example of the output: 
```
{
    "status" : "Stand in a place near the beach, and now is asked to go to a position near player 'player_1'.",  
    "action" : {
        "name" : "go_to_player", 
        "params" : {
            "player_name" : "player_1",
            "closeness" : 1
        }
    }  
}
```
''' % (
    status, 
    self.configs.get("personality", "A smart Minecraft agent."), 
    messages, 
    self.mcp_manager.get_actions_info(self.configs.get("actions", None)), 
)
        return prompt
    
    def update_status(self, data) : 
        status = data.get("status", None)
        if isinstance(status, str) : 
            self.status = status 
            add_log(title = self.pack_message("Update status."), content = self.status, label = "execute")
        else :
            add_log(title = self.pack_message("Keep status unchanged."), label = "execute")
        
    def pack_message(self, message) : 
        return "[Agent \'%s\'] %s" % (self.configs["username"], message)

    