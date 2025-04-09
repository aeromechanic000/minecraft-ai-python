
import signal, math, time, functools

from world import *
from agent import *
from utils import *

class MineMCP(object) : 
    def __init__(self, configs):
        signal.signal(signal.SIGINT, self.signal_handler)
        self.configs = configs
        global mcdata 
        mcdata = minecraft_data(self.configs["minecraft_version"])
        global prismarine_item 
        prismarine_item = prismarine_items(self.configs["minecraft_version"])
        self.agents = {} 
    
    def signal_handler(self, sig, frame):
        add_log(title = "Exiting MineMCP...", label = "execute")
        self.stop()

    def start(self):
        for agent_configs in self.configs.get("agents", []) : 
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
                if action is not None : 
                    action["execute"] = action_data["execute"]
        return action

    def stop(self):
        for agent in self.agents.values() : 
            agent.stop() 