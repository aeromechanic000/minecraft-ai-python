
from utils import simple_rag

BREEDING_FOODS = {
    "cow": ["wheat"],
    "mooshroom": ["wheat"],
    "sheep": ["wheat"],
    "pig": ["carrot", "potato", "beetroot"],
    "chicken": ["wheat_seeds", "pumpkin_seeds", "melon_seeds", "beetroot_seeds"],
    "wolf": ["beef", "porkchop", "chicken", "rabbit", "mutton", "rotten_flesh"],
    "cat": ["cod", "salmon"],
    "horse": ["golden_apple", "golden_carrot"],
    "donkey": ["golden_apple", "golden_carrot"],
    "rabbit": ["carrot", "dandelion", "golden_carrot"],
}

KNOWLEDGE_BASE = {
    "crafting_basics": {
        "title": "Crafting & Inventory Mechanics",
        "tags": "craft crafting inventory planks sticks crafting_table furnace smelt smelting recipe tool pickaxe axe sword shovel hoe",
        "content": """
## Crafting & Inventory Mechanics

### Crafting Grids
- **2x2 Inventory Grid**: Always available in your inventory. Can craft basic items (planks, sticks, crafting table).
- **3x3 Crafting Table**: Required for most recipes. Use `interact_with_block` with a crafting_table to access it, or place one from inventory.

### Essential Crafting Recipes (use the `craft` action)
These are recipes you should know without needing to discover them:

**Important: Item Names** — Use specific Minecraft item names with the `craft` action. Common examples:
- Planks: `oak_planks`, `birch_planks`, `spruce_planks`, etc. (NOT "wood_planks")
- Logs: `oak_log`, `birch_log`, `spruce_log`, etc.
- Generic names like `planks`, `wood_planks`, `log` are auto-resolved based on inventory.

**From Logs (2x2 inventory grid):**
- Log → 4 Planks (e.g., oak_log → oak_planks)
- 2 Planks → 4 Sticks

**From Planks (2x2 inventory grid):**
- 4 Planks (2x2) → Crafting Table
- 3 Planks (row) → 6 Signs

**Tools (require Crafting Table):**
- Stone tier: replace planks with cobblestone
- Iron tier: replace with iron ingots (smelt iron ore in furnace)
- Diamond tier: replace with diamonds
- Gold tier: replace with gold ingots (smelt gold ore)

**Smelting (requires Furnace):**
- Iron Ore + fuel → Iron Ingot
- Gold Ore + fuel → Gold Ingot
- Sand + fuel → Glass
- Cobblestone + fuel → Stone
- Raw meat + fuel → Cooked meat (restores more hunger)
- Clay Ball + fuel → Brick
- Cactus + fuel → Green Dye
- Log + fuel → Charcoal (acts as coal substitute)
- Common fuel: coal, charcoal, lava bucket, blaze rod, wood items (less efficient)

**Utility Items (require Crafting Table):**
- 8 Cobblestone → Furnace
- 8 Planks → Chest (stores 27 stacks)
- 5 Leather → Leather Armor pieces / 5 Iron Ingots → Iron Armor / 5 Diamonds → Diamond Armor
- 7 Iron Ingots → Bucket (3 per row left+right, 1 center bottom)
- 3 Iron Ingots → Shears (2 diagonal)
- 4 Iron Ingots + 1 Flint → Flint and Steel
- 1 Iron Ingot + 1 Flint → Flint and Steel (alternate)
""",
    },
    "key_mechanics": {
        "title": "Key Game Mechanics",
        "tags": "tool durability hunger health day night light torch mining speed stack block hardness combat damage",
        "content": """
## Key Game Mechanics
- **Tool Durability**: Wooden=59, Stone=131, Iron=250, Diamond=1561, Gold=32 uses
- **Mining Speed**: Better tools mine faster. Wrong tool won't drop items (e.g., pickaxe needed for stone).
- **Tool Tiers**: Wood < Stone < Iron < Diamond < Netherite. Higher tier mines harder blocks.
- **Block Hardness**: Some blocks require specific tool tiers (e.g., iron pickaxe needed for diamond ore, gold ore, redstone ore).
- **Hunger**: Running/jumping drains hunger. Below 18 hunger = no health regen. At 0 hunger = take damage.
- **Stacking**: Most items stack to 64. Tools/armor do not stack.
- **Day/Night Cycle**: 20 minutes real time = 1 Minecraft day. Monsters spawn in darkness.
- **Light**: Torches (1 stick + 1 coal) prevent hostile mob spawning. Place them to stay safe.
""",
    },
    "animal_breeding": {
        "title": "Animal Breeding",
        "tags": "breed breeding animal cow sheep pig chicken wolf cat horse donkey rabbit mooshroom baby feed wheat carrot seed fish golden_apple dandelion potato beetroot love",
        "content": """
## Animal Breeding

### Breeding Foods by Animal
- **Cow / Mooshroom**: Wheat
- **Sheep**: Wheat
- **Pig**: Carrot / Potato / Beetroot
- **Chicken**: Any seeds (wheat, pumpkin, melon, beetroot seeds)
- **Wolf (tamed)**: Any meat (raw beef, porkchop, chicken, rabbit, mutton, rotten_flesh)
- **Cat (tamed)**: Raw fish (cod, salmon)
- **Horse / Donkey**: Golden Apple / Golden Carrot
- **Rabbit**: Carrot / Dandelion / Golden Carrot

### Breeding Process
1. Get two adult animals of the same species (babies cannot breed)
2. Obtain their breeding food items
3. Enclose them in a small area (within 8 blocks of each other)
4. Feed each animal once using `feed_animal` action (right-click with food)
5. Hearts appear — "Love Mode" activated
6. They move toward each other, "kiss" for ~3 seconds — baby spawns nearby
7. Parents get 5-minute cooldown before breeding again
8. Baby grows up in ~20 minutes; feeding it the same food speeds growth

### Key Tips
- Only adult, same-species pairs work
- Feed directly (do not drop food on ground)
- Keep animals within 8 blocks; they can pathfind through fences
- Use `breed_animals` action to automate the full process
""",
    },
}

def get_breeding_food(entity_name, inventory=None) :
    """Return the first available breeding food for the given entity from inventory, or the default food if no inventory given; call with get_breeding_food(entity_name, inventory)."""
    foods = BREEDING_FOODS.get(entity_name, None)
    if foods is None :
        for key in BREEDING_FOODS :
            if key in entity_name :
                foods = BREEDING_FOODS[key]
                break
    if foods is None :
        return None
    if inventory is not None :
        for food in foods :
            if inventory.get(food, 0) > 0 :
                return food
    return foods[0]

def _get_local_knowledge(query_text, top_k=3) :
    """Retrieve relevant local knowledge entries by keyword matching."""
    records = []
    for key, entry in KNOWLEDGE_BASE.items() :
        records.append(entry["tags"] + " " + entry["title"])

    results = simple_rag(query_text, records, top_k)

    matched = []
    keys = list(KNOWLEDGE_BASE.keys())
    for idx, _ in results :
        matched.append(KNOWLEDGE_BASE[keys[idx]]["content"].strip())
    return matched

def _get_online_knowledge(query_text, benchmark_url, top_k=3) :
    """Retrieve relevant online knowledge, guides, and advancements from the benchmark API. Returns list of formatted strings."""
    from model import search_benchmark

    entries = []

    # Search knowledge (task categories with action references)
    try :
        result = search_benchmark(benchmark_url, query_text, "knowledge")
        if result and "results" in result :
            for item in result["results"][:top_k] :
                if not isinstance(item, dict) :
                    continue
                parts = []
                # results are {path, content} dicts from recursive search
                content = item.get("content", item)
                category = content.get("name", item.get("path", ""))
                description = content.get("description", "")
                actions = content.get("actions", [])
                if category :
                    parts.append("## %s" % category)
                if description :
                    parts.append(description)
                if actions and isinstance(actions, list) :
                    action_names = []
                    for a in actions[:5] :
                        if isinstance(a, dict) :
                            action_names.append(a.get("name", str(a)))
                        else :
                            action_names.append(str(a))
                    if action_names :
                        parts.append("Related actions: %s" % ", ".join(action_names))
                if len(parts) > 0 :
                    entries.append("\n".join(parts))
    except :
        pass

    # Search guides (step-by-step instructions for advancements)
    try :
        result = search_benchmark(benchmark_url, query_text, "guides")
        if result and "results" in result :
            for item in result["results"][:top_k] :
                if not isinstance(item, dict) :
                    continue
                parts = []
                title = item.get("title", item.get("name", ""))
                steps = item.get("steps", [])
                if title :
                    parts.append("## Guide: %s" % title)
                if steps and isinstance(steps, list) :
                    for step in steps[:5] :
                        if isinstance(step, dict) :
                            step_desc = step.get("description", "")
                            action_name = step.get("action_name", "")
                            if step_desc :
                                line = "- %s" % step_desc
                                if action_name :
                                    line += " (action: %s)" % action_name
                                parts.append(line)
                if len(parts) > 1 :
                    entries.append("\n".join(parts))
    except :
        pass

    # Search advancements (rationale and actual requirements)
    try :
        result = search_benchmark(benchmark_url, query_text, "advancements")
        if result and "results" in result :
            for item in result["results"][:top_k] :
                if not isinstance(item, dict) :
                    continue
                parts = []
                name = item.get("name", "")
                rationale = item.get("rationale", "")
                actual = item.get("actual", "")
                level = item.get("level", "")
                if name :
                    header = "## Advancement: %s" % name
                    if level :
                        header += " (%s)" % level
                    parts.append(header)
                if rationale :
                    parts.append(rationale)
                if actual :
                    parts.append("How to: %s" % actual)
                if len(parts) > 1 :
                    entries.append("\n".join(parts))
    except :
        pass

    return entries

def get_knowledge_context(agent, query=None, top_k=3) :
    """Retrieve relevant Minecraft knowledge from both local and online sources; returns formatted string or None."""
    from skills import get_inventory_counts, get_nearest_entities

    search_parts = []

    if query is not None :
        search_parts.append(query)

    if hasattr(agent, 'current_goal') and agent.current_goal is not None :
        target = agent.current_goal.get("target", "")
        if target is not None and len(target.strip()) > 0 :
            search_parts.append(target)

    try :
        inventory = get_inventory_counts(agent)
        if inventory is not None :
            search_parts.extend(inventory.keys())
    except :
        pass

    try :
        entities = get_nearest_entities(agent, 16, 8)
        for entity in entities :
            search_parts.append(entity.name)
    except :
        pass

    query_text = " ".join(search_parts)
    if len(query_text.strip()) == 0 :
        return None

    # Local knowledge
    local_entries = _get_local_knowledge(query_text, top_k)

    # Online knowledge (best-effort, skip if unreachable)
    online_entries = []
    benchmark_url = None
    if hasattr(agent, 'settings') and agent.settings is not None :
        benchmark_url = agent.settings.get("benchmark_api_url", None)
    if benchmark_url is not None :
        online_entries = _get_online_knowledge(query_text, benchmark_url, top_k)

    all_entries = local_entries + online_entries
    if len(all_entries) == 0 :
        return None

    return "\n\n".join(all_entries)
