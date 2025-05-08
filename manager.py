
import signal, math, time, functools

from agent import *
from world import *
from utils import *

class Manager(object) : 
    def __init__(self, configs):
        signal.signal(signal.SIGINT, self.signal_handler)
        self.configs = configs
        global mcdata 
        mcdata = minecraft_data(self.configs["minecraft_version"])
        global prismarine_item 
        prismarine_item = prismarine_items(self.configs["minecraft_version"])
        self.agents = {} 
    
    def signal_handler(self, sig, frame):
        add_log(title = "Exiting Minecraft AI...", label = "warning")
        self.stop()

    def start(self):
        for agent_configs in self.configs.get("agents", []) : 
            agent = Agent(agent_configs, self)
            self.agents[agent_configs["username"]] = agent 

    def get_actions(self) : 
        ignore_actions = self.configs.get("ignore_actions", [])
        if self.configs.get("insecure_coding", False) == False and "new_action" not in ignore_actions :
            ignore_actions.append(ignore_actions)
        actions = []
        for action in get_primary_actions() : 
            if action["name"] not in ignore_actions : 
                actions.append(action)
        return actions

    def get_actions_info(self) : 
        actions_info = ""
        for i, action in enumerate(self.get_actions()) : 
            actions_info += "\n\n### Action %d\n- Action Name : %s\n- Action Description : %s " % (i, action["name"], action["desc"])
            if len(action["params"]) > 0 : 
                actions_info += "\n- Action Parameters:"
                for key, value in action["params"].items() : 
                    actions_info += "\n\t- %s : %s The parameter should be given in a JSON type of '%s', and fit into domain '%s'." % (key, value["desc"], value["type"], value["domain"])
        return actions_info

    def get_actions_desc(self) : 
        actions_desc = ""
        for action in self.get_actions() : 
            actions_desc += "\n\t- %s : %s" % (action["name"], action["desc"])
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
                    param_value = validate_param(action.get("params", {}).get(key, None), value["type"], value["domain"])
                    if param_value is not None :
                        action["params"][key] = param_value
                    else : 
                        action = None
                        break
                if action is not None : 
                    action["perform"] = action_data["perform"]
        return action

    def stop(self):
        for agent in self.agents.values() : 
            agent.stop() 