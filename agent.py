
import math, time, functools 
from javascript import require, On 

from memory import *
from actions import *

class Agent(object) : 
    def __init__(self, configs, manager) :
        add_log(title = "Agent Created.", content = "Configs: %s" % configs, label = "success")
        self.configs, self.manager = configs, manager
        self.self_driven_thinking_timer = self.manager.configs.get("self_driven_thinking_timer", None)
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

        @On(self.bot, 'time')
        def handle_time(*args) :
            if self.self_driven_thinking_timer is not None : 
                if self.self_driven_thinking_timer < 1 : 
                    self.self_driven_thinking_timer = self.manager.configs.get("self_driven_thinking_timer", None)
                    self_driven_thinking(self)
                else :
                    self.self_driven_thinking_timer -= 1
        
        @On(self.bot, "login")
        def handle_login(*args) :
            skin_path = os.path.join("./skins", self.configs.get("skin", {}).get("file", None))
            if os.path.isfile(skin_path) :
                self.bot.chat("/skin set upload %s %s" % (self.configs.get("skin", {}).get("model", "classic"), skin_path))

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
                    if sizeof(self.bot.players) == 2 or "@%s" % self.bot.username in message or "@all" in message or "@All" in message or "@ALL" in message : 
                        record = {"type" : "message", "data" : {"sender" : username, "content" : message}}
                    elif username == self.bot.username and message.strip().startswith("[[Self-Driven Thinking]]") :
                        record = {"type" : "message", "data" : {"sender" : username, "content" : message.strip()[len("[[Self-Driven Thinking]]"):]}}
                    else :
                        self.memory.update({"type" : "status", "data" : {"sender" : username, "status" : message}})
                
                if len(record) < 1 : 
                    add_log(title = self.pack_message("Ignore message."), content = "sender: %s; message: %s" % (username, message), label = "warning", print = False)
                    return 

                add_log(title = self.pack_message("Get message."), content = "sender: %s; message: %s" % (username, message), label = "action")
                self.memory.update({"type" : "message", "data" : {"sender" : username, "content" : message}})
                work()
                    
            def work() : 
                current_working_process = get_random_label()
                self.working_process = current_working_process 
                message = self.memory.get_out_of_summary_message()
                while message is not None :
                    prompt = self.build_prompt(message) 
                    add_log(title = self.pack_message("Built prompt."), content = prompt, label = "action", print = False)
                    llm_result = call_llm_api(self.configs["provider"], self.configs["model"], prompt, max_tokens = self.configs.get("max_tokens", 4096))
                    add_log(title = self.pack_message("Get LLM response"), content = str(llm_result), label = "action", print = False)
                    if llm_result["status"] > 0 :
                        add_log(title = self.pack_message("Error in calling LLM: %s" % llm_result["error"]), label = "warning")
                    else :
                        _, data = split_content_and_json(llm_result["message"])
                        add_log(title = self.pack_message("Got data."), content = json.dumps(data, indent = 4), label = "action")
                        status_summary = data.get("status", None)
                        if status_summary is not None : 
                            self.status_summary = status_summary
                        action = self.manager.extract_action(data)
                        if action is not None : 
                            add_log(title = self.pack_message("Perfom action."), content = str(action), label = "action")
                            action["params"]["agent"] = self
                            run_action(action["perform"], action["params"])
                    message = self.memory.get_out_of_summary_message()
                    if message is not None and self.working_process != current_working_process :
                        break
                self.working_process = None

            def run_action(perform, params) : 
                try : 
                    result = perform(**params)
                except Exception as e : 
                    add_log(title = self.pack_message("Exception in performing action."), content = "Exception: %s" % e, label = "error")

    def build_prompt(self, message) :     
        prompt = '''
You are an AI assistant helping to plan the next action for a Minecraft bot. Based on the current status, memory, instruction, and the list of available actions, your task is to determine what the bot should do next. 

You must output: 
1. An updated status summary, if any change is needed. This should briefly describe the bot's current situation, goals, recent actions, and important outcomes that help track progress. 
2. The next action for the bot to execute. Choose from the list of 'Available Actions', and provide appropriate parameter values based on the definitions.

Important Guidelines:
1. Only update the status if new context or progress has occurred. Otherwise, set it to null.
2. Only generate an action if one is needed. Otherwise, set action to null.
3. When choosing an action, prioritize non-chat actions to make sure the task progresses. 
4. If the requirement is already sasified. Use chat to tell the reason why there is no need to perform any actions.

The selected action's parameters must follow the types and domains described under 'Available Actions'.

## Bot's Status
%s

## Bot's Memory
%s

## Lastest Message
%s

## Available Actions 
%s

''' % (self.get_status_info(), self.memory.get(), "\"%s\" said: \"%s\"" % (message["sender"], message["content"]), self.manager.get_actions_info())
        if self.manager.configs.get("insecure_coding_rounds", 0) > 0 : 
            prompt += '''
## Additional Instruction for Using `new_action`:
Among the available actions, always prioritize using predefined actions to accomplish the current task. Only use the new_action when it is clearly necessary — i.e., when none of the existing predefined actions are sufficient to fulfill the task. If you decide to use new_action, you must provide a clear, specific, and complete description of the task under the `task` parameter. This description should include:
    - What the bot is expected to do,
    - Any contextual details needed for proper execution,
    - The expected result or behavior,
    - Relevant constraints, if any.
This is essential because the new_action will result in generating a custom Python function (generated_action(agent)) that uses agent.bot to control the bot. Poorly specified tasks will cause the bot to fail or behave unpredictably.
'''
        prompt += '''
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
'''
        return prompt

    def get_mc_time(self) : 
        hrs, mins = 0, 0
        t = self.bot.time.timeOfDay 
        hrs = math.floor(t // 10000)
        mins = math.floor(min(59, (t % 10000) // (10000 / 60)))
        secs = math.floor(min(59, (t % 10000) % (10000 / 60)))
        return [self.bot.time.day, hrs, mins, secs]

    def get_status_info(self) : 
        status = "- Bot's Name: %s" % self.bot.username
        status += "\n- Bot's Profile: %s" % self.configs.get("profile", "A smart Minecraft AI character.")
        if len(self.status_summary.strip()) > 0 :
            status += "\n- Status Summary: %s" % self.status_summary
        status += "\n- Bot's Status of Health (from 0 to 20, where 0 for death and 20 for completely healthy): %s" % self.bot.health 
        status += "\n- Bot's Degree Of Hungry (from 0 to 20, where 0 for hungry and 20 for full): %s" % self.bot.food
        pos = get_entity_position(self.bot.entity)
        if pos is not None : 
            status += "\n- Bot's Position: x: %s, y: %s, z: %s" % (math.floor(pos.x), math.floor(pos.y), math.floor(pos.z))
        add_log(title = self.pack_message("Get primary status."), content = status, print = False)
        items_in_inventory, items_info = get_item_counts(self), "" 
        for key, value in items_in_inventory.items() : 
            items_info += "%s %s;" % (value, key)
        if len(items_info.strip()) > 0 : 
            add_log(title = self.pack_message("Get inventory items info."), content = items_info, print = False)
            status += "\n- Items in Inventory: %s" % items_info
        try : 
            blocks, blocks_info = get_nearest_blocks(self, block_names = get_block_names(), max_distance = 16, count = 8), ""
            for block in blocks : 
                pos = block.position
                if pos is not None :
                    blocks_info += "%s (at x: %s, y: %s, z: %s);" % (block.name,  math.floor(pos.x), math.floor(pos.y), math.floor(pos.z)) 
            if len(blocks_info.strip()) > 0 : 
                add_log(title = self.pack_message("Get nearby blocks info."), content = blocks_info, print = False)
                status += "\n- Blocks Nearby: %s" % blocks_info
            entities, entities_info = get_nearest_entities(self, max_distance = 16, count = 8), "" 
            for entity in entities : 
                pos = entity.position
                if pos is not None :
                    entities_info += "%s (at x: %s, y: %s, z: %s);" % (entity.name,  math.floor(pos.x), math.floor(pos.y), math.floor(pos.z)) 
            if len(entities_info.strip()) > 0 : 
                add_log(title = self.pack_message("Get nearby entities info."), content = entities_info, print = False)
                status += "\n- Entities Nearby: %s" % entities_info
        except Exception as e : 
            add_log(title = self.pack_message("Exception when get information of nearby blocks and entities."), content = "Exception: %s" % e, label = "warning")
        return status

    def pack_message(self, message) : 
        return "[Agent \'%s\'] %s" % (self.configs["username"], message)

    def stop(self) :
        self.act_running, self.plan_running = False, False
        add_log(title = self.pack_message("Stop."), label = "success")
