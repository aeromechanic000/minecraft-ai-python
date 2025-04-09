# MineMCP 🤖

MineMCP is a Python framework for controlling Minecraft bots using various LLMs. It builds upon the excellent foundation laid by the <a href="https://github.com/kolbytn/mindcraft">MINDcraft</a> project, which offers an efficient system for enabling LLM agents to interact with Minecraft environments using MCP-style command-to-action mappings. Many ideas and design choices from MINDcraft have been incorporated into MineMCP. In essence, MineMCP can be seen as the Pythonic counterpart to MINDcraft (At lease, we hope so 😉).

🦾 MineMCP is under development, more functions are added and optimized. If you have any question, welcome to join the our Discord server for more communications! 

<a href="https://discord.gg/zAxFt9cZs8"><img src="https://s2.loli.net/2025/04/08/BOwDWH3XiyTAZgb.png" alt="Official Discord Server" width="180" height="30"></a>

# Quick Start 🚀
0. You need Minecraft Java Edition 1.21.1 for running MineMCP. 
1. Clone the repo.
```
git clone https://github.com/aeromechanic000/MineMCP.git
```
2. Enter the root directory.
```
cd MineMCP
```
3. Install the required node modules.
```
npm install 
```
5. Create a conda environment with python3.10.
```
conda create -n minemcp python=3.10
```
6. Activate the created conda environment. 
```
conda activate minemcp
```
7. Install the required python pacages. 
```
pip install -r requirements.txt
```
8. Create a new world of version 1.21.1 of Minecraft Java Edition and open it to LAN at port 55916.
9. Start the bots. 
```
python main.py
```
10. You can configure the agent in configs.json, which is the default configuration. You can also specify another configuration file when start main.py. You need to restart main.py with new configuaration, after quit the current process by pressing CTRL-C.
```
python main.py path/to/another/configs
```

# Citation
```
@misc{minemcp2025,
    Author = {MineMCP},
    Title = {MineMCP: LLM-Driven Minecraft Agents in Python},
    Year = {2025},
    url={https://github.com/aeromechanic000/MineMCP}
}
```