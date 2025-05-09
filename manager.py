
import importlib.machinery
import importlib.util
import signal 

from agent import *
from world import *
from utils import *

class Plugin(object) : 
    def __init__(self, agent) : 
        self.agent = agent
        self.reminder = ""
    
    def get_reminder(self) : 
        return self.reminder

    def get_plugin_actions(self) : 
        return []

class Manager(object) : 
    def __init__(self, configs):
        signal.signal(signal.SIGINT, self.signal_handler)
        self.configs = configs
        global mcdata 
        mcdata = minecraft_data(self.configs["minecraft_version"])
        global prismarine_item 
        prismarine_item = prismarine_items(self.configs["minecraft_version"])
        self.load_plugins()
    
    def load_plugins(self) : 
        self.plugins, self.plugin_actions = {}, [] 
        plugins_dir = "./plugins"
        for item in os.listdir(plugins_dir) :
            plugin_path = os.path.join(plugins_dir, item, "main.py")
            if item in self.configs.get("plugins", []) and os.path.isfile(plugin_path) :
                plugin_main = "%s/%s/main.py" % (plugins_dir, item) 
                try :
                    loader = importlib.machinery.SourceFileLoader('my_class', plugin_main)
                    spec = importlib.util.spec_from_loader(loader.name, loader)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.plugins[item] = module.PluginInstance()
                    self.plugin_actions += self.plugins[item].get_actions()
                except Exception as e : 
                    add_log(title = "Exeption happens when importing plugin: %s" % item, content = "Exception: %s" % e, label = "warning")
        add_log(title = "Loaded plugins:", content = str(list(self.plugins.keys())), label = "manager")

    def signal_handler(self, sig, frame):
        add_log(title = "Exiting Minecraft AI...", label = "warning")
        self.stop()

    def start(self):
        self.agents = {} 
        for agent_configs in self.configs.get("agents", []) : 
            agent = Agent(agent_configs, self)
            self.agents[agent_configs["username"]] = agent 

    def get_actions(self) : 
        ignore_actions = self.configs.get("ignore_actions", [])
        if self.configs.get("insecure_coding_rounds", 0) < 1 and "new_action" not in ignore_actions :
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
                    param_value = validate_param(action.get("params", {}).get(key, None), value["type"])
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