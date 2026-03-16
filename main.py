
import os, multiprocessing, signal, subprocess
import argparse, json

from agent import *
from utils import *
from vision import check_vision_requirements, check_and_prepare_model

# Import monitor server if available
try:
    from monitor.server import MonitorServer
    MONITOR_AVAILABLE = True
except ImportError:
    MONITOR_AVAILABLE = False

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
        self.monitor_server = None
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def start(self):
        # Start web monitor if enabled
        web_monitor = self.settings.get("web_monitor", {})
        if web_monitor.get("enabled", False) and MONITOR_AVAILABLE:
            port = web_monitor.get("port", 8080)
            try:
                self.monitor_server = MonitorServer(port=port)
                self.monitor_server.start()
                add_log(title = "Web monitor started.", content = "Port: %d" % port, label = "system")
            except Exception as e:
                add_log(title = "Failed to start web monitor.", content = "Exception: %s" % e, label = "warning")
        elif web_monitor.get("enabled", False) and not MONITOR_AVAILABLE:
            add_log(title = "Web monitor not available.", content = "FastAPI/uvicorn not installed. Run: uv add fastapi uvicorn", label = "warning")

        agents = self.settings.get("agents", [])

        # Check vision requirements for all agents
        add_log(title = "Checking vision requirements...", label = "system")
        vision_status = check_vision_requirements(agents)

        # Handle models that need to be downloaded
        for profile_path, status in vision_status.items():
            if status["enabled"] and not status["model_ready"]:
                model_name = status["model"]
                add_log(
                    title = "Vision model check",
                    content = f"Profile: {profile_path}, Model: {model_name} (not downloaded)",
                    label = "warning"
                )

                model_ready, should_continue = check_and_prepare_model(model_name)

                if not should_continue:
                    add_log(
                        title = "Agent startup cancelled",
                        content = f"Profile: {profile_path}",
                        label = "system"
                    )
                    # Remove this agent from the list
                    if profile_path in agents:
                        agents.remove(profile_path)
                elif not model_ready:
                    # Mark that model is not ready but continue
                    vision_status[profile_path]["model_ready"] = False
                    add_log(
                        title = "Starting without vision model",
                        content = f"Profile: {profile_path}, Vision will be disabled",
                        label = "warning"
                    )

        if not agents:
            add_log(title = "No agents to start.", label = "system")
            return

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