# Create AIC Profiles

Minecraft AI characters in the Python implementation are defined through **profile files** written in JSON. Each profile specifies the bot’s name, personality, appearance, and language model configuration—allowing you to craft intelligent and expressive in-game companions.

This guide walks you through how to create a bot profile that works with the `minecraft-ai-python` framework.

🔬 *Try the visual toolkit to create bot profiles:* [Original Character for Minecraft AI](https://minecraft-ai-oc-creator.vercel.app/)

---

## 1. Create the Profile File

Create a new JSON file in your working directory. For example:

```

profiles/max.json

````

---

## 2. Set Basic Identity

Each bot requires a `username`. You may also optionally assign a custom Minecraft skin:

```json
{
    "username": "Max",
    "skin": {
        "model": "classic",
        "file": "~/Projects/minecraft-ai/skins/max.png"
    }
}
````

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

The `longterm_thinking` field defines the bot’s overarching purpose and memory strategy:

```json
"longterm_thinking": "I aim to become a reliable builder and problem-solver who helps the player achieve big goals..."
```

Tips:

* Mention growth, learning, or player-centered cooperation.

---

## 5. Configure the LLM Model

Specify the backend model used for the bot's language reasoning and dialogue:

```json
"provider": "Doubao",
"model": "doubao-1-5-pro-32k-250115"
```

* `provider`: The platform or API (e.g., `"OpenAI"`, `"Doubao"`, `"Ollama"`)
* `model`: The specific model identifier from that provider

Ensure the corresponding API keys are configured in `model.json` file or system environment variables.

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
  "provider": "Doubao",
  "model": "doubao-1-5-pro-32k-250115"
}
```