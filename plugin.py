
from agent import *
from world import *
from utils import *

class Plugin(object) : 
    def __init__(self, agent) : 
        self.agent = agent
        self.reminder = "" 
        self.plugin_name = None
    
    def get_reminder(self) : 
        return self.reminder

    def get_actions(self) : 
        return []

    def pack_message(self, message) : 
        if self.plugin_name is not None :
            return "[Agent \"%s\"] [Plugin \"%s\"] %s" % (self.agent.configs["username"], self.plugin_name, message)
        else :
            return "[Agent \"%s\"] [Plugin] %s" % (self.agent.configs["username"], message)

