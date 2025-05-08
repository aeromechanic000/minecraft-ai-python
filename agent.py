
import math, time, functools 
from javascript import require, On 

from memory import *
from actions import *

class Agent(object) : 
    def __init__(self, configs, manager) :
        add_log(title = "Agent Created.", content = "Agent has been created with configs: %s" % configs, label = "header")
        self.configs, self.manager = configs, manager
        self.status_summary = ""
        self.working_process = None
        bot_configs = self.configs.copy()
        bot_configs.update({
            "host" : self.manager.configs["host"],
            "port" : self.manager.configs["port"],
            "version" : self.manager.configs["minecraft_version"],
        })
        self.memory = Memory(self)
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
            add_log(title = self.pack_message("I spawned."), label = "success")
            self.bot.chat("Hi. I am %s." % self.bot.username)
            viewer_port = self.configs.get("viewer_port", None)
            viewer_first_person = self.configs.get("viewer_first_person", False)
            viewer_distance = self.configs.get("viewer_distance", 6)
            if viewer_port is not None : 
                require('canvas')
                viewer = require('prismarine-viewer')
                viewer["mineflayer"](self.bot, {"port": viewer_port, "firstPerson" : viewer_first_person, "viewDistance" : viewer_distance})

            @On(self.bot, "end")
            def handle_end(*args):
                self.bot.quit()
                add_log(title = self.pack_message("Bot end."), label = "success")
                self.stop()
                self.manager.stop()

            @On(self.bot, 'chat')
            def handle_msg(this, username, message, *args):
                message = message.strip()
                ignore_messages = [
                    "/",
                    "Set own game mode to",
                    "Set the time to",
                    "Set the difficulty to",
                    "Teleported ",
                    "Set the weather to",
                    "Gamerule "
                ]
                record = {}

                if username is not None and all([not message.startswith(msg) for msg in ignore_messages + self.manager.configs.get("ignore_messages", [])]) : 
                    if username == self.bot.username :
                        if message.strip().startswith("[[Self-Driven Thinking]]") :
                            record = {"type" : "message", "data" : {"sender" : username, "content" : message.strip()[len("[[Self-Driven Thinking]]"):]}}
                        else : 
                            self.memory.update({"type" : "status", "data" : {"status" : message}})
                    elif sizeof(self.bot.players) == 2 or "@%s" % self.bot.username in message or "@all" in message or "@All" in message or "@ALL" in message : 
                        record = {"type" : "message", "data" : {"sender" : username, "content" : message}}
                
                if len(record) < 1 : 
                    add_log(title = self.pack_message("Ignore message."), content = "sender: %s; message: %s" % (username, message), label = "warning")
                    return 

                add_log(title = self.pack_message("Get message."), content = "sender: %s; message: %s" % (username, message), label = "action")
                self.memory.update({"type" : "message", "data" : {"sender" : username, "content" : message}})
                work()
                    
            def work() : 
                current_working_process = get_random_label()
                self.working_process = current_working_process 
                instruction = self.memory.get_instruction()
                self.memory.reset_instruction()
                while instruction is not None and len(instruction.strip()) > 0 :
                    add_log(title = self.pack_message("Get instruction"), content = instruction, label = "action")
                    prompt = self.build_prompt(instruction) 
                    llm_result = call_llm_api(self.configs["provider"], self.configs["model"], prompt, max_tokens = self.configs.get("max_tokens", 4096))
                    add_log(title = self.pack_message("Get LLM response"), content = str(llm_result), label = "action")
                    if llm_result["status"] > 0 :
                        add_log(title = self.pack_message("Error in calling LLM: %s" % llm_result["error"]), label = "warning")
                    else :
                        _, data = split_content_and_json(llm_result["message"])
                        add_log(title = self.pack_message("Got data."), content = str(data), label = "action")
                        status_summary = data.get("status", None)
                        if status_summary is not None : 
                            self.status_summary = status_summary
                        action = self.manager.extract_action(data)
                        if action is not None : 
                            add_log(title = self.pack_message("Perfom action."), content = str(action), label = "action")
                            action["params"]["agent"] = self
                            run_action(action["perform"], action["params"])
                    instruction = self.memory.get_instruction()
                    self.memory.reset_instruction()
                    if instruction is not None and self.working_process != current_working_process :
                        break
                self.working_process = None

            def run_action(perform, params) : 
                try : 
                    result = perform(**params)
                except Exception as e : 
                    add_log(title = self.pack_message("Exception in performing action."), content = "Exception: %s" % e, label = "error")

    def build_prompt(self, instruction) :     
        return '''
You are an AI assistant helping to plan the next action for a Minecraft bot. Based on the current status, memory, instruction, and the list of available actions, your task is to determine what the bot should do next. 

You must output: 
1. An updated status summary, if any change is needed. This should briefly describe the bot's current situation, goals, recent actions, and important outcomes that help track progress. 
2. The next action for the bot to execute. Choose from the list of 'Available Actions', and provide appropriate parameter values based on the definitions.

Important Guidelines:
1. Only update the status if new context or progress has occurred. Otherwise, set it to null.
2. Only generate an action if one is needed. Otherwise, set action to null.
3. When choosing an action, prioritize non-chat actions to make sure the task progresses. Only use chat if it is the only meaningful or required response.

The selected action's parameters must follow the types and domains described under 'Available Actions'.

## Current Status
%s

## Memory
%s

## Instruction
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
''' % (self.get_status_info(), self.memory.get(), instruction, self.manager.get_actions_info())

    def get_mc_time(self) : 
        hrs, mins = 0, 0
        t = self.bot.time.timeOfDay 
        hrs = math.floor(t // 10000)
        mins = math.floor(min(59, (t % 10000) // (10000 / 60)))
        return [self.bot.time.day, hrs, mins]

    def get_status_info(self) : 
        status = "- Agent's Name: %s\n" % self.bot.username
        if len(self.status_summary.strip()) > 0 :
            status += "- Status Summary: %s\n" % self.status_summary
        status += "\n- Agent's Status of Health (from 0 to 20, where 0 for death and 20 for completely healthy): %s" % self.bot.health 
        status += "\n- Agent's Degree Of Hungry (from 0 to 20, where 0 for hungry and 20 for full): %s" % self.bot.food
        pos = get_entity_position(self.bot.entity)
        if pos is not None : 
            status += "\n- Agent's Position: x: %s, y: %s, z: %s" % (math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
        add_log(title = self.pack_message("Get primary status."), content = status, print = False)
        items_in_inventory, items_info = get_item_counts(self), "" 
        for key, value in items_in_inventory.items() : 
            items_info += "%s %s;" % (value, key)
        if len(items_info.strip()) > 0 : 
            add_log(title = self.pack_message("Get inventory items info."), content = items_info)
            status += "\n- Items in Inventory: %s" % items_info
        try : 
            blocks, blocks_info = get_nearest_blocks(self, block_names = get_block_names(), max_distance = 16, count = 8), ""
            for block in blocks : 
                pos = block.position
                if pos is not None :
                    blocks_info += "%s (at x: %s, y: %s, z: %s);" % (block.name,  math.floor(pos.x), math.floor(pos.y), math.floor(pos.z)) 
            if len(blocks_info.strip()) > 0 : 
                add_log(title = self.pack_message("Get nearby blocks info."), content = blocks_info)
                status += "\n- Blocks Nearby: %s" % blocks_info
            entities, entities_info = get_nearest_entities(self, max_distance = 16, count = 8), "" 
            for entity in entities : 
                pos = entity.position
                if pos is not None :
                    entities_info += "%s (at x: %s, y: %s, z: %s);" % (entity.name,  math.floor(pos.x), math.floor(pos.y), math.floor(pos.z)) 
            if len(entities_info.strip()) > 0 : 
                add_log(title = self.pack_message("Get nearby entities info."), content = entities_info)
                status += "\n- Entities Nearby: %s" % entities_info
        except Exception as e : 
            add_log(title = self.pack_message("Exception when get information of nearby blocks and entities."), content = "Exception: %s" % e, label = "warning")
        return status

    def pack_message(self, message) : 
        return "[Agent \'%s\'] %s" % (self.configs["username"], message)

    def stop(self) :
        self.act_running, self.plan_running = False, False
        add_log(title = self.pack_message("Stop."), label = "success")
