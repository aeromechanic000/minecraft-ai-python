
import sys, signal, threading, math
from javascript import require, On 

from model import *
from utils import *

mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')

def get_actions(action_names = None) : 
    availabel_actions = [
        {
            "name" : "go_to_player", 
            "desc": "Go to the given player.",
            "params": {
                "player_name": {"type" : "string", "desc" : "The name of the player to go to.", "domain" : "any valid value"},
                "closeness": {"type" : "float", "desc" : "How close to get to the player. If no special reason, closeness should be set to 1.", "domain" : [0, math.inf]},
            },
            "execute" : None,  
        },
        {
            "name" : "move_away", 
            "desc": "Move away from the current location in any direction by a given distance.",
            "params": {
                "distance": {"type" : "float", "desc" : "The distance to move away.", "domain": [20, math.inf]},
            },
            "execute" : None,  
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
        except : 
            valid_value = None
    return valid_value

class Agent(object) : 
    def __init__(self, configs, mcp_manager) :
        add_log(title = "Agent Created.", content = "Agent has been created with configs: %s" % configs, label = "header")
        self.configs, self.mcp_manager = configs, mcp_manager
        bot_configs = self.configs.copy()
        self.bot = mineflayer.createBot(bot_configs)
        self.bot.loadPlugin(pathfinder.pathfinder)
        self.plan_thread, self.act_thread = None, None
        self.status_summary, self.recent_actions = "", [] 
        self.messages, self.actions = [], []
        self.plan_running, self.act_running = False, False

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
                        # Got whisper message 
                        self.push_msg({"sender" : sender, "message" : message, "type" : "whisper"})
                    else : 
                        # Got update message 
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
                add_log(title = self.pack_message("Perfom action."), content = str(action))
                for i in range(self.mcp_manager.configs.get("action_retry_times", 1)) :
                    add_log(title = self.pack_message("Try for the %d-th time." % i))
                    try : 
                        if action["name"] == "go_to_player" : 
                            player = self.bot.players[action["params"]["player_name"]]
                            if player is not None and player.entity is not None :  
                                pos = player.entity.position
                                self.bot.pathfinder.setMovements(self.movements)
                                self.bot.pathfinder.setGoal(pathfinder.goals.GoalNear(pos.x, pos.y, pos.z, action["params"]["closeness"])) 
                                break
                            else :
                                add_log(title = self.pack_message("Failed to get player's position."), label = "warning")
                        elif action["name"] == "move_away" : 
                            if self.bot.entity is not None :
                                pos = self.bot.entity.position
                                vector = get_random_vector(action["params"]["distance"])
                                self.bot.pathfinder.setMovements(self.movements)
                                self.bot.pathfinder.setGoal(pathfinder.goals.GoalNear(pos.x + vector[0], pos.y, pos.z + vector[1], 0)) 
                                break
                            else : 
                                add_log(title = self.pack_message("Failed to get bot's position."), label = "warning")
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
''' % (self.get_status(), self.configs.get("personality", "A smart Minecraft agent."), latest_messages, self.mcp_manager.get_actions_info())
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
            add_log(title = self.pack_message("Update status: %s" % status), print = False)
        else :
            add_log(title = self.pack_message("Keep status unchanged."), print = False)
        
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

class MineMCP(object) : 
    def __init__(self, configs):
        signal.signal(signal.SIGINT, self.signal_handler)
        self.configs = configs
        self.agents = {} 
    
    def signal_handler(self, sig, frame):
        add_log(title = "Exiting MineMCP...", label = "execute")
        self.stop()

    def start(self):
        for agent_configs in self.configs.get("agents", []) : 
            agent_configs["host"] = self.configs["host"]
            agent_configs["port"] = self.configs["port"]
            agent = Agent(agent_configs, self)
            self.agents[agent_configs["username"]] = agent 

    def get_actions_info(self, action_names = None) : 
        actions = get_actions(action_names)
        actions_info = ""
        for i, action in enumerate(actions) : 
            actions_info += "\n\n### Action %d\n- Action Name : %s\n- Action Description : %s " % (i, action["name"], action["desc"])
            if len(action["params"]) > 0 : 
                actions_info += "\n- Action Parameters:"
                for key, value in action["params"].items() : 
                    actions_info += "\n\t- %s : %s The parameter should be given in a JSON type of '%s', and fit into domain '%s'." % (key, value["desc"], value["type"], value["domain"])

        return actions_info

    def get_actions_desc(self, action_names = None) : 
        actions = get_actions(action_names)
        actions_desc = ""
        for action in actions : 
            actions_desc += "\n\t- %s : %s" % (action["name"], action["desc"])
        return actions_desc
    
    def extract_action(self, data) : 
        actions = get_actions()
        action = data.get("action", None) 
        if action is not None and isinstance(action, dict) : 
            name = action.get("name", None)
            action_data = None
            for a in actions : 
                if a["name"] == name : 
                    action_data = a
                    break
            if action_data is not None :
                for key, value in action_data["params"].items() : 
                    param_value = validate_param(action.get("params", {}).get(key, None), value["type"], value["domain"])
                    if param_value is not None :
                        action["params"][key] = param_value
                    else : 
                        action = None
                        break
        return action

    def stop(self):
        for agent in self.agents.values() : 
            agent.stop() 
            