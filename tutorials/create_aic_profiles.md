# Create AIC Profiles

Minecraft AI characters in the Python implementation are defined through **profile files** written in JSON. Each profile specifies the bot's name, personality, appearance, and language model configuration—allowing you to craft intelligent and expressive in-game companions.

This guide walks you through how to create a bot profile that works with the `minecraft-ai-python` framework.

🔬 *Try the visual toolkit to create bot profiles:* [Original Character for Minecraft AI](https://minecraft-ai-oc-creator.vercel.app/)

---

## 1. Create the Profile File

Create a new JSON file in your working directory. For example:

```
profiles/max.json
```

---

## 2. Set Basic Identity

Each bot requires a `username`. You may also optionally assign a custom Minecraft skin:

```json
{
    "username": "Max",
    "skin": {
        "model": "classic",
        "file": "~/Projects/minecraft-ai-python/skins/max.png"
    }
}
```

* `username`: How the bot appears in the Minecraft world.
* `skin.model`: `"classic"` or `"slim"` depending on the skin layout.
* `skin.file`: Path to the skin `.png` file. Use an **absolute path**.

---

## 3. Define the Bot's Personality

Use the `profile` field to define the bot's voice, tone, and behavioral traits.

```json
"profile": "A smart Minecraft agent following own heart! Pragmatic, focused, and a little reserved..."
```

Tips:

* Be descriptive and imaginative—this text guides how the language model roleplays the bot.
* Include values, attitudes, and preferred interaction styles.

---

## 4. Add Long-Term Goals

The `longterm_thinking` field defines the bot's overarching purpose and memory strategy:

```json
"longterm_thinking": "I aim to become a reliable builder and problem-solver who helps the player achieve big goals..."
```

Tips:

* Mention growth, learning, or player-centered cooperation.

---

## 5. Configure the LLM Model

Specify the LLM provider using the `llm` configuration with `base_url`, `model`, and `api_key`:

```json
"llm": {
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o",
    "api_key": "env:OPENAI_API_KEY"
}
```

* `base_url`: The API endpoint URL (see provider table below)
* `model`: The specific model identifier
* `api_key`: Your API key or `env:VAR_NAME` to read from environment variable

**Common base URLs:**

| Provider | Base URL |
|----------|----------|
| OpenAI | `https://api.openai.com/v1` |
| Anthropic | `https://api.anthropic.com/v1` |
| DeepSeek | `https://api.deepseek.com` |
| Doubao | `https://ark.cn-beijing.volces.com/api/v3` |
| Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| Ollama | `http://127.0.0.1:11434/v1` |
| Pollinations | `https://text.pollinations.ai/openai` |

Set your API key as an environment variable:

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

---

## 6. Tag-Specific Configuration (Optional)

You can configure different models for different tasks:

```json
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
    }
}
```

Available tags: `memory`, `reflection`, `decide`, `new_action`

---

## ✅ Summary: Example Profile

```json
{
  "username": "Max",
  "skin": {
    "model": "classic",
    "file": "~/Projects/minecraft-ai-python/skins/max.png"
  },
  "profile": "A smart Minecraft agent following own heart! Pragmatic, focused, and a little reserved...",
  "longterm_thinking": "I aim to become a reliable builder and problem-solver who helps the player achieve big goals...",
  "llm": {
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model": "doubao-1-5-pro-32k-250115",
    "api_key": "env:DOUBAO_API_KEY"
  }
}
```
