
import sys, math, time, functools 
import importlib.machinery
import importlib.util
from javascript import require, On 

from memory import *
from actions import *

class Agent(object) : 
    def __init__(self, configs, settings) :
        add_log(title = "Agent Created.", content = json.dumps(configs, indent = 4), label = "success")
        self.configs, self.settings = configs, settings 
        global mcdata 
        mcdata = minecraft_data(self.settings["minecraft_version"])
        global prismarine_item 
        prismarine_item = prismarine_items(self.settings["minecraft_version"])
        self.load_plugins()
        self.self_driven_thinking_timer = self.configs.get("self_driven_thinking_timer", None)
        self.status_summary = ""
        self.working_process = None
        bot_configs = self.configs.copy()
        bot_configs.update({
            "host" : self.settings["host"],
            "port" : self.settings["port"],
            "version" : self.settings["minecraft_version"],
            "checkTimeoutInterval" : 60 * 10000,
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

        @On(self.bot, "end")
        def handle_end(*args):
            self.bot.quit()
            add_log(title = self.pack_message("Bot end."), label = "warning")
            
        @On(self.bot, "login")
        def handle_login(*args) :
            skin_path = self.configs.get("skin", {}).get("file", None)
            if skin_path is not None : 
                skin_path = os.path.expanduser(skin_path)
                if os.path.isfile(skin_path) and self.memory.skin_path != skin_path :
                    self.bot.chat("/skin set upload %s %s" % (self.configs.get("skin", {}).get("model", "classic"), skin_path))
                    self.memory.skin_path = skin_path
                    self.memory.save()
                    add_log(title = self.pack_message("Mannual restart is required"), content = "After settting the skin, you need to restart minecraft-ai-python for the AIC to behave as expected.", label = "warning")

        @On(self.bot, "spawn")
        def handle_spawn(*args) :
            add_log(title = self.pack_message("I spawned."), label = "success")
            messages = self.memory.get_out_of_summary_message()
            if len(messages) > 0 :
                self.bot.emit("work")
            else :
                self.bot.chat("Hi. I am %s." % self.bot.username)
            viewer_port = self.configs.get("viewer_port", None)
            viewer_first_person = self.configs.get("viewer_first_person", False)
            viewer_distance = self.configs.get("viewer_distance", 6)
            if viewer_port is not None : 
                require('canvas')
                viewer = require('prismarine-viewer')
                viewer["mineflayer"](self.bot, {"port": viewer_port, "firstPerson" : viewer_first_person, "viewDistance" : viewer_distance})

            @On(self.bot, 'time')
            def handle_time(*args) :
                # this is triggered for every 20 time ticks
                # An hour in Mincraft has 10000 time ticks, and it takes 20 mins in real world.
                if self.self_driven_thinking_timer is not None : 
                    if self.self_driven_thinking_timer < 1 : 
                        self_driven_thinking(self)
                    else :
                        self.self_driven_thinking_timer -= 1
            
            @On(self.bot, "think")
            def handle_think(this, message):
                record = {"type" : "reflection", "data" : {"sender" : self.bot.username, "content" : message}}
                self.memory.update(record)
                self.bot.emit("work")

            @On(self.bot, 'chat')
            def handle_chat(this, username, message, *args):
                message = message.strip()
                ignore_messages = [
                    "Set own game mode to",
                    "Set the time to",
                    "Set the difficulty to",
                    "Teleported ",
                    "Set the weather to",
                    "Gamerule "
                ]
                status_messages = [
                    "Gave ",
                ]
                record = {}

                if username is not None and all([not message.startswith(msg) for msg in ignore_messages + self.settings.get("ignore_messages", [])]) : 
                    if username == self.bot.username :
                        record = {"type" : "report", "data" : {"sender" : username, "content" : message}}
                    elif (sizeof(self.bot.players) == 2 or "@%s" % self.bot.username in message or "@all" in message or "@All" in message or "@ALL" in message) and all(not message.startswith(msg) for msg in status_messages) :
                        if "@admin reset working process" in message :
                            self.working_process = None
                            add_log(title = self.pack_message("Working process reset."), label = "warning")
                        else :
                            record = {"type" : "message", "data" : {"sender" : username, "content" : message}}
                    else :
                        record = {"type" : "status", "data" : {"sender" : username, "content" : message}}

                if len(record) < 1 : 
                    add_log(title = self.pack_message("Ignore message."), content = "sender: %s; message: %s" % (username, message), label = "warning", print = False)
                    return 

                add_log(title = self.pack_message("Get message."), content = "sender: %s; message: %s; type: %s" % (username, message, record["type"]), label = "action")
                self.memory.update(record)

                if record["type"] == "message" :
                    self.bot.emit("work")
                    
            @On(self.bot, "work")
            def handle_work(this) : 
                if self.working_process is not None : 
                    add_log(title = self.pack_message("Current working process is not finished."), content = "working process: %s" % self.working_process, label = "warning")
                    return 
                    
                messages = self.memory.get_out_of_summary_message()
                if len(messages) < 1 :
                    add_log(title = self.pack_message("There is no messages to work on."), label = "warning")
                    return
                
                self.working_process = get_random_label() 

                prompt = self.build_prompt(messages) 
                json_keys = {
                    "status" : {
                        "description" : "An updated version of the status summary of the agent. If no update is needed, set value to null.",
                    },
                    "action" : {
                        "description" : "An JSON dictionary to specify the next action for the agent to execute. If no action is needed, set value to null.",
                        "keys" : {
                            "name" : {
                                "description" : "a JSON string of the action name which is listed in the 'Available Actions'",
                            },
                            "params" : {
                                "description" : "a JSON dictionary where keys are the names of the parameters as described in the 'Available Actions' for the selecte action; and the associated value should follow the 'type' and 'domain' constrains in the description.",
                            }
                        } 
                    }, 
                    "message" : {
                        "description" : "A message in JSON string to the player who sent you the lastest message, if necessary. If not applicable, leave the value to null.",
                    },
                }
                examples = [
                    '''
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
''',
                ]
                add_log(title = self.pack_message("Built prompt."), content = prompt, label = "action", print = False)
                provider, model = self.get_provider_and_model("action")
                llm_result = call_llm_api(provider, model, prompt, json_keys, examples, max_tokens = self.configs.get("max_tokens", 4096))
                add_log(title = self.pack_message("Get LLM response"), content = json.dumps(llm_result, indent = 4), label = "action", print = False)
                data = llm_result["data"]
                if data is not None :
                    status_summary = data.get("status", None)
                    if status_summary is not None : 
                        self.status_summary = status_summary
                    resp_message = data.get("message", None)
                    if resp_message is not None and isinstance(resp_message, str) :
                        chat(self, message["sender"], resp_message) 
                    action = self.extract_action(data)
                    if action is not None : 
                        action["params"]["agent"] = self
                        run_action(action["perform"], action["params"])

                self.working_process = None
                self.memory.summarize()
                message = self.memory.get_out_of_summary_message()
                if message is not None :
                    self.bot.emit("work")
                elif self.self_driven_thinking_timer is not None :
                    self_driven_thinking(self)
            
            def run_action(perform, params) : 
                try : 
                    add_log(title = self.pack_message("Perfom action."), content = "perform: %s; params: %s" % (perform.__name__, params), label = "action")
                    result = perform(**params)
                except Exception as e : 
                    add_log(title = self.pack_message("Exception in performing action."), content = "Exception: %s" % e, label = "error")

    def build_prompt(self, messages) :     
        message_info_list = []
        for message in messages :
            if message["sender"] == self.bot.username :
                message_info_list.append("Reflection: \"%s\"" % message["content"])
            else :
                message_info_list.append("\"%s\" said: \"%s\"" % (message["sender"], message["content"]))

        prompt = '''
You are an AI assistant helping to plan the next action for a Minecraft bot. Based on the current status, memory, instruction, and the list of available actions, your task is to determine what the bot should do next. 

You must output: 
1. An updated status summary, if any change is needed. This should briefly describe the bot's current situation, goals, recent actions, and important outcomes that help track progress. 
2. The next action for the bot to execute. Choose from the list of 'Available Actions', and provide appropriate parameter values based on the definitions.
3. An message to the player who sent the latest message, if necessary.

Important Guidelines:
1. Only update the status if new context or progress has occurred. Otherwise, set it to null.
2. Only generate an action if one is needed. Otherwise, set action to null.
3. You should consider the latest message with the highest priority when generating the action.
4. When choosing an action, consider all available actions and select the one that is most consistent with the task requirement. 
5. When choosing an action, prioritize non-chat actions to make sure the task progresses. 
6. When is is required to perform some moves, choose an action to response, and `chat` should be the last option.
7. If the requirement is already sasified. Use chat to tell the reason why there is no need to perform any actions.

The selected action's parameters must follow the types and domains described under 'Available Actions'.

## Bot's Status
%s

## Bot's Memory
%s

## Lastest Message
%s

## Available Actions 
%s

''' % (self.get_status_info(), self.memory.get(), "\n".join(message_info_list), self.get_actions_info())
        if self.settings.get("insecure_coding_rounds", 0) > 0 : 
            prompt += '''
## Additional Instruction for Using `new_action`:
Among the available actions, always prioritize using predefined actions to accomplish the current task. Only use the new_action when it is clearly necessary — i.e., when none of the existing predefined actions (execluding `chat`) are sufficient to fulfill the task. If you decide to use new_action, you must provide a clear, specific, and complete description of the task under the `task` parameter. This description should include:
    - What the bot is expected to do,
    - Any contextual details needed for proper execution,
    - The expected result or behavior,
    - Relevant constraints, if any.
This is essential because the new_action will result in generating a custom Python function (generated_action(agent)) that uses agent.bot to control the bot. Poorly specified tasks will cause the bot to fail or behave unpredictably.
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
    
    def load_plugins(self) : 
        self.plugins, self.plugin_actions = {}, [] 
        plugins_dir = "./plugins"
        for item in os.listdir(plugins_dir) :
            plugin_path = os.path.join(plugins_dir, item, "main.py")
            if item in self.settings.get("plugins", []) and os.path.isfile(plugin_path) :
                plugin_main = "%s/%s/main.py" % (plugins_dir, item) 
                try :
                    loader = importlib.machinery.SourceFileLoader('my_class', plugin_main)
                    spec = importlib.util.spec_from_loader(loader.name, loader)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.plugins[item] = module.PluginInstance(self)
                    self.plugin_actions += self.plugins[item].get_actions()
                except Exception as e : 
                    add_log(title = "Exeption happens when importing plugin: %s" % item, content = "Exception: %s" % e, label = "warning")
        add_log(title = self.pack_message("Loaded plugins:"), content = str(list(self.plugins.keys())), label = "agent")

    def get_plugin_reminder_info(self) : 
        reminder_info_list = []
        for key, value in self.plugins.items() :
            if value is not None :
                reminder = value.get_reminder()
                if reminder is not None and len(reminder.strip()) > 0 :
                    reminder_info_list.append("\n [Reminder from \'%s\'] %s" % (key, reminder))
        return "\n".join(reminder_info_list)

    def get_actions(self) : 
        ignore_actions = self.settings.get("ignore_actions", [])
        if self.settings.get("insecure_coding_rounds", 0) < 1 and "new_action" not in ignore_actions :
            ignore_actions.append("new_action")
        actions = []
        for action in get_primary_actions() + self.plugin_actions : 
            if action["name"] not in ignore_actions : 
                actions.append(action)
        return actions

    def get_actions_info(self) : 
        actions_info = ""
        for i, action in enumerate(self.get_actions()) : 
            actions_info += "\n\n### Action %d\n- Action Name : %s\n- Action Description : %s " % (i, action["name"], action["description"])
            if len(action["params"]) > 0 : 
                actions_info += "\n- Action Parameters:"
                for key, value in action["params"].items() : 
                    actions_info += "\n\t- %s : %s The parameter should be given in a JSON type of '%s'." % (key, value["description"], value["type"])
        return actions_info

    def get_actions_desc(self) : 
        actions_desc = ""
        for action in self.get_actions() : 
            actions_desc += "\n\t- %s : %s" % (action["name"], action["description"])
        return actions_desc
    
    def extract_action(self, data) : 
        action = data.get("action", None) 
        if action is not None and isinstance(action, dict) : 
            name = action.get("name", None)
            action_data = None
            for a in self.get_actions() : 
                if a["name"] == name : 
                    action_data = a
                    break
            if action_data is not None :
                for key, value in action_data["params"].items() : 
                    param_value = validate_param(action.get("params", {}).get(key, None), value["type"], value.get("domain", None))
                    if param_value is not None :
                        action["params"][key] = param_value
                    else : 
                        action = None
                        break
                if action is not None : 
                    action["perform"] = action_data["perform"]
        return action

    def get_provider_and_model(self, tag = None) :
        provider, model =  self.configs["provider"], self.configs["model"]
        if tag is not None and isinstance(tag, str) :
            provider = self.configs.get(tag, {}).get("provider", provider)
            model = self.configs.get(tag, {}).get("model", model)
        return provider, model

    def pack_message(self, message) : 
        return "[Agent \"%s\"] %s" % (self.configs["username"], message)


if __name__ == "__main__" : 
    configs = read_json(sys.argv[1])
    settings = read_json("./settings.json")
    logging.basicConfig(
            filename = os.path.join("./logs/log-%s-%s.json" % (get_datetime_stamp(), configs["username"])),
            filemode = 'a',
            format = '%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
            datefmt = '%H:%M:%S',
            level = logging.DEBUG, 
    )
    Agent(configs, settings)