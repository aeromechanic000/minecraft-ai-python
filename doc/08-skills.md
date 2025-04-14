
# Skills of Agent

In MineMCP, **skills** are low-level utility methods that directly interact with the Minecraft world through the Mineflayer API. These methods are not meant to be called by the LLM directly. Instead, they serve as building blocks for the higher-level **actions** available to the LLM.

Skills handle tasks like locating nearby entities, identifying free spaces, checking surroundings, or accessing block and inventory data. By abstracting these core operations, MineMCP ensures that high-level actions remain clean, focused, and reusable.

Below are some representative examples of skills used in the system:

---

### `get_nearest_entity_where(predicate, max_distance)`

Finds the nearest entity that satisfies a given condition within a specified distance.

- **Usage**: Helps actions like `fight` or `search_entity` locate a valid target.
- **Input**: A predicate function and a distance limit.
- **Output**: The nearest matching entity object, or `None`.

---

### `get_nearby_entities(max_distance=32, count=16)`

Returns a list of nearby entities, sorted by distance, up to a specified maximum count.

- **Usage**: Useful for environment scanning, prioritizing threats, or situational awareness.
- **Includes**: Basic distance filtering and sorting.
- **Note**: Also logs invalid or missing entities when encountered.

---

### `get_nearest_freespace(size=1, distance=8)`

Searches for a free space within a radius that the bot can safely move to or stand on.

- **Usage**: Used by actions like `move_away` to find escape paths or idle spots.
- **Checks**:
  - Top block must be air.
  - Bottom block must be diggable and able to support the bot.
- **Returns**: The first valid position found, or `None`.

---

These and other similar skills are designed to be modular and composable, allowing new high-level actions to be built quickly with minimal duplication. They also act as a foundation for more complex planning and environment interaction strategies in later modules.
