
import sys, time
sys.path.append("../../")

from plugin import Plugin 

def pop_dancing(agent, duration) :
    result = ""
    agent.bot.chat("I am dancing")
    agent.bot.setControlState("jump", True)
    time.sleep(duration)
    agent.bot.setControlState("jump", False)
    return result

class PluginInstance(Plugin) :
    def get_actions(self) :
        return [
            {
                "name" : 'dance_poping',
                "description" : 'Dance poping.',
                "params" : {
                    'duration': {"type" : 'float', "description" : 'Duration in seconds (e.g., 0.1 for 100 milliseconds).'},
                },
                "perform" : pop_dancing, 
            },
        ]