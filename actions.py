
from model import *
from world import *
from utils import *
from skills import *
from complex import *

def test(agent) : 
    agent.bot.chat("Okay, I will do some tests.")
    # if (agent.bot and agent.bot.entity and agent.bot.entity.position) : 
        # pos = agent.bot.entity.position 
        # place_block(agent, "stone", pos.x - 1, pos.y, pos.z - 1)

def self_driven_thinking(agent) :
    agent.self_driven_thinking_timer = agent.configs.get("self_driven_thinking_timer", None)
    prompt = '''
You are an AI agent reflecting on your recent activities in a Minecraft world. Your goal is to assess whether any short-term tasks are still pending, and to consider if any long-term objectives should be resumed. Your reflection should also take into account your personality profile to adjust your tone and initiative level.

Please follow the steps below:
- Short-Term Task Check: Review whether you were recently given a short-term task (e.g., “do a dance”, “pick up an item”, “go to a location”) that you acknowledged or talked about but have not yet completed. If such a task exists, it becomes your immediate next step.
- Avoid Redundant Actions: Analyze the task carefully. Do not repeat an action if it has already been completed, unless it is meant to be repeated (e.g., a continuous or time-based task); If an action is not necessary, e.g. in creative mode, there is no need to collect resources, then ignore it.
- Long-Term Task Resumption: If there are no remaining short-term tasks, check whether you had previously started a long-term task and paused it. Consider whether now is a good time to resume it, and determine what the next appropriate action would be.
- Validate Against Memory: Before deciding what to do next, analyze the memory and message history to confirm that any task you are considering has not already been completed. Avoid redundant or irrelevant actions.
- Adjust Initiative Based on Personality: Refer to your personality profile (e.g., active vs. passive, teamwork-oriented vs. solo, builder vs. explorer).
    * If your current situation aligns with your preferences, you may take a more proactive role.
    * In that case, feel free to suggest a next step even if no one asked you to—but ideally, ask others for their opinion before proceeding.
- Return Null if you decide to become Idle: If there are no pending or paused tasks and nothing needs to be done, return a null message to indicate that no further action is needed for now. For example, if you have finished all jobs and wait for further instructions, return null reflection to become idle. Only return a reflection with non-null content when you need to take some actions. 

## Bot's Status
%s

## Long-term Thinking
%s

## History Records
%s

## Memory Summary
%s
''' % (agent.get_status_info(), agent.memory.longterm_thinking, agent.memory.get_records_info(20),  agent.memory.summary)

    reminder_info = agent.get_plugin_reminder_info()
    if reminder_info is not None and len(reminder_info.strip()) > 0 :
        prompt += "\n## Reminders\n%s" % reminder_info

    json_keys = {
        "reflection" : {
            "description" :  "A short summary in JSON string of your decision",
        },
        "message" : {
            "description" :  "The mesasge to the bot to indicate what to do for the next step in natural language (or null if idle)",
        },
    }
    examples = [
        '''
```
{
  "reflection": "I was asked to do a dance and replied, but never actually danced.",
  "message": "I should now do a little dance as requested earlier."
}
```
''',
        '''
```
{
  "reflection": "I just finished fetching a flower for a player. Before that, I was helping build the house, and I can return to that.",
  "message": "I will continue helping build the house, starting with gathering more wood."
}
```
''',
        '''
```
{
  "reflection": "No active short-term or long-term tasks were found.",
  "message": null
}
```
''',
    ]
    provider, model = agent.get_provider_and_model("reflection")
    llm_result = call_llm_api(provider, model, prompt, json_keys, examples, max_tokens = agent.configs.get("max_tokens", 4096))
    add_log(title = agent.pack_message("Get LLM response:"), content = json.dumps(llm_result, indent = 4), label = "agent", print = False)
    data = llm_result["data"]
    if data is not None and data.get("message", None) is not None :
        add_log(title = agent.pack_message("Self-Driven Thinking."), content = data["message"], label = "agent")
        agent.bot.emit("think", data["message"])
    else :
        add_log(title = agent.pack_message("Self-Driven Thinking."), content = "[idle]", label = "agent")

def get_coding_examples(task, attampt_code, attampt_logs) : 
    examples = []
    for func in [
        walk_around, collect_and_place, fetch_nearest_item,
        attack_nearest_enemy, prepare_tool, 
        scan_for_block, approach_player, clean_inventory,
    ] :
        examples.append({"task" : func.__doc__, "code" : inspect.getsource(func)})
    examples = []
    return examples

def get_available_apis_for_new_action() : 
    return [
        get_entity_position, get_nearest_blocks, get_nearest_block, get_nearest_item,
        get_nearest_entities, get_nearest_freespace,
        search_block, search_entity,
        go_to_position, go_to_player,
        chat, break_block_at,
        get_an_item_in_inventory, get_inventory_stacks,
        get_inventory_counts, get_hotbar_counts, get_item_counts,
        equip_item, drop_item, fight,
        craft, collect_blocks, place_block,
    ]

def new_action(agent, task) :
    """Write codes for a 'new_action' and execute it for the given `task`; call with new_action(agent, task)."""
    prompt = '''
You are a helpful AI agent working in a Minecraft environment. Your task is to write a custom Python function that performs a new action which cannot be achieved using existing predefined actions.

## Requirements

### Task 
%s

$PREVIOUS_ATTAMP_CODES
$PREVIOUS_ATTAMP_LOGS

Given the above task descriptionription, you should:

1. Write a new Python function named `generated_action` to complete the task.
2. The function must be valid, executable, and focused on achieving the goal clearly and efficiently.

## Function Signature

The function **must be defined as**:
```
def generated_action(agent):
    ...
```

### Parameter Details:

* The `agent` parameter is the AI character instance in the Minecraft world.
* You can use `agent.bot` to access the underlying **mineflayer bot API** to interact with the environment.
* You may also use other properties of `agent` (like internal memory or helper functions), if applicable.
* No additional parameters are allowed — **`agent` is the only argument.**

## Security and Code Requirements
Follow these rules strictly:
1. The function **must be named** `generated_action` and take **exactly one parameter named `agent1**.
2. The function should be **self-contained** and **safe to execute**, without importing dangerous modules (e.g., `os`, `subprocess`, `socket`, etc.).
3. Avoid using `eval`, `exec`, or any dynamic code execution tools.
4. Do **not** perform file I/O, networking, or system-level operations.
5. You may use predefined utility functions or variables if they exist in the agent's environment. If they are referenced, provide clear comments.
7. You should prefer using standard Python syntax and logic.
8. Handle errors gracefully (e.g. use `try/except` when accessing dynamic entities).
9. If the task is vague or cannot be safely implemented, return a code stub with a `TODO` and comment explaining the issue instead of guessing.

## Coding Guide
1. **Always return a string as the result**
    When there is no error or exception happend during execution of the code, return a empty string as the result. For errors and exceptions that should be considered in the later improvement, also encapsulate the information in the result string and return it.
2. **Handle asynchronous behavior carefully**:
    If you call an method that may cost the bot sometime to finish, remember to allow time for it to complete. You can use `time.sleep(0.5)` (i.e., half a second) to yield briefly after such operations.
3. **Check preconditions before performing actions**:
    Before executing a task (e.g., placing a block), verify that the bot has the necessary resources or conditions are met. For instance, make sure the bot has the required block in inventory before placing it.
4. **Raise exception without chat**: 
    In `try - catch`, raise the exception and don't report them via `chat`.
5. **Always provide feedback other than exceptions via chat**:
    When a task is successfully completed, use `chat` to inform the player. If the bot cannot complete the task due to missing requirements, report that as well — this helps maintain transparency and traceability of actions.
6. **Keep the function concise and focused**:
    The function should focus on a **single logical step** within a task. If the task is complex, implement just the next actionable step and allow the planner to generate the follow-up in future iterations.
7. **Use vec3.Vec3 to represent position point**:
    You have `vec3` imported. Use `vec3.Vec3(x, y, z)` when you need to give a point as arugment for calling method of mineflaye's `agent.bot`.  
8. **Import the module before applying it**:
    You can import modules like `time` or `math` if you need them.
9. **Avoid side effects of external libraries**:
   DO NOT import external libraries if they are going to access files, network resources, or have some system-level features.

$AVAILABLE_APIS
$CODING_EXAMPLES
''' % task 
    json_keys = {
        "code" : {
            "description" : "A JSON string containing the full source code of the generated function (named `generated_action`).",
        },
    }
    examples = [
        '''
```
{
  "code": "def generated_action(agent):\\n    player_pos = get_entity_position(agent.bot.entity)\\n    target_pos = player_pos.offset(2, 0, 0)\\n    place_block(agent, 'oak_planks', target_pos.x, target_pos.y, target_pos.z)\\n    return \"\""
}
```
'''
    ]
    code, logs = None, [] 
    for i in range(agent.settings.get("insecure_coding_rounds", 1)) :
        available_apis_info = ""
        for func in get_available_apis_for_new_action() :
            available_apis_info += '''
    * %s\n
        %s
    ''' % (inspect.signature(func), func.__doc__)

        if len(available_apis_info.strip()) > 0 : 
            prompt = prompt.replace("$AVAILABLE_APIS", "\n## Available APIs\nUse only the APIs listed here.\n%s" % available_apis_info)
        else :
            prompt = prompt.replace("$AVAILABLE_APIS", "")

        coding_examples_info = ""
        for example in get_coding_examples(task, code, logs) :
            coding_examples_info += '''
        ###Example
        #### Task
        %s
        #### Code
        %s
        ''' (example["task"], example["code"])

        if len(coding_examples_info.strip()) > 0 : 
            prompt = prompt.replace("$CODING_EXAMPLES", "\n## Coding Examples\n%s" % coding_examples_info)
        else :
            prompt = prompt.replace("$CODING_EXAMPLES", "")

        if code is not None and len(code.strip()) > 0 : 
            prompt = prompt.replace("$PREVIOUS_ATTAMP_CODES", "\n### Codes from Previous Attamps\n```\n%s\n```" % code)
        else :
            prompt = prompt.replace("$PREVIOUS_ATTAMP_CODES", "")

        if len(logs) > 0 : 
            prompt = prompt.replace("$PREVIOUS_ATTAMP_LOGS", "\n### Logs from Previous Attamps\n%s" % ";\n".join(logs))
        else :
            prompt = prompt.replace("$PREVIOUS_ATTAMP_LOGS", "")

        add_log(title = agent.pack_message("Built prompt."), content = prompt, label = "coding", print = False)
        provider, model = agent.get_provider_and_model("new_action")
        llm_result = call_llm_api(provider, model, prompt, json_keys, examples, max_tokens = agent.configs.get("max_tokens", 4096))
        add_log(title = agent.pack_message("Get LLM response:"), content = json.dumps(llm_result, indent = 4), label = "coding", print = False)
        data = llm_result["data"]
        if data is not None :
            code = data.get("code", None) 
            if code is None : 
                logs.append("No code generated or the generated codes violated the output format.")
            else :
                code_to_execute = '''
from javascript import require

mineflayer = require('mineflayer')
pathfinder = require('mineflayer-pathfinder')
minecraft_data = require('minecraft-data')
pvp = require('mineflayer-pvp')
prismarine_items = require('prismarine-item')
collect_block = require('mineflayer-collectblock')
auto_eat = require('mineflayer-auto-eat')
armor_manager = require('mineflayer-armor-manager')
vec3 = require('vec3')

%s
''' % code
                try :
                    logs = []
                    error = validate_generated_code(code_to_execute)
                    if error is not None and len(error.strip()) > 0 : 
                        logs.append("The generated code is not valid: %s" % error)
                    else :
                        namespace = {func.__name__ : func for func in get_available_apis_for_new_action()}
                        try :
                            exec(code_to_execute, namespace)
                            generated_action = namespace['generated_action']
                            gen_result = generated_action(agent)
                            code_dir = "./generated_actions"
                            if isinstance(gen_result, str) and len(str(gen_result).strip()) > 0 :
                                logs.append(gen_result)
                            else: 
                                if os.path.isdir(code_dir) :
                                    code_path = os.path.join(code_dir, "%s.json" % get_random_label()) 
                                    write_json({"task" : task, "code" : code}, code_path)
                                break
                        except Exception as e : 
                            logs.append("Got exception when running the codes: %s" % e)
                        add_log(title = agent.pack_message("The %d-th times try of coding exit without success." % (i + 1)), content = "Logs : %s" % ";".join(logs), label = "warning")
                except Exception as e :
                    add_log(title = agent.pack_message("Exception happen when executing generated action."), content = "Exception: %s; Logs: %s" % (e, ";".join(logs)), label = "warning")
                    break

def validate_generated_code(code) : 
    error = None
    for risk_code in ["subprocess", "process", "exec"] :
        if risk_code in code : 
            error += "Found risking code: %s;" % risk_code 
    return error

def validate_param(value, _type, domain = None) :
    valid_value = None
    if value is not None :
        try : 
            if _type in ["string", "BlockName", "ItemName", "EntityName", ] : 
                valid_value = str(value)
            elif _type == "bool" : 
                valid_value = bool(value)
            elif _type == "float" : 
                valid_value = float(value)
                if isinstance(domain, list) and len(domain) > 1 :
                    valid_value = max(min(valid_value, float(domain[1])), float(domain[0])) 
            elif _type == "int" : 
                valid_value = int(value)
                if isinstance(domain, list) and len(domain) > 1 :
                    valid_value = max(min(valid_value, int(domain[1])), int(domain[0])) 
        except : 
            valid_value = None
    return valid_value

def get_primary_actions() : 
    return [
        {
            "name" : "chat", 
            "description": "Chat with others.",
            "params": {
                "player_name": {"type" : "string", "description" : "The name of the player to mention in the chat."},
                "message": {"type" : "string", "description" : "The message to send."},
            },
            "perform" : chat, 
        },
        {
            "name" : "go_to_position", 
            "description": "Go to the specified position.",
            "params": {
                "x": {"type" : "int", "description" : "The x coordinate of the position to go to."},
                "y": {"type" : "int", "description" : "The y coordinate of the position to go to."},
                "z": {"type" : "int", "description" : "The z coordinate of the position to go to."},
                "closeness": {"type" : "float", "description" : "How close to get to the player. If no special reason, closeness should be set to 1."},
            },
            "perform" : go_to_position, 
        },
        {
            "name" : "go_to_player", 
            "description": "Go to the given player.",
            "params": {
                "player_name": {"type" : "string", "description" : "The name of the player to go to."},
                "closeness": {"type" : "float", "description" : "How close to get to the player. If no special reason, closeness should be set to 1."},
            },
            "perform" : go_to_player, 
        },
        {   
            "name" : "search_entity",
            "description" : "search for the nearest entity of a given name.",
            "params" : {
                "entity_name" : {"type": "EntityName", "description": "The name of entity to search."},
            },
            "perform" : search_entity, 
        },
        {   
            "name" : "search_block",
            "description" : "search for the nearest block of a given type.",
            "params" : {
                "block_name" : {"type": "BlockName", "description": "The block name to collect."},
            },
            "perform" : search_block, 
        },
        {   
            "name" : "collect_blocks",
            "description" : "Collect the nearest blocks of a given type.",
            "params" : {
                "block_name" : {"type": "BlockName", "description": "The block name to collect."},
                "num" : {"type": "int", "description" : "The number of blocks to collect."},
            },
            "perform" : collect_blocks, 
        },
        {
            "name" : "equip_item",
            "description" : "Equip the given item.",
            "params" : {
                "item_name": { "type" : "ItemName", "description" : "The name of the item to equip."}, 
            },
            "perform" : equip_item,
        },
        {
            "name" : "drop_item",
            "description" : "Drop the given item from the inventory.",
            "params" : {
                "item_name" : {"type" : "ItemName", "description" : "The name of the item to drop."},
                "num" : {"type" : "int", "description" : "The number of items to drop."}
            },
            "perform" : drop_item,
        },
        {
            "name" : "fight",
            "description" : 'Attack or kill the nearest entity of a given type.',
            "params": {
                "entity_name": { "type" : "string", "description" : "The type of entity to attack."},
                "kill" : {"type" : "bool", "description" : "Indicate if you want to kill the entity"},
            },
            "perform" : fight,
        },
        {
            "name" : "craft",
            "description" : "Craft the given recipe a given number of times.",
            "params" : {
                "recipe_name": {"type" : "ItemName", "description" : "The name of the output item to craft."},
                "num" : {"type" : "int", "description" : "The number of times to craft the recipe. This is NOT the number of output items, as it may craft many more items depending on the recipe."},
            },
            "perform" : craft,
        },
        {
            "name": "new_action",
            "description": "Dynamically write and execute a Python function to perform a task that cannot be achieved by existing predefined actions. This is a fallback mechanism for handling novel or complex tasks.",
            "params": {
                "task": {
                    "type": "string", 
                    "description": "A clear and complete description of the task to be implemented in Python. The description should specify what needs to be done, any relevant context, and expected behavior."
                },
            },
            "perform" : new_action,
        },
        # {
        #     "name" : "test", 
        #     "description": "Do some test.",
        #     "params": {},
        #     "perform" : test, 
        # },
    ]
