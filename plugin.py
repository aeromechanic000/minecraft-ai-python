
from agent import *
from world import *
from utils import *

class Plugin(object) : 
    def __init__(self, agent) : 
        self.agent = agent
        self.reminder = "" 
    
    def get_reminder(self) : 
        return self.reminder

    def get_actions(self) : 
        return []
