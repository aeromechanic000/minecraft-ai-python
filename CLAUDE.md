# Minecraft AI-Python: Developer Guide

This document summarizes the key requirements and setup instructions for the Minecraft AI-Python project, with a focus on using `uv` for Python package management.

## Project Overview

Minecraft AI-Python is a modular framework for building AI Characters (AICs) in Minecraft. It uses Python to control Minecraft bots via a JavaScript bridge (JSPyBridge/mineflayer), enabling LLM-driven agents to interact with the game world.

**Key Components:**
- **Python 3.9+** - Main runtime for AI agent logic
- **Node.js** - Runs mineflayer for Minecraft protocol communication
- **JSPyBridge** - Python-JavaScript interop package (v1.2.6+)
- **LLM Provider** - OpenAI, Anthropic, Ollama, or compatible API

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                             │
│                    (Process Manager)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ├─────────────────┐
                          │                 │
                    ┌─────▼─────┐    ┌────▼─────┐
                    │  agent.py │    │ agent.py │  (Multiprocess)
                    └─────┬─────┘    └────┬─────┘
                          │                │
              ┌───────────┴────────────────┴──────────┐
              │         Python Modules                  │
              │  - agent.py, memory.py, world.py       │
              │  - actions.py, skills.py, model.py     │
              └───────────────────┬────────────────────┘
                                  │
              ┌───────────────────┴────────────────────┐
              │      JSPyBridge (javascript package)   │
              │      require('mineflayer', ...)        │
              └───────────────────┬────────────────────┘
                                  │
              ┌───────────────────┴────────────────────┐
              │         Node.js Runtime                │
              │  - mineflayer (Minecraft bot)          │
              │  - mineflayer-pathfinder               │
              │  - mineflayer-collectblock             │
              │  - mineflayer-pvp, -auto-eat, etc.     │
              └───────────────────┬────────────────────┘
                                  │
              ┌───────────────────┴────────────────────┐
              │      Minecraft Server (1.21.1)         │
              └────────────────────────────────────────┘
```

## Cognitive Metabolism: Proactive Agent Model

The agent operates on a **Cyclic Metabolism** model rather than a linear request-response pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│                    COGNITIVE METABOLISM CYCLE                    │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
    ┌─────────┐         ┌─────────┐         ┌─────────┐
    │  IDLE   │ ──────► │ REFLECT │ ──────► │  PLAN   │
    └─────────┘         └─────────┘         └─────────┘
         ▲                    │                    │
         │                    │                    ▼
         │                    │              ┌─────────┐
         │                    └─────────────►│   ACT   │
         │                                   └─────────┘
         │                                         │
         └─────────────────────────────────────────┘
```

### Key Components

1. **Identity Generation**: If `longterm_thinking` is empty, the agent generates its identity from the profile on first spawn using the reflection LLM.

2. **Idle Detection**: Agent is truly idle when:
   - No active goal (`current_goal is None`)
   - No pending requests (`request_queue` is empty)
   - No active work (`working_process is None`)

3. **Reflection Triggers**:
   - **Action completion** - Always triggers when goal completes/fails
   - **Player message** - Always triggers when receiving message while idle
   - **Idle timer** - Only triggers if `self_driven_thinking_timer` is not `null`

4. **Proposal/Handshake Protocol**: For autonomous actions (not triggered by player):
   - Agent announces intent: `"[Proposal] I want to X. I'll proceed in N seconds unless you have other plans."`
   - Waits for `proposal_grace_period` seconds (default: 30)
   - Player can interrupt by sending any message
   - If no interruption, action executes

5. **Player Interrupt**: Any player message cancels pending proposals immediately.

6. **Goal Persistence**: Goals persist across restarts. On restart, agent announces: `"I'm resuming: {target}"`

### Request Priority Queue

| Priority | Source | Behavior |
|----------|--------|----------|
| 1 (HIGH) | Player messages | Immediate processing |
| 2 (MEDIUM) | Self-reflection, idle reflection | Deferred if busy |
| 3 (LOW) | Goal continuation | Uses handshake protocol |

## Key Requirements

### Python Dependencies (from pyproject.toml)

```toml
[project]
name = "minecraft-ai-python"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = [
    "javascript>=1!1.2.6",   # Python-JavaScript bridge
    "json5>=0.13.0",         # JSON5 parser for configs
    "requests>=2.32.5",      # HTTP client for LLM APIs
    "fastapi>=0.109.0",      # Web monitor server
    "uvicorn>=0.27.0",       # ASGI server
    "ultralytics>=8.0.0",    # Vision: RT-DETR object detection
    "torch>=2.0.0",          # Vision: PyTorch backend
    "Pillow>=10.0.0",        # Vision: Image processing
]
```

### Node.js Dependencies

- `mineflayer@^4.26.0` - Minecraft bot framework
- `minecraft-data@^3.85.0` - Minecraft version data
- `mineflayer-pathfinder@^2.4.5` - Pathfinding plugin
- `mineflayer-collectblock@^1.6.0` - Block collection plugin
- `mineflayer-pvp@^1.3.2` - Combat plugin
- `mineflayer-auto-eat@^3.3.6` - Auto-eat plugin
- `mineflayer-armor-manager@^2.0.1` - Armor management
- `prismarine-viewer@^1.32.0` - World viewer
- And more (see package.json)

### Configuration Files

| File | Purpose |
|------|---------|
| `settings.json` | Global settings (Minecraft connection, agent list) |
| `profiles/*.json` | Individual agent profiles (personality, LLM config) |

### Bot Profile Configuration

Each bot profile in `profiles/*.json` uses the `llm` configuration format:

```json
{
    "username": "Max",
    "profile": "Bot personality description...",
    "longterm_thinking": "Long-term goals...",
    "self_driven_thinking_timer": 1000,
    "proposal_grace_period": 30,
    "llm": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key": "env:OPENAI_API_KEY"
    }
}
```

**Key Configuration Fields:**

| Field | Description |
|-------|-------------|
| `username` | Bot's in-game name |
| `profile` | Personality description (used for identity generation if `longterm_thinking` is empty) |
| `longterm_thinking` | Long-term goals and aspirations. **Can be empty** - will be auto-generated from profile on first spawn |
| `self_driven_thinking_timer` | Ticks between autonomous reflections when idle. When `null`, only disables idle reflection (action completion and player message reflection still work) |
| `proposal_grace_period` | Seconds to wait for player response before executing autonomous actions (default: 30) |
| `modes` | Behavioral mode configuration (see below) |

**Tag-specific provider configuration:**

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

Available tags: `memory`, `reflection`, `decide`, `new_action`

### Behavioral Modes Configuration

The bot has a reactive behavioral modes system that responds immediately to urgent situations. Modes are configured in the profile:

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
| `self_preservation` | ON | Respond to drowning, burning, and damage at low health |
| `unstuck` | ON | Get unstuck when blocked for too long |
| `cowardice` | OFF | Run away from enemies (alternative to self_defense) |
| `self_defense` | ON | Attack nearby enemies |
| `cheat` | OFF | Use cheats for instant block placement |

**Mode Behavior:**
- Modes run every tick (~1 second) to provide immediate reactive responses
- Modes with `interrupts: ['all']` can interrupt any ongoing action
- `cowardice` is OFF by default so bots fight rather than flee
- Proactive behaviors (hunting, item collecting) are handled by the reflection system, not modes

### Cerebellum Configuration

The Cerebellum is the reflex system that handles automatic responses. It can be configured in the profile:

```json
{
    "cerebellum": {
        "narrate_behavior": false
    }
}
```

**Available Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `narrate_behavior` | `false` | If `true`, prints attack completion logs to console |

**Attack Cooldowns:**
- Self-defense attacks have an 8-second cooldown between triggers
- Cowardice flee has a 5-second cooldown
- Entities recently attacked are tracked for 5 seconds to prevent repeated attacks on the same target

**Web Monitor Integration:**
- Mode states are displayed in the web monitor when a bot is selected
- Modes can be toggled in real-time through the web interface
- Changes are picked up by the bot on the next tick

---

## Vision System

The Vision System provides visual perception capabilities using multiple detection backends. It allows the bot to "see" its environment and include visual observations in its decision-making context.

### Supported Detectors

| Detector | Description | Best For |
|----------|-------------|----------|
| `yolo` | YOLOv8-based detection | Minecraft players and mobs (default) |
| `rtdetr` | RT-DETR object detection | General object detection |
| `vlm` | Vision Language Model | Rich scene understanding via API |

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      VISION SYSTEM FLOW                          │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Model Manager  │  │     Camera      │  │  VisionSystem   │
│  (main.py)      │  │  (camera.py)    │  │  (vision.py)    │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         │  1. Check model    │                    │
         │     exists         │                    │
         │                    │                    │
         │  2. Prompt for     │                    │
         │     download       │                    │
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Detector      │
                    │  (yolo/rtdetr/  │
                    │   vlm)          │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ get_vision_ctx  │
                    │  1. Capture     │
                    │  2. Detect/     │
                    │     Analyze     │
                    │  3. Format      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ build_decide_   │
                    │ prompt          │
                    │ + Visual Obs    │
                    └─────────────────┘
```

### Components

#### 1. vision.py - Core Vision Module

Contains all vision-related functionality with a modular detector architecture:

**Detector Classes:**
- `YOLODetector` - Minecraft-specific YOLOv8 detection (default)
- `RTDETRDetector` - General-purpose RT-DETR object detection
- `VLMDetector` - Vision Language Model analysis via API

**Model Management Functions:**
- `is_model_downloaded()` - Check if model exists
- `check_and_prepare_model()` - Handle model download with user confirmation
- `check_vision_requirements()` - Check all agent profiles for vision needs
- `download_model()` - Download model from registry
- `create_detector()` - Factory function to create detector instances

**VisionSystem Class:**
- `_init_detector()` - Initialize detector based on config
- `_init_camera()` - Initialize camera via JSPyBridge
- `capture_screenshot()` - Capture first-person view
- `get_vision_context()` - Main entry point with caching

#### 2. camera.py - Python Camera Module

Encapsulates JSPyBridge calls to JavaScript rendering libraries:
- Uses `prismarine-viewer` for world rendering
- Uses `node-canvas-webgl` for canvas creation
- Uses `three.js` for WebGL rendering
- Captures JPEG screenshots from bot's first-person view

### Available Models

The `model` field should be a URL to download the model, or a local path to an existing model file.

**Default Model URLs (used if `model` is not specified):**

| Detector | Default URL | Description |
|----------|-------------|-------------|
| `yolo` | `https://raw.githubusercontent.com/CHATDOO/Minecraft-YOLOv5/main/best.pt` | Minecraft mobs: cow, creeper, pig, villager, sheep, house |
| `rtdetr` | `https://github.com/ultralytics/assets/releases/download/v0.0.0/rtdetr-l.pt` | General object detection |
| `vlm` | (none - uses API) | Vision Language Model |

**Alternative Models:**

| Model Key | URL | Description |
|-----------|-----|-------------|
| `minecraft_yolov5_chatdoo` | `https://raw.githubusercontent.com/CHATDOO/Minecraft-YOLOv5/main/best.pt` | Minecraft mobs & blocks (default) |
| `minecraft_player_yolov8_styalai` | `https://github.com/styalai/player-detection-on-Minecraft-with-YOLOv8/raw/main/player_detection%20on%20minecraft%2004%20(gpu).pt` | Player detection only |
| `rtdetr_l` | `https://github.com/ultralytics/assets/releases/download/v0.0.0/rtdetr-l.pt` | RT-DETR Large (~64MB) |
| `rtdetr_x` | `https://github.com/ultralytics/assets/releases/download/v0.0.0/rtdetr-x.pt` | RT-DETR Extra Large (~130MB) |

**Custom Models:**

You can specify any custom model by providing its URL:

```json
{
    "vision": {
        "enabled": true,
        "detector": "yolo",
        "model": "https://your-server.com/path/to/your-model.pt"
    }
}
```

Or use a local file path:

```json
{
    "vision": {
        "enabled": true,
        "detector": "yolo",
        "model": "/path/to/your/local-model.pt"
    }
}
```

Models downloaded from URLs are cached in the `models/` directory.

### Configuration

Enable vision in bot profile:

```json
{
    "username": "Max",
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

**Vision Configuration Fields:**

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | Enable/disable vision system |
| `detector` | `"yolo"` | Detector type: `yolo`, `rtdetr`, or `vlm` |
| `model` | (varies) | For `yolo`/`rtdetr`: URL or local path to model file. For `vlm`: API model name |
| `confidence_threshold` | `0.3` | Minimum confidence for detections (yolo/rtdetr only) |
| `cache_ttl_seconds` | `2` | Cache TTL to avoid redundant captures |
| `max_saved_screenshots` | `10` | Max number of screenshots to keep (0 = keep none) |
| `vlm` | `{}` | VLM-specific config: `base_url`, `api_key`, `prompt` (vlm only) |

**VLM Configuration (optional):**

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

**Note:** For VLM, the `model` field is the API model name (e.g., "gpt-4o", "claude-3-opus-20240229"). If `vlm` section is not provided, the detector falls back to the agent's `llm` configuration.

**VLM Configuration Fields:**

| Field | Description |
|-------|-------------|
| `vlm.base_url` | API base URL (falls back to `llm.base_url`) |
| `vlm.api_key` | API key (supports `env:VAR_NAME` prefix) |
| `vlm.prompt` | Custom prompt for vision analysis (optional) |

**Prerequisites:**
- `viewer_port` must be set in profile
- Python dependencies: `ultralytics`, `torch`, `Pillow`
- For VLM: valid API key for the chosen provider

### Startup Flow

1. `main.py` checks all agent profiles for vision requirements
2. If model not downloaded (for yolo/rtdetr):
   - Shows model name, size, and available disk space
   - Prompts user for download confirmation
   - Downloads model if confirmed
   - Allows starting without model if declined
3. Agent starts with or without vision capability

### Runtime Behavior

- Vision context is added to LLM prompt during `handle_decide()`
- Results are cached to avoid redundant captures
- If model unavailable, logs warning once (no runtime download)
- Each detector formats output appropriately for LLM context

### Detector Output Formats

**YOLO:** "You see the following objects through your vision system. This uses a Minecraft-specific YOLO model trained to detect players and mobs."

**RT-DETR:** "You see the following objects through your vision system. **Important:** This uses a general-purpose object detector (not Minecraft-specific). Labels like 'person' may represent players or mobs..."

**VLM:** Returns rich natural language descriptions based on the configured prompt.

---

**Common base URLs:**

| Provider | Base URL |
|----------|----------|
| OpenAI | `https://api.openai.com/v1` |
| Anthropic | `https://api.anthropic.com/v1` |
| DeepSeek | `https://api.deepseek.com` |
| Doubao | `https://ark.cn-beijing.volces.com/api/v3` |
| Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| Pollinations | `https://text.pollinations.ai/openai` |
| Ollama | `http://127.0.0.1:11434/v1` | |

### Minecraft Version

- **Supported:** Minecraft Java Edition 1.21.1
- The `minecraft_version` in `settings.json` must match your running server

## Known Issues & Patches

### JSPyBridge Compatibility Fixes

As of February 2025, the JSPyBridge package (v1.2.6) has compatibility issues with newer mineflayer versions. Two patches are required:

**Patch 1: mineflayer version mismatch**
- Issue: mineflayer expects `minecraft-data` to have version 1.21.11, but only 1.21.10 exists
- Fix: Change `1.21.11` to `1.21.10` in testedVersions array

**Patch 2: Module resolution in deps.js**
- Issue: `$require()` doesn't resolve package entry points correctly
- Fix: Call `pm.resolve()` before `import()` in $require function

### Applying Patches

When using `uv`, the patches need to be applied to the `.venv` environment:

**After first run (when node_modules are created):**

```bash
# Find the version.js file and apply Patch 1
JSPY_PATH=".venv/lib/python3.9/site-packages/javascript/js/node_modules/mineflayer/lib"
sed -i '' 's/1\.21\.11/1.21.10/g' "$JSPY_PATH/version.js"

# Apply Patch 2 to deps.js
DEPS_PATH=".venv/lib/python3.9/site-packages/javascript/js/deps.js"
# Replace line 139 in deps.js:
# OLD: const mod = await import([newpath, ...path].join('/'))
# NEW: const resolvedPath = pm.resolve(newpath)
#      const mod = await import(resolvedPath.href)
```

**Note:** The patches are applied to the Python package's bundled node_modules (created on first use), not the project's local `node_modules`.

---

## Quick Start with `uv`

`uv` is a fast Python package manager written in Rust. It's recommended for managing this project's dependencies.

### 1. Install `uv`

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Create Project Environment

```bash
cd /Users/nil/Projects/minecraft-ai-python

# uv will automatically create/use .venv directory
uv sync
```

This creates a virtual environment and installs all dependencies from `pyproject.toml`.

### 2.5. Apply JSPyBridge Patches (Required)

The JSPyBridge package needs compatibility patches applied. Run the setup script:

```bash
./setup-uv.sh
```

Or apply manually:

```bash
# After the first run creates node_modules
JSPY_PATH=".venv/lib/python3.9/site-packages/javascript/js/node_modules/mineflayer/lib"
sed -i '' 's/1\.21\.11/1.21.10/g' "$JSPY_PATH/version.js"

# The deps.js patch is already applied to the .venv
```

**Note:** The version.js patch must be applied after the first run (when node_modules are auto-created by JSPyBridge).

### 3. Add Packages

```bash
# Add a new Python package
uv add requests

# Add a dev dependency
uv add --dev pytest

# Add from git
uv add git+https://github.com/user/repo.git
```

### 4. Run the Bot

```bash
# Option 1: Activate venv then run (recommended)
source .venv/bin/activate  # macOS/Linux
python main.py --agents ./profiles/max.json

# Option 2: Use uv run (includes python prefix)
uv run python main.py --agents ./profiles/max.json

# Option 3: Use full python path
.venv/bin/python main.py --agents ./profiles/max.json
```

### 5. Useful `uv` Commands

```bash
# List installed packages
uv pip list

# Update dependencies
uv lock --upgrade

# Install from requirements.txt
uv pip install -r requirements.txt

# Run Python in the project environment
uv python

# Run tests
uv run pytest

# Remove the virtual environment
uv venv --clear
```

### Environment Variables

For LLM API keys, use environment variables with the `env:` prefix in profiles:

```bash
# Set API keys in your shell
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Or use a .env file (add to .gitignore!)
echo 'OPENAI_API_KEY=sk-...' > .env
```

Then use with uv:

```bash
uv run --env-file .env main.py
```

---

## Project Structure

```
minecraft-ai-python/
├── main.py                 # Entry point, process manager
├── agent.py                # Core agent logic
├── memory.py               # Memory management
├── world.py                # World state and minecraft-data wrappers
├── actions.py              # Available actions
├── skills.py               # Skill definitions
├── model.py                # LLM interface
├── modes.py                # Behavioral modes system
├── utils.py                # Utilities
├── plugin.py               # Minecraft AI plugin base class
├── vision.py               # Vision system (RT-DETR-L object detection)
├── camera.py               # Camera module for screenshot capture
├── settings.json           # Global configuration
├── pyproject.toml          # Python dependencies
├── package.json            # Node.js dependencies (mineflayer plugins)
├── run.sh                  # Legacy conda startup script
├── profiles/               # Agent profiles
│   ├── max.json
│   └── ...
├── plugins/                # Minecraft AI plugins (Python)
│   ├── BuildWithBlueprint/
│   ├── Dance/
│   ├── ShootWithBowAndArrow/
│   └── Task/
├── monitor/                # Web monitor server
│   ├── server.py           # FastAPI server
│   └── templates/          # HTML templates
├── bots/                   # Bot history/memory
├── skins/                  # Bot skin files
└── patches/                # npm patch-package patches
```

## Plugin Systems

This project uses **two separate plugin systems** that serve different purposes:

### 1. Mineflayer Plugins (JavaScript/Node.js)

These are JavaScript plugins that extend the **mineflayer** bot framework. They handle low-level Minecraft bot behaviors and are loaded in `agent.py` via `bot.loadPlugin()`.

**Installed via:** `npm install` (see `package.json`)
**Location:** `node_modules/` and JSPyBridge's internal `node_modules/`
**Loaded in:** `agent.py` (lines 31-35)

**Examples:**
- `mineflayer-pathfinder` - Pathfinding and navigation
- `mineflayer-pvp` - Combat mechanics
- `mineflayer-collectblock` - Block collection
- `mineflayer-auto-eat` - Automatic food consumption
- `mineflayer-armor-manager` - Armor equipment management

**Code reference (agent.py:31-35):**
```python
self.bot.loadPlugin(pathfinder.pathfinder)
self.bot.loadPlugin(pvp.plugin)
self.bot.loadPlugin(collect_block.plugin)
self.bot.loadPlugin(auto_eat.loader)
self.bot.loadPlugin(armor_manager)
```

### 2. Minecraft AI Plugins (Python)

These are Python plugins that extend the **Minecraft AI** framework. They define custom behaviors, actions, and skills for AI agents. Each plugin inherits from the `Plugin` base class in `plugin.py`.

**Location:** `plugins/` directory
**Base class:** `plugin.py.Plugin`
**Loaded dynamically:** Based on agent profile configuration

**Examples:**
- `BuildWithBlueprint` - Build structures from blueprints
- `Dance` - Dance animations
- `ShootWithBowAndArrow` - Archery actions
- `Task` - Task management

**Plugin structure:**
```python
from plugin import Plugin

class MyPlugin(Plugin):
    def __init__(self, agent):
        super().__init__(agent)
        self.plugin_name = "MyPlugin"

    def get_actions(self):
        # Return list of custom actions
        return []

    def get_reminder(self):
        # Return reminder text for the LLM
        return "This plugin does X"
```

**Key Difference:**
- **Mineflayer plugins** add low-level bot capabilities (movement, combat, inventory)
- **Minecraft AI plugins** add high-level AI behaviors (building, tasks, custom actions)

---

## Common Issues

### ECONNREFUSED / ECONNRESET

**Cause:** Minecraft version mismatch between client and settings.

**Fix:**
1. Ensure Minecraft server is running version 1.21.1
2. Check `settings.json` has `"minecraft_version": "1.21.1"`
3. Verify port matches the LAN world port

### JSPyBridge Module Not Found

**Cause:** The Python `javascript` package uses its own bundled node_modules.

**Fix:** Install missing packages via npm in the Python package directory:
```bash
cd /opt/anaconda3/envs/mc/lib/python3.12/site-packages/javascript/js/
npm install mineflayer-collectblock
```

Or apply the deps.js patch mentioned above.

### Node.js Version Warnings

**Cause:** mineflayer 4.27.0+ requires Node.js >=22, but you have v20.

**Impact:** Non-critical - operations should work fine with v20.

**Optional Fix:** Upgrade Node.js if issues occur:
```bash
# Using nvm
nvm install 22
nvm use 22
```

---

## Development Workflow

### Creating a New Agent Profile

```bash
# Copy example profile
cp profiles/max.json profiles/my-agent.json

# Edit the profile
vim profiles/my-agent.json  # Set username, personality, model

# Run the new agent
uv run main.py --agents ./profiles/my-agent.json
```

### Creating a Minecraft AI Plugin

Minecraft AI plugins are Python modules that extend agent capabilities with custom actions and behaviors.

1. Create a new directory under `plugins/YourPlugin/`
2. Add `main.py` with your plugin class inheriting from `Plugin`
3. Import and enable in agent profiles

Example structure:
```
plugins/
└── MyPlugin/
    ├── main.py
    └── README.md (optional)
```

Example `main.py`:
```python
from plugin import Plugin

class MyPlugin(Plugin):
    def __init__(self, agent):
        super().__init__(agent)
        self.plugin_name = "MyPlugin"
        self.reminder = "This plugin helps with X"

    def get_actions(self):
        # Return list of custom actions
        return [{
            "name": "my_custom_action",
            "description": "Does something useful"
        }]
```

**Note:** This is different from Mineflayer plugins (JavaScript), which are installed via npm and handle low-level bot behaviors.

### Testing Changes

```bash
# Run with verbose output
uv run main.py --agents ./profiles/max.json

# Check logs
tail -f logs/log-*.json
```

---

## Resources

- [Main README](README.md)
- [Minecraft AI Whitepaper](https://github.com/aeromechanic000/minecraft-ai-whitepaper)
- [JSPyBridge Documentation](https://github.com/extremeheat/JSPyBridge)
- [Mineflayer Documentation](https://github.com/PrismarineJS/mineflayer)
