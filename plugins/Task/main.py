
import os, sys, time
sys.path.append("../../")

from plugin import Plugin 
from agent import * 

def execute_task(agent) : 
    agent.plugins["Task"].execute_task()

def new_task(agent, task_name, requirement, collaborate) : 
    agent.plugins["Task"].new_task(task_name, requirement, collaborate)

class Task(object) : 
    def __init__(self, agent, configs) : 
        self.agent, self.configs = agent, configs
    
    def execute(self) :
        pass

class PluginInstance(Plugin) :
    def __init__(self, agent) : 
        super().__init__(agent)
        self.plans, self.task, self.goal = {}, None, None 
        self.available_agents = []
        self.plugin_name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        self.path = "./plugins/%s/" % self.plugin_name
        try :
            plans_dir = os.path.join(self.path, "plans")
            for file in os.listdir(plans_dir) :
                if file.endswith('.json') and not file.startswith('.') : 
                    self.plans[file[0:-5]] = read_json(os.path.join(plans_dir, file))
            task_path = "./bots/%s/task.json" % self.agent.configs["username"]
            if os.path.isfile(task_path) : 
                self.task = Task(self.agent, read_json(task_path))
            for file in self.agent.settings["agents"] :
                profile = read_json(file)
                print(profile, self.agent.configs["username"])
                if profile["username"] != self.agent.configs["username"] :
                    self.available_agents.append(profile["username"])
        except Exception as e :  
            add_log(title = self.pack_message("Exception when initializing:"), content = str(e), label = "warning")
        self.load()
    
    def load(self) : 
        filepath = os.path.join(self.path, "save.json")
        if os.path.isfile(filepath) :
            data = read_json(filepath)
    
    def save(self) :
        if os.path.isdir(self.path) :
            filepath = os.path.join(self.path, "save.json")
            data = {}
            write_json(data)
    
    def get_actions(self) : 
        return [
            {
                "name" : "execute_task",
                "description" : "Execute the predefined task, only if its status is 'True', which means the predefined task is not None. Status of the predefined task: %s" % (self.task is not None, ),
                "params" : {},
                "perform" : execute_task, 
            },
            {
                "name" : "new_task",
                "description" : "Start a new task with the given name and requirements",
                "params" : {
                    "task_name": { "type" : "string", "description" : "name of the task to perform, which should be one of the options ['cooking', 'crafting', 'construction']." },
                    "requirement": { "type" : "string", "description" : "a string that describes the requirement of the task in natural language." },
                    "collaborate": { "type" : "bool", "description" : "indicate whether the bot should try to collaborate in executing the task." },
                },
                "perform" : new_task, 
            },
        ]
    
    def execute_task(self) : 
        if self.task is not None : 
            add_log(title = self.pack_message("Execute predefined task."), content = json.dumps(self.task.configs, indent = 4), label = "plugin")
            self.task.execute()
        else :
            add_log(title = self.pack_message("None predefined task."), content = "Nothing to execute.", label = "warning")

    def new_task(self, task_name, requirement, collaborate = False) : 
        add_log(title = self.pack_message("Get a new task."), content = "task_name = %s, requirement = %s, collaborate = %s" % (task_name, requirement, collaborate), label = "plugin")

        self.goal = requirement

        if task_name == "cooking" :
            self.goal += "\n\nFor cooking tasks: First gather all necessary ingredients. Use furnaces, smokers, or campfires as appropriate for the recipe. Ensure you have fuel for cooking. Check your recipe book for crafting recipes if needed."
        elif task_name == "crafting" :
            self.goal += "\n\nFor crafting tasks: Gather all required materials and tools. Use the appropriate crafting station (crafting table, anvil, enchanting table, etc.). Follow the correct recipe pattern. Ensure you have enough materials for the desired quantity."
        elif task_name == "construction" :
            self.goal += "\n\nFor construction tasks: Plan the build layout first. Gather all necessary building materials and tools. Start with the foundation and work systematically. Consider lighting, accessibility, and structural integrity. Use scaffolding if building tall structures."
        
        if collaborate == True :
            if len(self.available_agents) > 0 :
                self.goal += "\n\nYou must collaborate with other players: %s. IMPORTANT: Before starting any work, communicate with your teammates to create a clear plan. Discuss what materials and resources are needed, then divide responsibilities - decide who will gather which materials, who will handle which parts of the task, and establish a timeline. Once everyone agrees on the plan and their assigned roles, execute your part while coordinating with others to ensure efficient completion. Use chat to share progress updates and coordinate handoffs between team members." % ", ".join(self.available_agents)
            else : 
                add_log(title = self.pack_message("Parameter 'collaborate = %s' ignored." % collaborate), content = "There is not enough AI characters to collaborate.", label = "warning")
        
        add_log(title = self.pack_message("Add record to memory"), content = "Goal of task: %s" % self.goal, label = "plugin")
        record = {"type" : "message", "data" : {"sender" : self.agent.bot.username, "content" : self.goal}}
        self.agent.memory.update(record)
        self.agent.bot.emit("work")
        self.goal = None