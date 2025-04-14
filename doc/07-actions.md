
# Actions of Agent

In MineMCP, **Available Actions** represent the high-level behaviors that the agent can perform in the Minecraft world. These actions form the bridge between the **LLM's reasoning and decision-making** and the **actual execution** via Minecraft bot APIs (provided by [Mineflayer](https://github.com/PrismarineJS/mineflayer)) and custom skill modules.

### Purpose

During the **Planning Phase**, the LLM is tasked with choosing the next best action from the list of available options based on the context of recent messages, goals, and the current environment. Each action is defined with:

- A **name** (unique identifier).
- A **description** for the LLM to understand its purpose.
- **Parameters** that must be provided to execute it (with type constraints and domains).
- The **perform method**, which maps directly to the method on the Agent that will carry out the behavior.

This structure allows the LLM to act as a controller that generates executable plans in the form of structured action dictionaries.

### Action Schema

Each action has the following fields:

| Field        | Description |
|--------------|-------------|
| `name`       | Action identifier (e.g., `"go_to_player"`) |
| `desc`       | Natural language description of the action |
| `params`     | Dictionary of required parameters, with type, description, and domain constraints |
| `perform`    | Method name on the agent to execute the action |

---

### List of Available Actions

#### 1. **go_to_player**
> Move toward a specific player.

```json
{
  "player_name": "string",
  "closeness": "float (e.g., 1.0)"
}
```

#### 2. **move_away**
> Move away from the current position by a given distance.

```json
{
  "distance": "float (minimum 20)"
}
```

#### 3. **collect_blocks**
> Gather blocks of a specific type near the agent.

```json
{
  "block_name": "BlockName (e.g., 'log')",
  "num": "int (1 - 16)"
}
```

#### 4. **equip**
> Equip an item in hand or armor slot.

```json
{
  "item_name": "ItemName (e.g., 'iron_pickaxe')"
}
```

#### 5. **drop**
> Drop items from the inventory.

```json
{
  "item_name": "ItemName",
  "num": "int (1 - 16)"
}
```

#### 6. **search_block**
> Locate and go to a block of a given type within a range.

```json
{
  "block_name": "BlockName",
  "range": "float (32 - 512)"
}
```

#### 7. **search_entity**
> Locate and approach a nearby entity.

```json
{
  "entity_name": "string (e.g., 'cow')",
  "range": "float (32 - 512)"
}
```

#### 8. **fight**
> Attack the nearest entity of a specific type.

```json
{
  "entity_name": "string (e.g., 'zombie')"
}
```

#### 9. **craft**
> Craft items based on known recipes.

```json
{
  "recipe_name": "ItemName",
  "num": "int (1 - 4)"
}
```

#### 10. **chat**
> Send a message to a specific player or all players.

```json
{
  "player_name": "string (e.g., 'all' or a player name)",
  "message": "string (any text)"
}
```

### Dynamic Domains

Some parameter domains are dynamically generated at runtime, for example:

- `get_collect_block_names()`
- `get_drop_item_names()`
- `get_search_entity_names()`

These reflect the current environment or inventory context, ensuring the LLM works with only **valid, context-aware inputs**.

### Summary

The **available actions** act as the “vocabulary” the LLM can use to direct the Agent. This design encourages:

- **Safety:** Constraints on domains and types prevent invalid operations.
- **Interpretability:** Easy to track what the agent is doing and why.
- **Modularity:** You can add new actions by defining the perform method and describing its intent.

> Example flow:  
> LLM observes `"I need wood"` → selects `"collect_blocks"` with `"block_name": "log", "num": 5` → the `collect_blocks()` skill is called on the agent → bot starts gathering logs nearby.
