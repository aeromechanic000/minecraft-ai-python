
import math, time, functools, threading

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
            "execute" : "go_to_player", 
        },
        {
            "name" : "move_away", 
            "desc": "Move away from the current location in any direction by a given distance.",
            "params": {
                "distance": {"type" : "float", "desc" : "The distance to move away.", "domain": [20, math.inf]},
            },
            "execute" : "move_away", 
        },
        {
            "name" : "collect_blocks",
            "desc" : "Collect the nearest blocks of a given type.",
            "params" : {
                "block_type" : {"type": "BlockName", "desc": "The block type to collect.", "domain" : get_collect_block_types()},
                "num" : {"type": "int", "desc" : "The number of blocks to collect.", "domain" : [1, 16]}
            },
            "execute" : "collect_blocks", 
        },
        {
            "name" : "equip",
            "desc" : "Equip the given item.",
            "params" : {
                "item_name": { "type" : "ItemName", "desc" : "The name of the item to equip.", "domain" : get_equip_item_names()}, 
            },
            "execute" : "equip",
        },
    ]
    actions = []
    for action in availabel_actions : 
        if not isinstance(action_names, list) or action["name"] in action_names :
            actions.append(action) 
    return actions

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

        self.plan_thread, self.act_thread = None, None
        self.status_summary, self.recent_actions = "", [] 
        self.messages, self.actions = [], []
        self.plan_running, self.act_running = False, False

        @On(self.bot, 'resourcePack')
        def handle(*args) :
            self.bot.acceptResourcePack()

        @On(self.bot, 'spawn')
        def handle(*args) :
            add_log(title = self.pack_message("I spawned."), label = "success")
            self.movements = pathfinder.Movements(self.bot)
            viewer_port = self.configs.get("viewer_port", None)
            viewer_first_person = self.configs.get("viewer_first_person", False)
            viewer_distance = self.configs.get("viewer_distance", 6)
            if viewer_port : 
                require('canvas')
                viewer = require('prismarine-viewer')
                viewer["mineflayer"](self.bot, {"port": viewer_port, "firstPerson" : viewer_first_person, "viewDistance" : viewer_distance})
            self.plan_thread = threading.Thread(target = self.plan)
            self.plan_thread.start()
            self.act_thread = threading.Thread(target = self.act)
            self.act_thread.start()

            @On(self.bot, 'chat')
            def handleMsg(this, sender, message, *args):
                if sender and (sender != self.bot.username):
                    if "@%s" % self.bot.username in message or "@all" in message : 
                        self.push_msg({"sender" : sender, "message" : message, "type" : "whisper"})
                    else : 
                        self.push_msg({"sender" : sender, "message" : message, "type" : "update"})

        @On(self.bot, "end")
        def handle(*args):
            self.bot.quit()
            add_log(title = self.pack_message("Bot end."))
            self.stop()
            if all([agent.plan_running == False for agent in self.mcp_manager.agents.values()]) : 
                self.mcp_manager.stop()
        
    def push_msg(self, msg) : 
        self.messages.append(msg)

    def push_action(self, action) : 
        self.actions.append(action)

    def plan(self) : 
        self.plan_running = True
        while self.plan_running : 
            if len(self.messages) > 0 : 
                if any([message["type"] == "whisper" for message in self.messages]) :
                    messages = self.messages.copy()
                    self.messages.clear()
                    add_log(title = self.pack_message("Process messages."), content = str(messages), label = "execute")
                    prompt = self.build_plan_prompt(messages)
                    llm_result = call_llm_api(self.configs["provider"], self.configs["model"], prompt)
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

    def act(self) : 
        self.act_running = True
        actions = []
        while self.act_running : 
            if len(self.actions) > 0 : 
                actions += self.actions.copy()
                self.actions.clear()
                add_log(title = self.pack_message("Got actions."), content = str(actions), label = "execute")
            if len(actions) > 0 : 
                action = actions.pop(0) 
                add_log(title = self.pack_message("Perfom action."), content = str(action), label = "execute")
                try : 
                    execute = getattr(self, action["execute"]) 
                    execute(**action["params"])
                except Exception as e : 
                    add_log(title = self.pack_message("Exception in performing action."), label = "error")
                    add_log(title = self.pack_message("Exception."), content = str(e), label = "error", print = False)

    def build_plan_prompt(self, messages) :
        latest_messages = ""
        for message in messages : 
            latest_messages += "'%s' said: %s\n" % (message["sender"], message["message"])
        prompt = '''
You are a useful AI assistant in planning the actions for Minecraft bot. Given the status of the agent, you should evaluate the target of the agent and the current situations, and generate following contents: 
1. If applicable, update the status summary according to the current status and latest messages;
2. If applicable, indicate the next action (selected from the 'Available Actions') for the agent to execute, and provide the values for the parameters following the detailed description in 'Available Actions' of the selected action. 

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
''' % (self.get_status(), self.configs.get("personality", "A smart Minecraft agent."), latest_messages, self.mcp_manager.get_actions_info(self.configs.get("actions", None)))
        return prompt
    
    def get_status(self) : 
        status = "- Agent's Name: %s\n- Status Summary: %s " % (self.bot.username, self.status_summary)
        if len(self.recent_actions) > 0 : 
            recent_actions_desc = self.mcp_manager.get_actions_desc(self.recent_actions)
            if len(recent_actions_desc.strip()) > 0 : 
                status += "\n- Recent Actions: \n%s" % recent_actions_desc
        return status
    
    def update_status(self, data) : 
        status = data.get("status", None)
        if isinstance(status, str) : 
            self.status = status 
            add_log(title = self.pack_message("Update status."), content = self.status, label = "execute")
        else :
            add_log(title = self.pack_message("Keep status unchanged."), label = "execute")
        
    def pack_message(self, message) : 
        return "[Agent \'%s\'] %s" % (self.configs["username"], message)

    def stop(self) :
        if self.act_thread is not None : 
            self.act_running = False
            self.act_thread.join()
        if self.plan_thread is not None : 
            self.plan_running = False
            self.plan_thread.join()
        add_log(title = self.pack_message("Stop."), label = "success")
    
    def go_to_position(self, x, y, z, closeness) : 
        self.bot.pathfinder.setMovements(self.movements)
        self.bot.pathfinder.setGoal(pathfinder.goals.GoalNear(x, y, z, closeness)) 

    def go_to_player(self, player_name, closeness = 1) : 
        for t in range(self.mcp_manager.configs.get("action_retry_times", 1)) :
            add_log(title = self.pack_message("Try for the %d-th time." % (t + 1)))
            player = self.bot.players[player_name]
            if player is not None and player.entity is not None :  
                pos = player.entity.position
                self.go_to_position(pos.x, pos.y, pos.z, closeness)
                self.recent_actions.append("go_to_player")
                self.bot.chat("I am here.")
                break
            else :
                add_log(title = self.pack_message("Failed to get player's position."), label = "warning") 

    def move_away(self, distance) : 
        for t in range(self.mcp_manager.configs.get("action_retry_times", 1)) :
            add_log(title = self.pack_message("Try for the %d-th time." % (t + 1)))
            if self.bot.entity is not None :
                pos = self.bot.entity.position
                vector = get_random_vector(distance)
                self.go_to_position(pos.x + vector[0], pos.y, pos.z + vector[1], 0) 
                self.recent_actions.append("move_away")
                self.bot.chat("I moved to a new location.")
                break
            else : 
                add_log(title = self.pack_message("Failed to get bot's position."), label = "warning")

    def collect_blocks(self, block_type, num, exclude = None) : 
        for t in range(self.mcp_manager.configs.get("action_retry_times", 1)) :
            block_types = [block_type]
            if block_type in ["coal", "diamond", "emerald", "iron", "gold", "lapis_lazuli", "redstone", ] : 
                block_types.append("%s_ore" % block_type)
            if block_type.endswith("ore") :
                block_types.append("deepslate_%s" % block_type)
            if block_type == "dirt" : 
                block_types.append("grass_block")
            collected = 0
            for i in range(num) : 
                blocks = self.get_nearest_blocks(block_types = block_types, distance = 32, count = 16)
                if exclude is not None and isinstance(exclude, list) : 
                    blocks = list(filter(lambda block : all([block.position.x != position.x or block.position.y != position.y or block.position.z != position.z for position in exclude]), blocks))
                movements = pathfinder.Movements(self.bot)
                movements.dontMineUnderFallingBlock = False
                blocks = list(filter(lambda block: movements.safeToBreak(block), blocks))
                if len(blocks) < 1 : 
                    if collected < 1 :  
                        self.bot.chat("I don't find any %s nearby to collect." % get_block_display_name(get_block_id(block_type)))
                        add_log(title = self.pack_message("Collect Blocks"), content = "Don't find any %s nearby." % get_block_display_name(get_block_id(block_type)), print = False)
                    else :
                        self.bot.chat("Can't find more %s nearby to collect." % get_block_display_name(get_block_id(block_type)))
                        add_log(title = self.pack_message("Collect Blocks"), content = "Can't find more %s nearby." % get_block_display_name(get_block_id(block_type)), print = False)
                    break

                block = blocks[0]
                self.bot.tool.equipForBlock(block)
                item_id = self.bot.heldItem if self.bot.heldItem is not None else None 
                if not block.canHarvest(item_id) : 
                    self.bot.chat("I dont't have right tools to harvest %s." % block.displayName)
                    break

                try :
                    if must_collect_manually(block_type) :
                        add_log(title = self.pack_message("Collect Blocks"), content = "%s must be collected manually." % block.displayName, print = False)
                        self.go_to_position(block.position.x, block.position.y, block.position.z, 2)
                        self.bot.dig(block)
                        self.pickup_nearby_items()
                    else :
                        self.bot.collectBlock.collect(block)
                    collected += 1
                    self.auto_light()
                except Exception as e :
                    add_log(title = self.pack_message("Collect Blocks"), content = "Exception in collecting %s: %s" % (block.displayName, e), label = "warning")

                if self.bot.interrupt_code :
                    break;  

            self.bot.chat("I have collected %d %s." % (collected, get_block_display_name(get_block_id(block_type))))
        return collected > 0
    
    def get_nearest_blocks(self, block_types = None, distance = 32, count = 16) :
        block_ids = []
        if block_types is None or not isinstance(block_types, list) : 
            block_ids = get_all_block_ids(['air'])
        else : 
            for block_type in block_types :
                block_ids.append(get_block_id(block_type))
        positions = self.bot.findBlocks({"matching" : block_ids, "maxDistance" : distance, count : count})
        blocks = []
        for i in range(positions.length) : 
            block = self.bot.blockAt(positions[i])
            dist = positions[i].distanceTo(self.bot.entity.position)
            blocks.append({"block" : block, "distance" : dist})
        blocks = sorted(blocks, key = functools.cmp_to_key(lambda a, b : a["distance"] - b["distance"]))
        return [block["block"] for block in blocks]
 
    def get_nearest_block(self, block_type, distance = 16) :
        blocks = self.get_nearest_blocks(block_types = [block_type], distance = distance, count = 1)
        if len(blocks) > 0 :
            return blocks[0]
        return None 
   
    def get_nearest_item(self, distance = 1) : 
        return self.bot.nearestEntity(lambda entity : entity.name == 'item' and self.bot.entity.position.distanceTo(entity.position) < distance)

    def pickup_nearby_items(self) : 
        nearest_item = self.get_nearest_item(distance = 8)
        prev_item = nearest_item
        picked_up = 0
        while nearest_item :
            self.bot.pathfinder.setMovements(pathfinder.Movements(self.bot))
            self.bot.pathfinder.goto(pathfinder.goals.GoalFollow(nearest_item, 0.8), True)
            time.sleep(0.2)
            prev_item = nearest_item
            nearest_item = self.get_nearest_item()
            if prev_item == nearest_item :
                break
            picked_up += 1
        self.bot.chat("I picked up %d items" % picked_up)
        return True

    def should_place_torch(self) : 
        if self.bot.modes is not None and self.bot.modes.isOn('torch_placing') or self.bot.interrupt_code :
            return False
        pos = self.bot.entity.position
        nearest_torch = self.get_nearest_block('torch', 6)
        if nearest_torch is None :
            nearest_torch = self.get_nearest_block('wall_torch', 6)
        if nearest_torch is None : 
            block = self.bot.blockAt(pos)
            if block is None :
                return False
            else :
                has_torch = any([item.name == "torch" for item in self.bot.inventory.items()])
                return has_torch and block.name == 'air'
        return False

    def auto_light(self) : 
        if self.should_place_torch() :
            try : 
                pos = self.bot.entity.position
                self.place_block('torch', pos.x, pos.y, pos.z, 'bottom', True)
            except Exception as e : 
                return False
        return False
    
    def break_block_at(self, x, y, z) : 
        if x is None or y is None or z is None : 
            return False

        block = self.bot.blockAt([x, y, z])
        if block.name != "air" and block.name != "water" and block.name != "lava" :
            if self.bot.modes.isOn("cheat") :
                msg = "/setblock %d %d %d air" % (math.floor(x), math.floor(y), math.floor(z))
                self.bot.chat(msg)
                add_log(title = self.package_message("Break block."), content = "Used /setblock to break block at ($d, %d, %d)." % (math.floor(x), math.floor(y), math.floor(z)), print = False)
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

    def place_block(self, block_type, x, y, z, place_on = 'bottom', dont_cheat = False) :
        if get_block_id(block_type) and block_type != 'air' :
            add_log(title = self.pack_message("Place block."), content = "Invalid blocktype to place: %s" % block_type, print = False)
            return False

        target_dest = [math.floor(x), math.floor(y), math.floor(z)]
        if block_type == 'air' :
            add_log(title = self.pack_message("Place block."), content = "Placing air (removing block) at: %s" % target_dest, print = False)
            self.break_block_at(x, y, z)

        if self.bot.modes.isOn('cheat') and not dont_cheat :
            if self.bot.restrict_to_inventory :
                block = None 
                for item in self.bot.inventory.items() : 
                    if item.name == block_type : 
                        block = item
                if block is None :
                    add_log(title = self.pack_message("Place block."), content = "Cannot place %s. Restricted to the current inventory." % block_type, label = "warning")
                    return False

            face = "east"
            if place_on == "north" : 
                face = "south"
            elif place_on == "south" :
                face = "north"
            elif place_on == "east" : 
                face = "west"

            if "torch" in block_type and place_on != "bottom" :
                block_type = block_type.replace('torch', 'wall_torch')
                if place_on != "side" and place_on != "top" :
                    block_type += "[facing=%s]" % face

            if "botton" in block_type or block_type == "lever" :
                if place_on == "top" :
                    block_type += "[face=ceiling]"
                elif place_on == "bottom" :
                    block_type += "[face=floor]"
                else :
                    blockType += "[facing=%s]" % face

            if block_type == "ladder" or block_type == "repeater" or block_type == "comparator" :
                block_type += "[facing=%s]" % face

            if "stairs" in block_type :
                block_type += "[facing=%s]" % face

            msg = "/setblock %d %d %d %s" % (math.floor(x), math.floor(y), math.floor(z), block_type)
            self.bot.chat(msg)

            if "door" in block_type :
                msg = "/setblock %d %d %d %s [half=upper]" % (math.floor(x), math.floor(y + 1), math.floor(z), block_type)
                self.bot.chat(msg)

            if "bed" in block_type :
                msg = "/setblock %d %d %d %s [part=head]" % (math.floor(x), math.floor(y), math.floor(z - 1), block_type)
                self.bot.chat(msg)

            add_log(title = self.package_message("Place block."), content = "Used /setblock to place block %s at %s." % (block_type, target_dest), print = False)
            return True
        
        item_name = block_type
        if item_name == "redstone_wire" : 
            item_name = "redstone"

        block = None 
        for item in self.bot.inventory.items() : 
            if item.name == item_name : 
                block = None
                break

        if block is None and self.bot.game.gameMode == 'creative' and not self.bot.restrict_to_inventory :
            self.bot.creative.setInventorySlot(36, mc.makeItem(item_name, 1)) 
            for item in self.bot.inventory.items() : 
                if item.name == item_name : 
                    block = None
                    break

        if block is None :
            add_log(title = self.package_message("Place block."), content = "Have no %s to place." % block_type, print = False)
            return False

        target_block = self.bot.blockAt(target_dest)
        if target_block.name == block_type :
            add_log(title = self.package_message("Place block."), content = "%s already at %s." % (block_type, target_block.position), print = False)
            return False

        empty_blocks = ["air", "water", "lava", "grass", "short_grass", "tall_grass", "snow", "dead_bush", "fern"]
        if target_block.name not in empty_blocks :
            add_log(title = self.package_message("Place block."), content = "%s in the way at %s." % (block_type, target_block.position), print = False)
            removed = self.break_block_at(x, y, z)
            if removed == False :
                add_log(title = self.package_message("Place block."), content = "Cannot place %s at %s (block in the way)." % (block_type, target_block.position), print = False)
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
            add_log(title = self.package_message("Place block."), content = "Unknown place_on value: %s. Defaulting to bottom." % place_on, print = False)
        
        for d in dir_map.values() : 
            if d not in dirs : 
                dirs.append(d)

        for d in dirs :
            block = self.bot.blockAt([target_dest[0] + d[0], target_dest[1] + d[1], target_dest[2] + d[2]])
            if block.name not in empty_blocks :
                build_off_block = block
                face_vec = [-d[0], -d[1], -d[2]] 
                break

        if build_off_block is None : 
            add_log(title = self.package_message("Place block."), content = "Cannot place %s at %s (nothing to place on)." % (block_type, target_block.position), print = False)
            return False

        pos = self.bot.entity.position
        pos_above = pos.plus([0, 1, 0])
        dont_move_for = [
            'torch', 'redstone_torch', 'redstone_wire', 
            'lever', 'button', 'rail', 'detector_rail', 'powered_rail', 
            'activator_rail', 'tripwire_hook', 'tripwire', 'water_bucket',
        ]

        if block_type not in dont_move_for and (pos.distanceTo(target_block.position) < 1 or pos_above.distanceTo(target_block.position) < 1) :
            goal = pathfinder.goals.GoalNear(target_block.position.x, target_block.position.y, target_block.position.z, 2)
            inverted_goal = pathfinder.goals.GoalInvert(goal)
            self.bot.pathfinder.setMovements(pathfinder.Movements(self.bot))
            self.bot.pathfinder.goto(inverted_goal)

        if self.bot.entity.position.distanceTo(target_block.position) > 4.5 :
            pos = target_block.position
            movements = pathfinder.Movements(self.bot)
            self.bot.pathfinder.setMovements(movements)
            self.bot.pathfinder.goto(pathfinder.goals.GoalNear(pos.x, pos.y, pos.z, 4))
        
        self.bot.equip(block, 'hand')
        self.bot.lookAt(build_off_block.position)

        try :
            self.bot.placeBlock(build_off_block, face_vec)
            add_log(title = self.package_message("Place block."), content = "Placed %s at %s." % (block_type, target_dest), print = False)
            time.sleep(0.2)
            return True
        except Exception as e :
            add_log(title = self.package_message("Place block."), content = "Failed to place %s at %s." % (block_type, target_dest), print = False)
            return False

    def equip(self, item_name) :
        item = None 
        for slot in self.bot.inventory.slots : 
            if slot is not None and slot.name == item_name : 
                item = slot

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
                collect_block_types = get_collect_block_types()
                if valid_value not in collect_block_types : 
                    top_k_items = get_top_k_similar_items(valid_value, collect_block_types, k = 1, threshold = max(2, len(valid_value) / 2))
                    valid_value = top_k_items[0] if len(top_k_items) > 0 else None
            elif _type == "ItemName" : 
                valid_value = str(value)
                collect_item_names = get_equip_item_names()
                if valid_value not in collect_item_names : 
                    top_k_items = get_top_k_similar_items(valid_value, collect_item_names, k = 1, threshold = max(2, len(valid_value) / 2))
                    valid_value = top_k_items[0] if len(top_k_items) > 0 else None
        except : 
            valid_value = None
    return valid_value