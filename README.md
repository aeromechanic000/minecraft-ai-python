# MineMCP
A framework in Python to control MineCraft bots with various LLMs. Join the Discord server for communication!   

<a href="https://discord.gg/zAxFt9cZs8"><img src="https://s2.loli.net/2025/04/08/BOwDWH3XiyTAZgb.png" alt="Official Discord Server" width="180" height="30"></a>

# Quick Start
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
