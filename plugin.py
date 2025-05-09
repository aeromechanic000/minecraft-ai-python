
from agent import *
from world import *
from utils import *

class Plugin(object) : 
    def __init__(self) : 
        self.reminder = {} 
    
    def get_reminder(self, agent) : 
        return self.reminder.get(agent.configs["username"], None)

    def get_actions(self) : 
        return []
