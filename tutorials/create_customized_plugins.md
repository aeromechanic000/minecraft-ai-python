# How to Create Custom Plugins

Minecraft AI introduces a flexible plugin system, which has also been submitted as a pull request to MINDcraft. Once accepted, you’ll be able to use the same plugin mechanism in MINDcraft as well.

Plugins allow you to extend the behavior of AI characters by adding new actions or capabilities—without modifying the core implementation of Minecraft AI. This makes them the recommended way to teach your AI new and exciting skills.

In this tutorial, you’ll learn how to create a plugin and enable it in your game.

---

## Plugin Structure

Each plugin should be placed in its own directory under `plugins/`. The directory name will be used as the plugin name. Inside the plugin folder, only a `main.py` file is required.

For example, the structure of a simple plugin called `Dance` looks like this:

```
plugins
└─ Dance
   └─ main.py
```

In `main.py`, you must define a class named `PluginInstance`, which is a subclass of `Plugin` from `plugin.py`.

## Defining `PluginInstance`

Your `PluginInstance` class have three key methods: `init`, `get_actions` and `get_reminder`. These methods are called automatically during the plugin lifecycle.

### `init(self, agent)`

Use the `init(self, agent)` method to handle any setup or initialization logic needed for your plugin.

### `get_actions(self)`

This method should return a list of custom actions you want to add. Each action must follow the format used in the returned list of `get_primary_actions()` in `actions.py`.

### `get_reminder(self)`

This method should return a message in the format of string, to provide useful information for the bot's reflection action (see `self_driven_thinking` in `actions.py`).

## Enabling Plugins

Plugins are only loaded if explicitly listed in the `plugins` in `settings.json`. If a plugin name is not included here, it will be ignored.

For example, to enable both the `Dance`plugins, use:

```json
"plugins" : ["Dance", ]
```

## Example Plugin: `Dance`

Here’s a simple example of the `Dance` plugin. This plugin makes your AI character do a small "dance" action. You can easily customize it to create your own signature moves.

```python
import sys, time
sys.path.append("../../")

from plugin import Plugin 

def pop_dancing(agent, duration) :
    result = ""
    agent.bot.chat("I am dancing~")
    agent.bot.setControlState("jump", True)
    time.sleep(duration)
    agent.bot.setControlState("jump", False)
    return result

class PluginInstance(Plugin) :
    def get_actions(self) :
        return [
            {
                "name" : '!dancePoping',
                "description" : 'Dance poping.',
                "params" : {
                    'duration': {"type" : 'float', "description" : 'Duration in seconds (e.g., 0.1 for 100 milliseconds).'},
                },
                "perform" : pop_dancing, 
            },
        ]
```
