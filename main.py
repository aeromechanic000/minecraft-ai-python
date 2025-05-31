
import os, multiprocessing, signal, subprocess
import argparse, json

from agent import *
from utils import *

class AgentProcess(object) :
    def __init__(self, configs_path) : 
        self.running = False
        self.configs_path = configs_path
        signal.signal(signal.SIGINT, self.stop)
        self.process = None
    
    def run(self) : 
        self.running = True
        while self.running : 
            try : 
                self.process = subprocess.Popen(['python', 'agent.py', self.configs_path])
                return_code = self.process.wait()
                content = str(return_code) 
                if return_code == 0 : 
                    add_log(title = "Agent process restart.", label = "system")
                else :
                    if return_code == -15 : 
                        content = "Interupted by 'terminate' command." 
                    add_log(title = "Agent process exit.", content = content, label = "system")
                    break
            except Exception as e:
                add_log(title = "Exception in agent process.", content = str(e), label = "system")

    def stop(self, signum, frame):
        add_log(title = "Terminate Agent Process.", label = "system")
        self.running = False 
        self.process.terminate()

def run_agent_process(configs_path) : 
    agent_process = AgentProcess(configs_path)
    agent_process.run()

class Manager(object) : 
    def __init__(self, settings):
        self.settings = settings
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    def start(self):
        agents = self.settings.get("agents", [])
        with multiprocessing.Pool(processes=len(agents)) as pool:
            results = pool.map(run_agent_process, agents)    
        add_log(title = "Minecraft AI exit.", label = "system")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Process agent profiles and other options")
    parser.add_argument('--agents', nargs='+', type=str, help='Path to one or more agent profile JSON files')
    args = parser.parse_args()

    for d in ["./logs", "./generated_actions"] : 
        if not os.path.isdir(d) : 
            os.mkdir(d)

    logging.basicConfig(
            filename = os.path.join("./logs/log-%s.json" % (get_datetime_stamp())),
            filemode = 'a',
            format = '%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
            datefmt = '%H:%M:%S',
            level = logging.DEBUG, 
    )

    settings = read_json("./settings.json")
    settings["agents"] = args.agents if args.agents is not None else settings["agents"] 
    Manager(settings).start()