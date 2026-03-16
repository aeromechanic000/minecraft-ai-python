# <img src="https://s2.loli.net/2025/04/18/RWaFJkY4gSDLViy.png" alt="Minecraft AI" width="36" height="36"> Minecraft AI-Python: An Open Framework for Building Embodied AI in Minecraft

Minecraft AI-Python is a modular framework designed to support the creation and customization of AI Characters (AICs) within Minecraft environments. It provides a stable and extensible interface for perception, action, communication, memory, and reflection—enabling complex individual and multi-agent behaviors.

**The Embodied Turing Test** rather than asking "Can machines think?", Minecraft AI invites a new question for the generative AI era: Can machines play with us? Through open-ended interaction, emergent behaviors, and shared creativity, we explore whether AI can truly engage as a companion—not just in conversation, but in fun, imagination, and collaborative world-building.

> The [Minecraft AI Emobodied Benchmark](https://minecraft-ai-embodied-benchmark.megrez.plus/) Benchmark is a hierarchical evaluation framework designed to measure the embodied intelligence of AI agents in Minecraft. It organizes all in-game advancements into progressive levels, allowing researchers and developers to assess an agent’s cognitive and interactive abilities — from basic survival skills to complex multi-step planning and collaboration. Each level represents a milestone in autonomy, perception, and reasoning within a persistent, open-ended environment, providing a structured path for developing and comparing Minecraft-based AI systems.

This project is part of the broader Minecraft AI ecosystem. While the original [Minecraft AI](https://github.com/aeromechanic000/minecraft-ai) project focuses on a JavaScript-based infrastructure with integrated components, minecraft-ai-python emphasizes simplicity, flexibility, and rapid development in Python. It is ideal for educational experiments, prototyping research ideas, and custom agent development by individual contributors.

More detailed information can be found in [Minecraft AI Whitepapers and Technical Reports](https://github.com/aeromechanic000/minecraft-ai-whitepaper).

- [Minecraft AI: Toward Embodied Turing Test Through AI Characters](https://github.com/aeromechanic000/minecraft-ai-whitepaper/blob/main/whitepapers/minecraft_ai_whitepaper-toward_embodied_turing_test_through_ai_characters.pdf)

🧜 **Meet Max**, our new AI assistant for the Minecraft AI community! Ask questions, get started with AIC profiles, or explore tutorials — Max is here to help: [Max@MinecraftAI](https://www.coze.com/s/ZmFp9aCtM/)

🐦 Follow us on Twitter: [https://x.com/aeromechan71402](https://x.com/aeromechan71402)

🦾 Minecraft AI-Python is under development, more functions are added and optimized. If you have any question, welcome to join the our Discord server for more communications!

<a href="https://discord.gg/RKjspnTBmb" target="_blank"><img src="https://s2.loli.net/2025/04/18/CEjdFuZYA4pKsQD.png" alt="Official Discord Server" width="180" height="32"></a>

---

## 🖼️ Showcases 

<table>
<tr>
    <td><a href="https://www.youtube.com/watch?v=9phN6OWPmKg" target="_blank"><img src="https://s2.loli.net/2025/04/09/Kk35BEwvVlUuq9C.png" alt="Minecraft AI-Python: LLM-Driven Minecraft Agents in Python" width="380" height="220"></a></td>
    <td><img src="https://s2.loli.net/2025/04/09/CKwbHroZaj4xJSU.gif" alt="Minecraft AI-Python: LLM-Driven Minecraft Agents in Python" width="380" height="220"></td>
</tr>
</table>

---

## 🧠 Design Philosophy: Cognitive Metabolism

Traditional AI agents operate on a **Linear Execution** model: they wait for input, process it, and produce output. This works well for chatbots, but falls short for embodied agents that should feel "alive" in a persistent world.

Minecraft AI-Python introduces **Cognitive Metabolism** — a cyclic model where the agent continuously thinks, plans, and acts, even without player input.

### From Linear to Cyclic

```
Traditional Agent:          Cognitive Metabolism:
                            ┌─────────────────────┐
Input → Process → Output    │   IDLE → REFLECT    │
                            │     ↑         ↓     │
                            │     ACT   ←  PLAN   │
                            └─────────────────────┘
```

Instead of being reactive-only, the agent proactively generates its own goals, reflects on its situation, and takes initiative — much like a living creature.

### Core Principles

**1. Emergent Identity**

The agent's personality isn't just a prompt — it's a seed that grows into a unique identity. If `longterm_thinking` is empty, the agent generates its own aspirations from the profile during the "Foundational Reflection" on first spawn. This identity then influences all future decisions, creating consistency and depth.

**2. Handshake Protocol**

Autonomy without alignment is chaos. When the agent wants to do something self-driven, it announces its intent:

> "[Proposal] I want to explore the caves to the north. I'll proceed in 30 seconds unless you have other plans."

This creates a collaborative dynamic: the agent takes initiative but remains responsive to player direction. Any player message cancels the proposal, keeping the human in the loop.

**3. Persistent Memory & Goals**

The agent remembers past interactions, maintains relationships with players, and tracks long-term goals. If interrupted (e.g., server restart), it resumes where it left off:

> "I'm resuming: building the farmhouse foundation."

This persistence creates the illusion of a continuous conscious experience.

**4. Reflective Self-Improvement**

Through periodic self-reflection, the agent:
- Summarizes recent experiences into memory
- Updates its understanding of player relationships
- Adjusts its `longterm_thinking` based on significant events
- Derives lessons from successes and failures

This isn't just memory — it's learning and character development.

### Why This Matters

For the **Embodied Turing Test**, the question isn't "Can AI think?" but "Can AI play with us?" A true gaming companion should:

- **Take initiative** — not just wait for commands
- **Have personality** — consistent behavior that reflects a unique character
- **Stay aligned** — autonomous but not uncontrolled
- **Remember and grow** — relationships and skills that develop over time

Cognitive Metabolism is our approach to creating agents that feel alive — not just intelligent, but present.

---

## How to Contribute  

We wholeheartedly welcome you to contribute to the Minecraft AI project! Your contributions play a crucial role in shaping this project into a robust and versatile platform for the community.

### Submitting Code via Pull Requests (PRs)
The primary way to contribute code is through Pull Requests. When creating a PR, please adhere to the general best practices for PRs. Keep each PR focused on a specific issue or feature, and limit the scope of changes to a manageable size. This approach facilitates a smoother review process and enables quicker merging of your contributions. It ensures that our reviewers can thoroughly assess the changes without being overwhelmed by excessive code modifications.

### Code Structure and Compatibility Policies
Our goal is to establish Minecraft AI as a foundational platform in the community, empowering users to build innovative projects and drive the development of intelligent and engaging AI characters within the game. To achieve this, we have specific policies regarding the codebase:

- **Core and Underlying Code:** For the core implementation and underlying code, as well as the environment setup, we aim to maintain simplicity and focus on essential, indispensable features. Only changes that clearly enhance the performance across all scenarios and address bugs or deficiencies in the underlying code will be considered for merge after careful review.
- **Optional Features as Plugins:** Any features that are not universally applicable to all scenarios, especially those that can be optionally enabled or disabled at runtime, should be implemented as plugins. Before submitting a plugin, please ensure that it has been thoroughly tested to guarantee its proper functionality. Additionally, refrain from modifying any files outside the plugin's scope, including presetting the plugin's default configuration in the settings. Each plugin should include a README file that clearly outlines how to enable the plugin and any additional parameters required in the bot profile or other relevant areas to ensure optimal performance.

## Community Engagement and Alternative Contribution Methods
We encourage active communication within the community. If you encounter any issues or have ideas for improvements, feel free to discuss them with us first. We also support alternative ways of contributing, such as forking the repository or creating a separate repository for your plugins. Even if you choose not to submit your plugins to our main code repository, we are more than happy to collaborate and help promote third-party plugins through the Minecraft AI community, ensuring that all players can enjoy a richer gaming experience with enhanced features.
We look forward to your valuable contributions and the exciting possibilities they bring to the Minecraft AI project!

---

## 🚀 Quick Start 

This guide will walk you through setting up and running the `minecraft-ai-python` system.

### 1. Clone the Repository

Clone this repository into your working directory:

```bash
git clone https://github.com/aeromechanic000/minecraft-ai-python.git
cd minecraft-ai-python
```

Make sure you're in the `minecraft-ai-python` directory before continuing.

### 2. Install Prerequisites

#### 2.1 Install Node Modules

From the root of the `minecraft-ai` directory, install the required Node.js packages:

```bash
npm install
```

This will install all dependencies into the `node_modules` directory.

> 💡 **Note on Patches**
> If you plan to apply patches (e.g., from the `/patches` directory), first make your changes to the local dependency, then run:
>
> ```bash
> npx patch-package [package-name]
> ```
>
> These patches will be automatically re-applied on every `npm install`.

💁‍♂️ **Common Setup Issues**

Some devices may not support the latest `Node.js` version. If you see installation errors due to incompatible packages:

* Consider switching to Node.js **v18**, which is broadly compatible.
* Use a tool like [`nvm`](https://github.com/nvm-sh/nvm) (Linux/macOS) or [`nvm-windows`](https://github.com/coreybutler/nvm-windows) to manage multiple Node.js versions.

If individual packages fail to install, you can try:

* Installing them manually:

  ```bash
  npm install [package-name]
  ```
* Or using a pre-downloaded package: see [Use a Local Node Package](./tutorials/use_a_local_node_package.md)

#### 2.2 Install Python Modules

We recommend using `uv` for fast Python package management:

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv
```

Then create the virtual environment and install dependencies:

```bash
uv sync
```

This creates a `.venv` directory and installs all dependencies from `pyproject.toml`.

**Alternative (pip/conda):**

If you prefer traditional methods:

```bash
# Using conda
conda create -n mc python=3.13
conda activate mc
pip install javascript json5 requests fastapi uvicorn ultralytics torch Pillow

# Or using venv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install javascript json5 requests fastapi uvicorn ultralytics torch Pillow
```

#### 2.3 Install Minecraft Client

1. Download and install [Minecraft Launcher](https://www.minecraft.net/en-us/about-minecraft).
2. Minecraft AI supports **Minecraft Java Edition up to version 1.21.1**.
3. Launch Minecraft, create a world in the supported version, and open it to LAN (e.g., port `55916`).

### 3. Configure `settings.json`

Edit `settings.json` with the correct game connection settings:

```json
{
  "minecraft_version": "1.21.1",
  "host": "127.0.0.1",
  "port": 55916,
  "auth": "offline"
}
```

* `minecraft_version`: match your client version
* `host`: usually `localhost` or your machine’s IP
* `port`: must match the LAN world port

### 4. Create and Configure Bot Profiles

A bot profile defines an AI character's name, personality, and backend model. Set the profiles to activate in `settings.json`:

```json
"agents": ["./profiles/max.json"]
```

Here's a minimal example of `profiles/max.json`:

```json
{
    "username": "Max",
    "profile": "You are a smart Minecraft agent following your own heart...",
    "longterm_thinking": "I aim to become a reliable builder and problem-solver...",
    "self_driven_thinking_timer": 1000,
    "proposal_grace_period": 30,
    "resume_task_on_spawn": false,
    "skin": {"file": "./skins/max.png"},
    "llm": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key": "env:OPENAI_API_KEY"
    },
    "modes": {
        "self_preservation": true,
        "unstuck": true,
        "cowardice": false,
        "self_defense": true,
        "cheat": false
    },
    "cerebellum": {
        "narrate_behavior": false
    }
}
```

**Profile Configuration Fields:**

| Field | Description |
|-------|-------------|
| `username` | Bot's in-game name |
| `profile` | Personality description |
| `longterm_thinking` | Long-term goals. **Can be empty** - will be auto-generated from profile on first spawn |
| `self_driven_thinking_timer` | Ticks between idle reflections. When `null`, only disables idle reflection (action completion and player message reflection still work) |
| `proposal_grace_period` | Seconds to wait before executing autonomous actions (default: 30) |
| `resume_task_on_spawn` | Resume unfinished tasks when bot reconnects (default: false) |
| `skin` | Bot skin configuration: `{"file": "path/to/skin.png"}` |
| `modes` | Behavioral mode configuration (see below) |
| `cerebellum` | Reflex system configuration (see below) |

🛎️ **It is recommended** to set `self_driven_thinking_timer` to an integer such as `100` or `1000`.

**Reflection Triggers:**
- **Action completion** - Always triggers reflection when a goal is completed or failed
- **Player message** - Always triggers reflection when receiving a message while idle
- **Idle timer** - Only triggers if `self_driven_thinking_timer` is not `null`

When `self_driven_thinking_timer` is **`null`**: The bot will NOT autonomously reflect while idle, but WILL reflect when finishing tasks or receiving player messages.

When `self_driven_thinking_timer` is **not `null`**: The bot will also reflect autonomously after the timer expires while idle.

The timer value represents the number of laps the bot should wait before idle reflection. A lap refers to one interval between two consecutive "time" events in the Mineflayer framework, which occurs approximately every `20` game ticks.
Since there are about `10,000` ticks per hour in Minecraft, you can estimate how long each interval lasts in real-world time by doing the math based on your `self_driven_thinking_timer` value.

🧠 **Identity Generation**: If `longterm_thinking` is empty or not provided, the agent will automatically generate its long-term goals from the profile on first spawn. This makes the agent "come alive" with derived aspirations that match its personality.

🤝 **Handshake Protocol**: When the agent wants to perform autonomous actions (self-driven tasks), it announces its intent and waits for the `proposal_grace_period` before executing. Players can interrupt by sending any message. This keeps the agent aligned with player intentions while still being proactive.

### Behavioral Modes

The bot has a reactive behavioral modes system that responds immediately to urgent situations. Configure modes in the profile:

```json
{
    "modes": {
        "self_preservation": true,
        "unstuck": true,
        "cowardice": false,
        "self_defense": true,
        "cheat": false
    }
}
```

**Available Modes:**

| Mode | Default | Description |
|------|---------|-------------|
| `self_preservation` | ON | Respond to drowning, burning, and low health |
| `unstuck` | ON | Get unstuck when blocked for too long |
| `cowardice` | OFF | Run away from enemies (alternative to self_defense) |
| `self_defense` | ON | Attack nearby hostile enemies |
| `cheat` | OFF | Use cheats for instant block placement |

- **Reactive**: Modes run every tick (~1 second) for immediate response to urgent situations
- **Interruptible**: Modes like `self_preservation` and `self_defense` can interrupt any ongoing action
- **Web Monitor**: Mode states are displayed and can be toggled in real-time through the web interface

### Cerebellum (Reflex System)

The Cerebellum is a high-frequency reflex system that handles automatic responses. It runs every tick and provides immediate reactive behaviors without LLM calls.

Configure it in the profile:

```json
{
    "cerebellum": {
        "narrate_behavior": false
    }
}
```

**Cerebellum Configuration:**

| Field | Default | Description |
|-------|---------|-------------|
| `narrate_behavior` | `false` | If `true`, prints attack completion logs to console |

The Cerebellum works alongside the modes system:
- **Self-preservation reflexes**: Escape fire, lava, surface when drowning
- **Self-defense reflexes**: Attack nearby hostile entities
- **Attack cooldown**: 8-second cooldown between self-defense attacks on the same target

### Web Viewer (First-Person Camera)

You can enable a web-based viewer to see what the bot sees in real-time. Add these fields to your bot profile:

```json
{
    "viewer_port": 3000,
    "viewer_first_person": true,
    "viewer_distance": 6
}
```

**Viewer Configuration:**

| Field | Description |
|-------|-------------|
| `viewer_port` | Port for the web viewer (e.g., 3000) |
| `viewer_first_person` | Set to `true` for first-person view |
| `viewer_distance` | Render distance in chunks (default: 6) |

After starting the bot, open `http://localhost:3000` in your browser to see the bot's view.

### Web Monitor

The Web Monitor provides a browser-based dashboard to view bot status, toggle behavioral modes, and monitor activity in real-time.

Enable it in `settings.json`:

```json
{
    "web_monitor": {
        "enabled": true,
        "port": 8080,
        "state_write_interval_ms": 500,
        "viewer_enabled": true
    }
}
```

**Web Monitor Configuration:**

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | Enable/disable the web monitor |
| `port` | `8080` | Port for the web interface |
| `state_write_interval_ms` | `500` | How often to update bot state |
| `viewer_enabled` | `true` | Enable/disable 3D world viewer in monitor |

After starting the bot, open `http://localhost:8080` in your browser to access the monitor.

**Features:**
- View all connected bots and their status
- See bot health, hunger, position, and inventory
- Toggle behavioral modes in real-time
- Monitor current goals and actions
- 3D world viewer (when `viewer_enabled` is true)

**Prerequisites:**
- Python dependencies: `fastapi`, `uvicorn`

Install dependencies:
```bash
pip install fastapi uvicorn
# or with uv
uv add fastapi uvicorn
```

### Vision System (Object Detection)

The Vision System allows the bot to "see" and understand its environment using multiple detection backends. Detected objects are included in the bot's decision-making context.

#### Supported Detectors

| Detector | Description | Best For |
|----------|-------------|----------|
| `yolo` | YOLOv8-based detection (default) | Minecraft players and mobs |
| `rtdetr` | RT-DETR object detection | General object detection |
| `vlm` | Vision Language Model | Rich scene understanding via API |

#### Enable Vision

Add the `vision` configuration to your bot profile:

```json
{
    "viewer_port": 3000,
    "viewer_first_person": true,
    "vision": {
        "enabled": true,
        "detector": "yolo",
        "model": "https://raw.githubusercontent.com/CHATDOO/Minecraft-YOLOv5/main/best.pt",
        "confidence_threshold": 0.3,
        "cache_ttl_seconds": 2,
        "max_saved_screenshots": 10
    }
}
```

**Vision Configuration:**

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | Enable/disable vision system |
| `detector` | `"yolo"` | Detector type: `yolo`, `rtdetr`, or `vlm` |
| `model` | (varies) | Model URL or path for yolo/rtdetr; API model name for vlm |
| `confidence_threshold` | `0.3` | Minimum confidence for detections (yolo/rtdetr only) |
| `cache_ttl_seconds` | `2` | Cache TTL to avoid redundant captures |
| `max_saved_screenshots` | `10` | Max screenshots to keep (0 = keep none) |
| `vlm` | `{}` | VLM-specific config (see below) |

**Prerequisites:**
- `viewer_port` must be set (required for screenshot capability)
- Python dependencies: `ultralytics`, `torch`, `Pillow` (included in `pyproject.toml`)

#### YOLO Detector (Default)

YOLO is the default detector, optimized for Minecraft entities:

```json
{
    "vision": {
        "enabled": true,
        "detector": "yolo",
        "model": "https://raw.githubusercontent.com/CHATDOO/Minecraft-YOLOv5/main/best.pt",
        "confidence_threshold": 0.3
    }
}
```

**Available YOLO Models:**

| Model | Description |
|-------|-------------|
| `https://raw.githubusercontent.com/CHATDOO/Minecraft-YOLOv5/main/best.pt` | Minecraft mobs & blocks (default) |
| `https://github.com/styalai/player-detection-on-Minecraft-with-YOLOv8/raw/main/...` | Player detection only |

#### RT-DETR Detector

General-purpose object detection:

```json
{
    "vision": {
        "enabled": true,
        "detector": "rtdetr",
        "model": "https://github.com/ultralytics/assets/releases/download/v0.0.0/rtdetr-l.pt",
        "confidence_threshold": 0.3
    }
}
```

**Available RT-DETR Models:**

| Model | Size | Description |
|-------|------|-------------|
| `rtdetr-l.pt` | ~64 MB | Large (recommended) |
| `rtdetr-x.pt` | ~130 MB | Extra large, most accurate |

> **Note:** RT-DETR is a general-purpose detector. Labels like "person" may represent players or mobs, not actual humans.

#### VLM Detector (Vision Language Model)

Rich scene understanding using LLM APIs:

```json
{
    "vision": {
        "enabled": true,
        "detector": "vlm",
        "model": "gpt-4o",
        "vlm": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "env:OPENAI_API_KEY",
            "prompt": "Describe what you see in this Minecraft scene..."
        }
    }
}
```

**VLM Configuration:**

| Field | Description |
|-------|-------------|
| `vlm.base_url` | API base URL (falls back to agent's `llm.base_url`) |
| `vlm.api_key` | API key (supports `env:VAR_NAME` prefix) |
| `vlm.prompt` | Custom prompt for vision analysis (optional) |

**First Run:**
When you first start a bot with vision enabled and the model isn't downloaded, you'll see:
```
[Vision] Model download required
  Model: best.pt
  Size: ~64 MB
  Available disk space: 50000 MB

  This model will be downloaded.
Download the vision model? [y/N]:
```

Type `y` to download, or `n` to start without vision.

**Vision in Action:**
When the bot makes decisions, it receives visual context like:
```
Here is what you see through your vision (objects detected in your current view):
- 1 cow (center-middle, confidence: 85%)
- 2 sheep (positions: left-middle, right-middle, avg confidence: 78%)
- 1 tree (center-top, confidence: 92%)
```

> 🔍 Explore more sample profiles in the `profiles/` directory.

### 5. Configure LLM Provider

The `llm` configuration in the bot profile supports any OpenAI-compatible API. You can configure:

- `base_url`: The API endpoint URL
- `model`: The model identifier
- `api_key`: Your API key (use `env:VAR_NAME` to read from environment variable)

#### Setting API Keys

You can set API keys directly or use environment variables:

```json
"llm": {
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o",
    "api_key": "env:OPENAI_API_KEY"
}
```

Then export the environment variable:

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

> 🔐 **Best Practice**: Use environment variables (`env:VAR_NAME`) instead of hardcoding keys in profile files.

#### Tag-Specific Provider Configuration

You can configure different LLM providers for different tasks by adding tag-specific overrides:

```json
{
    "llm": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key": "env:OPENAI_API_KEY",
        "memory": {
            "model": "gpt-4o-mini"
        },
        "reflection": {
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "model": "doubao-1-5-pro-32k-250115",
            "api_key": "env:DOUBAO_API_KEY"
        },
        "decide": {
            "model": "gpt-4o"
        },
        "new_action": {
            "model": "gpt-4o"
        }
    }
}
```

Available tags:
- **`memory`**: Used for memory summarization tasks
- **`reflection`**: Used for self-driven thinking and reflection
- **`decide`**: Used for action decision making
- **`new_action`**: Used for generating custom Python actions (coding tasks)

Each tag inherits from the default `llm` config and only overrides the fields you specify.

#### Supported Providers and Base URLs

All providers use OpenAI-compatible APIs. Just set the `base_url` and `model` in your profile:

<table>
<tr>
    <td> <b>Provider</b> </td>
    <td> <b>Base URL</b> </td>
    <td> <b>Environment Variable</b> </td>
    <td> <b>Example Models</b> </td>
</tr>
<tr>
    <td> OpenAI </td>
    <td> <code>https://api.openai.com/v1</code> </td>
    <td> <code>OPENAI_API_KEY</code> </td>
    <td> gpt-4o, gpt-4o-mini <br> <a href="https://platform.openai.com/docs/models">full list</a> </td>
</tr>
<tr>
    <td> Anthropic </td>
    <td> <code>https://api.anthropic.com/v1</code> </td>
    <td> <code>ANTHROPIC_API_KEY</code> </td>
    <td> claude-sonnet-4-20250514, claude-opus-4-20250514 <br> <a href="https://docs.anthropic.com/en/docs/about-claude/models/overview">full list</a> </td>
</tr>
<tr>
    <td> DeepSeek </td>
    <td> <code>https://api.deepseek.com</code> </td>
    <td> <code>DEEPSEEK_API_KEY</code> </td>
    <td> deepseek-chat, deepseek-reasoner <br> <a href="https://api-docs.deepseek.com/quick_start/pricing">full list</a> </td>
</tr>
<tr>
    <td> Doubao </td>
    <td> <code>https://ark.cn-beijing.volces.com/api/v3</code> </td>
    <td> <code>DOUBAO_API_KEY</code> </td>
    <td> doubao-1-5-pro-32k-250115 <br> <a href="https://www.volcengine.com/docs/82379/1330310">full list</a> </td>
</tr>
<tr>
    <td> Qwen </td>
    <td> <code>https://dashscope.aliyuncs.com/compatible-mode/v1</code> </td>
    <td> <code>QWEN_API_KEY</code> </td>
    <td> qwen-max, qwen-plus <br> <a href="https://help.aliyun.com/zh/model-studio/getting-started/models">full list</a> </td>
</tr>
<tr>
    <td> Google Gemini </td>
    <td> <code>https://generativelanguage.googleapis.com/v1beta</code> </td>
    <td> <code>GEMINI_API_KEY</code> </td>
    <td> gemini-2.0-flash <br> <a href="https://ai.google.dev/gemini-api/docs/models">full list</a> </td>
</tr>
<tr>
    <td> OpenRouter </td>
    <td> <code>https://openrouter.ai/api/v1</code> </td>
    <td> <code>OPENROUTER_API_KEY</code> </td>
    <td> openai/gpt-4o, anthropic/claude-sonnet-4 <br> <a href="https://openrouter.ai/models">full list</a> </td>
</tr>
<tr>
    <td> <a href="https://pollinations.ai/">Pollinations</a> </td>
    <td> <code>https://text.pollinations.ai/openai</code> </td>
    <td> <b>NOT REQUIRED</b> </td>
    <td> openai-large, gemini, deepseek <br> <a href="https://text.pollinations.ai/models">full list</a> </td>
</tr>
<tr>
    <td> <a href="https://ollama.com/">Ollama</a> </td>
    <td> <code>http://127.0.0.1:11434/v1</code> </td>
    <td> <b>NOT REQUIRED</b> </td>
    <td> llama3.2, mistral <br> <a href="https://ollama.com/library">full list</a> </td>
</tr>
</table>

> **Note:** All providers use the standard OpenAI `/chat/completions` endpoint. The `call_openai_compatible_api` function handles this automatically.

#### Example Configurations

**OpenAI:**
```json
"llm": {
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o",
    "api_key": "env:OPENAI_API_KEY"
}
```

**Anthropic:**
```json
"llm": {
    "base_url": "https://api.anthropic.com/v1",
    "model": "claude-sonnet-4-20250514",
    "api_key": "env:ANTHROPIC_API_KEY"
}
```

**DeepSeek:**
```json
"llm": {
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "api_key": "env:DEEPSEEK_API_KEY"
}
```

**Doubao (with cheaper model for memory):**
```json
"llm": {
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model": "doubao-1-5-pro-32k-250115",
    "api_key": "env:DOUBAO_API_KEY",
    "memory": {
        "model": "doubao-1-5-lite-32k-250115"
    }
}
```

**Pollinations (free, no API key required):**
```json
"llm": {
    "base_url": "https://text.pollinations.ai/openai",
    "model": "openai-large",
    "api_key": ""
}
```

**Ollama (local, no API key required):**
```json
"llm": {
    "base_url": "http://127.0.0.1:11434/v1",
    "model": "llama3.2",
    "api_key": ""
}
```

---

### 6. Start the Bot System

Once everything is configured, start the agent system:

```bash
python main.py
```

You should see the AI agent(s) connect and say "Hi, I am [bot's name]!" or ("Found tasks not finished") within your Minecraft world!

### Common Errors

#### `ECONNRESET` (Code `-4077`)

This usually means your `minecraft_version` setting does not match the running game. Double-check that you are using:

* Minecraft Java Edition version `1.21.1`
* And the corresponding value in `settings.json`:

```json
"minecraft_version": "1.21.1"
```

**Recommended Fix**

* Use **Minecraft Java Edition `1.21.1`**
* Ensure the `minecraft_version` field in `settings.json` exactly matches the version of your running Minecraft world:

```json
"minecraft_version": "1.21.1"
```

<!-- ## Documentation -->
<!--  -->
<!-- More detailed information of Minecraft AI-Python can be found in the [Documentation](https://github.com/aeromechanic000/minecraft-ai-python/tree/main/doc). -->

## Tutorials 

Want to see how it all works? Check out the [Tutorials](./tutorials) for more detailed usage guides and examples.

## Citation

```
@misc{minecraft_ai_2025,
    author = {Minecraft AI},
    title = {Minecraft AI: Toward Embodied Turing Test Through AI Characters},
    year = {2025},
    url = {https://github.com/aeromechanic000/minecraft-ai-whitepaper}
}
```
