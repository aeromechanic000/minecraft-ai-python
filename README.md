# <img src="https://s2.loli.net/2025/04/18/RWaFJkY4gSDLViy.png" alt="Minecraft AI" width="36" height="36"> Minecraft AI-Python: An Open Framework for Building Embodied AI in Minecraft

Minecraft AI-Python is a modular framework designed to support the creation and customization of AI Characters (AICs) within Minecraft environments. It provides a stable and extensible interface for perception, action, communication, memory, and reflection—enabling complex individual and multi-agent behaviors.

🦾 Minecraft AI-Python is under development, more functions are added and optimized. If you have any question, welcome to join the our Discord server for more communications! 

<a href="https://discord.gg/RKjspnTBmb" target="_blank"><img src="https://s2.loli.net/2025/04/18/CEjdFuZYA4pKsQD.png" alt="Official Discord Server" width="180" height="36"></a>

🪇 **Relationship between Minecraft AI-Python and Minecraft AI**

This project is part of the broader Minecraft AI ecosystem. While the original [Minecraft AI](https://github.com/aeromechanic000/minecraft-ai) project focuses on a JavaScript-based infrastructure with integrated components, minecraft-ai-python emphasizes simplicity, flexibility, and rapid development in Python. It is ideal for educational experiments, prototyping research ideas, and custom agent development by individual contributors.

🤖 **Relationship between Minecraft AI and MINDcraft**

minecraft-ai shares many conceptual foundations with the [MINDCraft](https://github.com/kolbytn/mindcraft) project introduced by Convex researchers—particularly around planning, reflection, and social coordination in open-ended virtual environments. However, our approach prioritizes real-world usability and developer extensibility, with a special focus on:
    
- ⚙️️ A plugin-based mechanism for extending agent capabilities without modifying core logic
- 🧪 A practical and cohesive framework that includes memory, reflection, and coordination modules 

**The Introduction Video**

<a href="https://www.youtube.com/watch?v=9phN6OWPmKg" target="_blank"><img src="https://s2.loli.net/2025/04/09/Kk35BEwvVlUuq9C.png" alt="Minecraft AI-Python: LLM-Driven Minecraft Agents in Python" width="820" height="450"></a>

## 🖼️ Showcases 

<table>
<tr>
<td><img src="https://s2.loli.net/2025/04/09/CKwbHroZaj4xJSU.gif" alt="Minecraft AI-Python: LLM-Driven Minecraft Agents in Python" width="360" height="220"></td>
</tr>
</table>

## 🚀 Quick Start 
This guide will walk you through setting up and running the `minecraft-ai-python` system. Make sure you have **Minecraft Java Edition 1.21.1** installed and ready.

### Prerequisites

* **Minecraft Java Edition 1.21.1**
* **Node.js** and **npm**
* **Python 3.10** (Recommended: use [Anaconda](https://www.anaconda.com/))
* An API token from your preferred LLM provider (e.g., OpenRouter, etc.)

### 1. Clone the Repository

```bash
git clone https://github.com/aeromechanic000/minecraft-ai-python.git
cd minecraft-ai-python
```

### 2. Install Node Dependencies

Install the required Node.js packages:

```bash
npm install
```

> 🛠️ **Note on Patch Files**
> If you need to apply custom patches to npm modules (e.g., based on the `/patches` folder), first modify the local files as needed, then run:

```bash
npx patch-package [package-name]
```

Patches will be automatically applied every time you run `npm install`.

### 3. Set Up Python Environment

Create a virtual environment with Python 3.10 using Anaconda:

```bash
conda create -n mc python=3.10
conda activate mc
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### 4. Launch Minecraft

1. Open **Minecraft Java Edition**, version **1.21.1**
2. Create or load a world
3. Open the world to LAN using **port `55916`**

> ⚠️ You can use the ports other than `55916`, as long as it is open and match the `settings.json`.

### 5. Configure LLM Providers

Edit the `model.json` file to include your LLM provider token.

### 6. Start the Bot System

Once everything is configured, start the agent system:

```bash
python main.py
```

You should see the AI agent(s) connect and say "Hi, I am [bot's name]!" within your Minecraft world!

## Tutorials 

- [How to Create The Customized Plugins.](https://github.com/aeromechanic000/minecraft-ai-python/blob/main/tutorials/create_customized_plugins.md)

## FAQs
TBC.

## Documentation

More detailed information of Minecraft AI-Python can be found in the [Documentation](https://github.com/aeromechanic000/minecraft-ai-python/tree/main/doc).

## Citation
```
@misc{minecraft_ai_2025,
    author = {Minecraft AI},
    title = {Minecraft AI: Toward Embodied Turing Test Through AI Characters},
    year = {2025},
    url = {https://github.com/aeromechanic000/minecraft-ai-python}
}
```
