# <img src="https://s2.loli.net/2025/04/18/RWaFJkY4gSDLViy.png" alt="Minecraft AI" width="36" height="36"> Minecraft AI-Python: An Open Framework for Building Embodied AI in Minecraft

Minecraft AI-Python is a modular framework designed to support the creation and customization of AI Characters (AICs) within Minecraft environments. It provides a stable and extensible interface for perception, action, communication, memory, and reflection—enabling complex individual and multi-agent behaviors.

This project is part of the broader Minecraft AI ecosystem. While the original [Minecraft AI](https://github.com/aeromechanic000/minecraft-ai) project focuses on a JavaScript-based infrastructure with integrated components, minecraft-ai-python emphasizes simplicity, flexibility, and rapid development in Python. It is ideal for educational experiments, prototyping research ideas, and custom agent development by individual contributors.

More detailed information can be found in [Minecraft AI Whitepapers and Technical Reports](https://github.com/aeromechanic000/minecraft-ai-whitepaper).

- [Minecraft AI: Toward Embodied Turing Test Through AI Characters](https://github.com/aeromechanic000/minecraft-ai-whitepaper/blob/main/whitepapers/minecraft_ai_whitepaper-toward_embodied_turing_test_through_ai_characters.pdf)

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

Create a virtual environment with Python 3.10 using Anaconda:

```bash
conda create -n mc python=3.10
conda activate mc
```

Install Python dependencies:

```bash
pip install -r requirements.txt
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
"agents": ["./max.json"]
```

Here’s a minimal example of `max.json`:

```json
{
    "username": "Max",
    "profile": "You are a smart Minecraft agent following your own heart...",
    "longterm_thinking": "I aim to become a reliable builder and problem-solver...",
    "self_driven_thinking_timer" : null,
    "provider": "ollama",
    "model": "llama3.2"
}
```

🛎️ **It is recommended** to set `self_driven_thinking_timer` to an integer such as `100` or `1000`.
When `self_driven_thinking_timer` is not `null`, the bot will perform a reflection step every time it completes an action. Additionally, this timer serves as a delay before triggering autonomous reflection when the bot is idle.
The timer value represents the number of laps the bot should wait. A lap refers to one interval between two consecutive "time" events in the Mineflayer framework, which occurs approximately every `20` game ticks.
Since there are about `10,000` ticks per hour in Minecraft, you can estimate how long each interval lasts in real-world time by doing the math based on your `self_driven_thinking_timer` value.

> 🔍 Explore more sample profiles in the `profiles/` directory.

### 5. Configure AI Model Access

To supply API keys for LLM backends:

1. Copy `model.example.json` to `model.json`;
2. Fill in your API keys for the models you want to use:

```json
{
    "OpenAI": {
        "api_key" : "",
        "url": "https://api.openai.com/v1/responses"
    },
    "DeepSeek": {
        "api_key": "",
        "url": "https://api.deepseek.com/chat/completions"
    }
}
```

> 🔐 **Best Practice**: Use [environment variables](https://github.com/aeromechanic000/minecraft-ai/blob/main/tutorials/set_an_api_key_as_an_environment_variable.md) instead of hardcoding keys. If a key in `keys.json` is blank, Minecraft AI will automatically attempt to read it from your environment variables.

Then configure the desired provider and model of the bot profile:

```json
"provider" : "openai",
"model" : "gpt-4o"
```

✅ A full list of supported API providers and models is available in the table below.

<table>
<tr>
    <td> <b>Provider</b> </td> 
    <td> <b>Key</b> </td> 
    <td> <b>Model</b> </td>
    <td> <b>Example</b> </td>
</tr>
<tr>
    <td> OpenAI </td>
    <td> OPENAI_API_KEY </td>
    <td> gpt-4.1, gpt-4o <br> <a href="https://platform.openai.com/docs/models">full list of models</a> </td>
    <td> "model" : {"api" : "openai", "model" : "gpt-4o"} </td>
</tr>
<tr>
    <td> Google </td>
    <td> GEMINI_API_KEY </td>
    <td> gemini-2.5-flash-preview-05-20 <br> <a href="https://ai.google.dev/gemini-api/docs/models">full list of models</a> </td>
    <td> "model" : {"api" : "google", "model" : "gemini-2.5-flash-preview-05-20"} </td>
</tr>
<tr>
    <td> Anthropic </td>
    <td> ANTHROPIC_API_KEY </td>
    <td> claude-opus-4-20250514 <br> <a href="https://docs.anthropic.com/en/docs/about-claude/models/overview">full list of models</a> </td>
    <td> "provider" : "anthropic", "model" : "claude-opus-4-20250514" </td>
</tr>
<tr>
    <td> Deepseek </td>
    <td> DEEPSEEK_API_KEY </td>
    <td> deepseek-chat, deepseek-reasoner <br> <a href="https://api-docs.deepseek.com/quick_start/pricing">full list of models</a> </td>
    <td> "provider" : "deepseek", "model" : "deepseek-chat" </td>
</tr>
<tr>
    <td> Doubao </td>
    <td> DOUBAO_API_KEY </td>
    <td> doubao-1-5-pro-32k-250115 <br> <a href="https://www.volcengine.com/docs/82379/1330310">full list of models</a> </td>
    <td> "provider" : "doubao", "model" : "doubao-1-5-pro-32k-250115" </td>
</tr>
<tr>
    <td> Qwen </td>
    <td> QWEN_API_KEY </td>
    <td> qwen-max, qwen-plus <br> <a href="https://help.aliyun.com/zh/model-studio/getting-started/models">full list of models</a> </td>
    <td> "provider" : "qwen", "model" : "qwen-max" </td>
</tr>
<tr>
    <td> <a href="https://pollinations.ai/">Pollinations</a> </td>
    <td> <b>NOT REQUIRED</b> </td>
    <td> openai-large, gemini, deepseek <br> <a href="https://text.pollinations.ai/models">full list of models</a> </td>
    <td> "provider" : "pollinations", "model" : "openai-large"</td>
</tr>
<tr>
    <td> <a href="https://ollama.com/">Ollama</a> </td>
    <td> <b>NOT REQUIRED</b> </td>
    <td> llama3.2, llama3.1 <br> <a href="https://ollama.com/library">full list of models</a> </td>
    <td> "provider" : "ollama", "model" : "llama3.2"</td>
</tr>
<tr>
    <td> Openrouter </td>
    <td> OPENROUTER_API_KEY </td>
    <td> deepseek/deepseek-chat-v3-0324:free <br> <a href="https://openrouter.ai/models">full list of models</a> </td>
    <td> "provider" : "openrouter", "model" : "deepseek/deepseek-chat-v3-0324:free" </td>
</tr>
</table>

🧛‍♀️ *You can also use Deepseek models through the "doubao" API.*

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
